"""Statistical inference utilities for the Chicago crash-severity portfolio.

The functions implement association analysis, not causal identification.  They are
written to make coefficient uncertainty, model performance, and data provenance
explicit in a reproducible workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


@dataclass(frozen=True)
class BootstrapEstimate:
    """A group-level point estimate and percentile confidence interval."""

    group: str
    n: int
    point_estimate: float
    lower_ci: float
    upper_ci: float


def wilson_interval(successes: pd.Series, totals: pd.Series, alpha: float = 0.05) -> pd.DataFrame:
    """Return Wilson score confidence intervals for binomial proportions."""
    successes = pd.to_numeric(successes, errors="coerce").fillna(0).astype(float)
    totals = pd.to_numeric(totals, errors="coerce").fillna(0).astype(float)
    p = successes.div(totals.where(totals > 0))
    z = norm.ppf(1 - alpha / 2)
    denom = 1 + z**2 / totals.where(totals > 0)
    center = (p + z**2 / (2 * totals.where(totals > 0))) / denom
    half_width = z * np.sqrt((p * (1 - p) + z**2 / (4 * totals.where(totals > 0))) / totals.where(totals > 0)) / denom
    return pd.DataFrame({"rate": p, "lower_ci": center - half_width, "upper_ci": center + half_width})


def stratified_bootstrap_rates(
    frame: pd.DataFrame,
    group_col: str,
    outcome_col: str,
    n_bootstrap: int = 1000,
    seed: int = 42,
    max_rows_per_group: int = 25_000,
) -> pd.DataFrame:
    """Estimate group injury-crash rates with stratified percentile bootstrap CIs.

    Capping rows per group keeps the portfolio analysis fast while preserving a
    reproducible, balanced bootstrap design.  The reported `n` is the sampled
    analytical denominator, which makes the computational choice auditable.
    """
    required = {group_col, outcome_col}
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")

    rng = np.random.default_rng(seed)
    results: list[BootstrapEstimate] = []
    clean = frame[[group_col, outcome_col]].dropna().copy()
    clean[outcome_col] = clean[outcome_col].astype(int)

    for group, group_frame in clean.groupby(group_col, observed=True):
        if group_frame.empty:
            continue
        if len(group_frame) > max_rows_per_group:
            sample_idx = rng.choice(group_frame.index.to_numpy(), size=max_rows_per_group, replace=False)
            group_frame = group_frame.loc[sample_idx]
        values = group_frame[outcome_col].to_numpy(dtype=float)
        n = len(values)
        bootstrap_draws = np.empty(n_bootstrap, dtype=float)
        for i in range(n_bootstrap):
            bootstrap_draws[i] = rng.choice(values, size=n, replace=True).mean()
        results.append(
            BootstrapEstimate(
                group=str(group),
                n=n,
                point_estimate=float(values.mean()),
                lower_ci=float(np.quantile(bootstrap_draws, 0.025)),
                upper_ci=float(np.quantile(bootstrap_draws, 0.975)),
            )
        )
    return pd.DataFrame([estimate.__dict__ for estimate in results]).sort_values("point_estimate", ascending=False)


def build_feature_pipeline(categorical_features: Sequence[str]) -> ColumnTransformer:
    """Create a stable one-hot encoding transformer for categorical crash features."""
    return ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore", drop="first", sparse_output=False), list(categorical_features))
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def fit_logistic_model(
    train: pd.DataFrame,
    categorical_features: Sequence[str],
    outcome_col: str = "injury_crash",
    seed: int = 42,
) -> Pipeline:
    """Fit a regularized multivariable logistic model for prediction and diagnostics."""
    if train[outcome_col].nunique() < 2:
        raise ValueError("The training outcome must contain both classes.")
    model = Pipeline(
        steps=[
            ("features", build_feature_pipeline(categorical_features)),
            (
                "logit",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    solver="lbfgs",
                    random_state=seed,
                ),
            ),
        ]
    )
    model.fit(train[list(categorical_features)], train[outcome_col].astype(int))
    return model


def fit_inference_logit(
    train: pd.DataFrame,
    categorical_features: Sequence[str],
    outcome_col: str = "injury_crash",
) -> tuple[sm.Logit, pd.DataFrame]:
    """Fit an unpenalized Logit model and return an odds-ratio inference table.

    The separately fitted Statsmodels model supplies conventional Wald intervals
    for transparent coefficient reporting.  It is not used to claim causality.
    """
    encoder = build_feature_pipeline(categorical_features)
    design = encoder.fit_transform(train[list(categorical_features)])
    feature_names = encoder.get_feature_names_out().tolist()
    design_frame = pd.DataFrame(design, index=train.index, columns=feature_names)
    design_frame = sm.add_constant(design_frame, has_constant="add")
    fitted = sm.Logit(train[outcome_col].astype(int), design_frame).fit(disp=False, maxiter=200)

    ci = fitted.conf_int()
    coefficient_table = pd.DataFrame(
        {
            "feature": fitted.params.index,
            "coefficient": fitted.params.values,
            "odds_ratio": np.exp(fitted.params.values),
            "lower_ci": np.exp(ci.iloc[:, 0].values),
            "upper_ci": np.exp(ci.iloc[:, 1].values),
            "p_value": fitted.pvalues.values,
        }
    )
    return fitted, coefficient_table


def evaluate_classifier(model: Pipeline, test: pd.DataFrame, categorical_features: Sequence[str], outcome_col: str = "injury_crash") -> dict[str, float]:
    """Calculate held-out discrimination and calibration summary metrics."""
    y_true = test[outcome_col].astype(int).to_numpy()
    probability = model.predict_proba(test[list(categorical_features)])[:, 1]
    return {
        "roc_auc": float(roc_auc_score(y_true, probability)),
        "average_precision": float(average_precision_score(y_true, probability)),
        "brier_score": float(brier_score_loss(y_true, probability)),
        "prevalence": float(np.mean(y_true)),
    }


def top_odds_ratios(coefficient_table: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    """Select interpretable non-intercept coefficients for a forest plot."""
    table = coefficient_table.loc[coefficient_table["feature"] != "const"].copy()
    table["distance_from_null"] = np.abs(np.log(table["odds_ratio"]))
    table = table.replace([np.inf, -np.inf], np.nan).dropna(subset=["odds_ratio", "lower_ci", "upper_ci"])
    return table.sort_values(["p_value", "distance_from_null"], ascending=[True, False]).head(n).sort_values("odds_ratio")


def monthly_rates(frame: pd.DataFrame, date_col: str = "crash_date", outcome_col: str = "injury_crash") -> pd.DataFrame:
    """Aggregate monthly injury-crash rates and Wilson confidence intervals."""
    work = frame[[date_col, outcome_col]].dropna().copy()
    work["month"] = pd.to_datetime(work[date_col]).dt.to_period("M").dt.to_timestamp()
    summary = (
        work.groupby("month", as_index=False)
        .agg(injury_crashes=(outcome_col, "sum"), crashes=(outcome_col, "size"))
    )
    intervals = wilson_interval(summary["injury_crashes"], summary["crashes"])
    return pd.concat([summary, intervals], axis=1)


def calibration_table(probabilities: Iterable[float], outcomes: Iterable[int], bins: int = 10) -> pd.DataFrame:
    """Create an equal-frequency calibration table without hidden plotting logic."""
    frame = pd.DataFrame({"probability": list(probabilities), "outcome": list(outcomes)}).dropna()
    frame["bin"] = pd.qcut(frame["probability"], q=bins, duplicates="drop")
    return (
        frame.groupby("bin", observed=True)
        .agg(mean_predicted=("probability", "mean"), observed_rate=("outcome", "mean"), n=("outcome", "size"))
        .reset_index(drop=True)
    )

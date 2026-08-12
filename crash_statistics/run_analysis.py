"""Run the reproducible Chicago crash-severity association analysis.

Example
-------
python -m crash_statistics.run_analysis --limit 100000 --refresh

The pipeline fetches official City of Chicago data, writes only derived results
into `outputs/`, and creates an auditable JSON run manifest.  It intentionally
does not make a causal claim about any feature or safety intervention.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from crash_statistics.data_pipeline import fetch_or_load, prepare_analysis_frame
from crash_statistics.statistics import (
    calibration_table,
    evaluate_classifier,
    fit_inference_logit,
    fit_logistic_model,
    monthly_rates,
    stratified_bootstrap_rates,
    top_odds_ratios,
)
from crash_statistics.visualization import (
    plot_bootstrap_groups,
    plot_diagnostics,
    plot_monthly_injury_rate,
    plot_odds_ratio_forest,
    plot_risk_heatmap,
)

FEATURES = [
    "lighting_group",
    "weather_group",
    "surface_group",
    "intersection_context",
    "speed_group",
    "daypart",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Chicago crash-statistics portfolio analysis.")
    parser.add_argument("--limit", type=int, default=120_000, help="Maximum official crash records downloaded.")
    parser.add_argument("--refresh", action="store_true", help="Refresh local public-data cache.")
    parser.add_argument("--seed", type=int, default=2026, help="Random seed for split and bootstrap sampling.")
    parser.add_argument("--bootstrap-reps", type=int, default=1000, help="Number of non-parametric bootstrap repetitions.")
    parser.add_argument("--output-dir", default=None, help="Optional result directory override.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    package_dir = Path(__file__).resolve().parent
    cache_path = package_dir / "data" / "chicago_crashes_2018_2024.csv.gz"
    output_dir = Path(args.output_dir) if args.output_dir else package_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    raw = fetch_or_load(
        cache_path,
        refresh=args.refresh,
        limit=args.limit,
        app_token=os.getenv("CHICAGO_DATA_PORTAL_APP_TOKEN"),
    )
    frame = prepare_analysis_frame(raw)
    analysis = frame.dropna(subset=FEATURES + ["injury_crash"]).copy()
    if len(analysis) < 500:
        raise ValueError("At least 500 complete analysis rows are needed for the portfolio model.")
    if analysis["injury_crash"].nunique() < 2:
        raise ValueError("The data extract contains only one outcome class.")

    train, test = train_test_split(
        analysis,
        test_size=0.25,
        stratify=analysis["injury_crash"],
        random_state=args.seed,
    )
    predictive_model = fit_logistic_model(train, FEATURES, seed=args.seed)
    _, coefficient_table = fit_inference_logit(train, FEATURES)
    evaluation = evaluate_classifier(predictive_model, test, FEATURES)
    probabilities = predictive_model.predict_proba(test[FEATURES])[:, 1]
    calibration = calibration_table(probabilities, test["injury_crash"].to_numpy())
    bootstrap = stratified_bootstrap_rates(
        analysis,
        group_col="lighting_group",
        outcome_col="injury_crash",
        n_bootstrap=args.bootstrap_reps,
        seed=args.seed,
    )
    monthly = monthly_rates(analysis)
    forest = top_odds_ratios(coefficient_table)

    coefficient_table.to_csv(output_dir / "odds_ratio_inference.csv", index=False)
    bootstrap.to_csv(output_dir / "bootstrap_lighting_rates.csv", index=False)
    monthly.to_csv(output_dir / "monthly_injury_rates.csv", index=False)
    calibration.to_csv(output_dir / "calibration_table.csv", index=False)
    plot_monthly_injury_rate(monthly, output_dir)
    plot_odds_ratio_forest(forest, output_dir)
    plot_risk_heatmap(analysis, output_dir)
    plot_diagnostics(calibration, probabilities, test["injury_crash"].to_numpy(), output_dir)
    plot_bootstrap_groups(bootstrap, output_dir)

    manifest = {
        "data_source": "City of Chicago Data Portal: Traffic Crashes - Crashes (85ca-t3if)",
        "analysis_period": {"min_crash_date": str(analysis["crash_date"].min()), "max_crash_date": str(analysis["crash_date"].max())},
        "n_downloaded": int(len(raw)),
        "n_analysis": int(len(analysis)),
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "outcome": "injury_crash = injuries_total > 0 at the crash level",
        "features": FEATURES,
        "evaluation": {key: round(value, 4) for key, value in evaluation.items()},
        "uncertainty": f"Stratified non-parametric bootstrap, {args.bootstrap_reps} repetitions, seed {args.seed}",
        "interpretation": "Associational analysis only; no causal effect is identified.",
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

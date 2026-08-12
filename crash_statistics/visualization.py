"""Publication-quality visualization functions for crash-statistics results."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import roc_curve


PALETTE = {"navy": "#0B1F3A", "blue": "#1F77B4", "teal": "#2A9D8F", "coral": "#E76F51", "gold": "#E9C46A", "gray": "#6C757D"}


def _configure_style() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "axes.labelcolor": PALETTE["navy"],
            "axes.edgecolor": "#B8C2CC",
            "grid.color": "#DDE3E9",
        }
    )


def _output_path(output_dir: str | Path, name: str) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / name


def plot_monthly_injury_rate(monthly: pd.DataFrame, output_dir: str | Path) -> Path:
    """Plot monthly injury-crash rate with Wilson 95% uncertainty band."""
    _configure_style()
    fig, ax = plt.subplots(figsize=(12, 5.5))
    y = monthly["rate"] * 100
    lower = monthly["lower_ci"] * 100
    upper = monthly["upper_ci"] * 100
    ax.fill_between(monthly["month"], lower, upper, color=PALETTE["blue"], alpha=0.18, label="Wilson 95% CI")
    ax.plot(monthly["month"], y, color=PALETTE["navy"], linewidth=2.2, label="Observed injury-crash rate")
    ax.set_title("Chicago Injury-Crash Rate Over Time")
    ax.set_ylabel("Injury crashes (% of reported crashes)")
    ax.set_xlabel("Crash month")
    ax.legend(frameon=True, loc="best")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = _output_path(output_dir, "monthly_injury_rate.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_odds_ratio_forest(odds_ratios: pd.DataFrame, output_dir: str | Path) -> Path:
    """Plot adjusted odds ratios with conventional 95% Wald confidence intervals."""
    _configure_style()
    table = odds_ratios.copy().sort_values("odds_ratio")
    labels = table["feature"].str.replace("_", " ", regex=False).str.title()
    y = np.arange(len(table))
    fig, ax = plt.subplots(figsize=(10, max(5.5, len(table) * 0.55)))
    ax.errorbar(
        table["odds_ratio"],
        y,
        xerr=[table["odds_ratio"] - table["lower_ci"], table["upper_ci"] - table["odds_ratio"]],
        fmt="o",
        color=PALETTE["coral"],
        ecolor=PALETTE["gray"],
        capsize=3,
        linewidth=1.5,
    )
    ax.axvline(1.0, color=PALETTE["navy"], linestyle="--", linewidth=1.2, label="No adjusted association")
    ax.set_xscale("log")
    ax.set_yticks(y, labels)
    ax.set_xlabel("Adjusted odds ratio (log scale, 95% Wald CI)")
    ax.set_title("Statistical Associations With Injury-Crash Involvement")
    ax.legend(frameon=True)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = _output_path(output_dir, "adjusted_odds_ratio_forest.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_risk_heatmap(frame: pd.DataFrame, output_dir: str | Path) -> Path:
    """Show empirical injury-risk patterns by temporal and lighting condition."""
    _configure_style()
    table = frame.pivot_table(index="daypart", columns="lighting_group", values="injury_crash", aggfunc="mean") * 100
    daypart_order = ["LATE_NIGHT", "AM_PEAK", "MIDDAY", "PM_PEAK", "EVENING", "UNKNOWN"]
    table = table.reindex([item for item in daypart_order if item in table.index])
    fig, ax = plt.subplots(figsize=(10, 5.5))
    sns.heatmap(
        table,
        annot=True,
        fmt=".1f",
        cmap=sns.color_palette("mako", as_cmap=True),
        linewidths=0.8,
        linecolor="white",
        cbar_kws={"label": "Injury-crash rate (%)"},
        ax=ax,
    )
    ax.set_title("Observed Injury-Crash Rates by Time and Lighting")
    ax.set_xlabel("Lighting condition")
    ax.set_ylabel("Time-of-day category")
    ax.set_yticklabels([label.replace("_", " ").title() for label in table.index], rotation=0)
    ax.set_xticklabels([label.replace("_", " ").title() for label in table.columns], rotation=20, ha="right")
    fig.tight_layout()
    path = _output_path(output_dir, "risk_heatmap.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_diagnostics(calibration: pd.DataFrame, probabilities: np.ndarray, outcomes: np.ndarray, output_dir: str | Path) -> Path:
    """Plot calibration and ROC curves on a held-out test partition."""
    _configure_style()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    axes[0].plot([0, 1], [0, 1], linestyle="--", color=PALETTE["gray"], label="Perfect calibration")
    axes[0].plot(calibration["mean_predicted"], calibration["observed_rate"], marker="o", color=PALETTE["teal"], linewidth=2)
    axes[0].set_title("Held-out Calibration")
    axes[0].set_xlabel("Mean predicted probability")
    axes[0].set_ylabel("Observed injury-crash rate")
    axes[0].legend(frameon=True)

    false_positive_rate, true_positive_rate, _ = roc_curve(outcomes, probabilities)
    axes[1].plot(false_positive_rate, true_positive_rate, color=PALETTE["coral"], linewidth=2.2, label="Logistic model")
    axes[1].plot([0, 1], [0, 1], linestyle="--", color=PALETTE["gray"], label="No discrimination")
    axes[1].set_title("Held-out Discrimination")
    axes[1].set_xlabel("False-positive rate")
    axes[1].set_ylabel("True-positive rate")
    axes[1].legend(frameon=True)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Model Validation: Calibration and Discrimination", y=1.02, fontweight="bold")
    fig.tight_layout()
    path = _output_path(output_dir, "model_diagnostics.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_bootstrap_groups(bootstrap: pd.DataFrame, output_dir: str | Path) -> Path:
    """Plot group rates with non-parametric bootstrap confidence intervals."""
    _configure_style()
    table = bootstrap.sort_values("point_estimate")
    y = np.arange(len(table))
    fig, ax = plt.subplots(figsize=(9, max(4.5, len(table) * 0.7)))
    estimate = table["point_estimate"] * 100
    lower = table["lower_ci"] * 100
    upper = table["upper_ci"] * 100
    ax.errorbar(
        estimate,
        y,
        xerr=[estimate - lower, upper - estimate],
        fmt="o",
        color=PALETTE["blue"],
        ecolor=PALETTE["gray"],
        capsize=3,
    )
    ax.set_yticks(y, table["group"].str.replace("_", " ").str.title())
    ax.set_xlabel("Injury-crash rate (%) with 95% bootstrap CI")
    ax.set_title("Uncertainty-Aware Injury-Crash Rate Comparison")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = _output_path(output_dir, "bootstrap_rate_comparison.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path

"""Publication-quality GIS visualizations for the planning-screen outputs."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titleweight": "bold"})


def _save(fig: plt.Figure, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_accessibility_map(study: gpd.GeoDataFrame, output_path: Path) -> None:
    """Map baseline 30-minute job access, marking equity-priority tracts."""
    fig, ax = plt.subplots(figsize=(8.5, 9))
    study.plot(
        column="jobs_access_30min", cmap="viridis", legend=True,
        linewidth=0.25, edgecolor="white", ax=ax,
        legend_kwds={"label": "Accessible employment within 30 minutes"},
    )
    priority = study.loc[study["equity_priority"] == 1]
    if not priority.empty:
        priority.boundary.plot(ax=ax, color="#D62728", linewidth=0.85, label="Equity-priority tract")
        ax.legend(loc="lower left", frameon=True)
    ax.set_title("Employment Accessibility and Equity Priority\nOpen-data planning screen")
    ax.set_axis_off()
    _save(fig, output_path)


def plot_scenario_change_map(study: gpd.GeoDataFrame, output_path: Path) -> None:
    """Map change in 30-minute job access under the documented sensitivity case."""
    max_abs = max(float(study["scenario_access_change"].abs().max()), 1.0)
    fig, ax = plt.subplots(figsize=(8.5, 9))
    study.plot(
        column="scenario_access_change", cmap="RdYlGn", vmin=-max_abs, vmax=max_abs,
        legend=True, linewidth=0.25, edgecolor="white", ax=ax,
        legend_kwds={"label": "Change in accessible employment within 30 minutes"},
    )
    ax.set_title("Scenario Sensitivity: Accessibility Change\n20% generalized-cost reduction for 12–30 minute OD pairs")
    ax.set_axis_off()
    _save(fig, output_path)


def plot_equity_distribution(study: pd.DataFrame, output_path: Path) -> None:
    """Contrast access distributions between equity-priority and other tracts."""
    labels = np.where(study["equity_priority"] == 1, "Equity-priority", "Other tracts")
    figure, ax = plt.subplots(figsize=(8.5, 5.2))
    for label, color in (("Other tracts", "#4C78A8"), ("Equity-priority", "#E45756")):
        values = study.loc[labels == label, "jobs_access_30min"]
        ax.hist(values, bins=16, alpha=0.60, label=label, color=color, density=True)
    ax.set_title("Distribution of 30-Minute Employment Accessibility")
    ax.set_xlabel("Accessible employment")
    ax.set_ylabel("Density of Census tracts")
    ax.legend(frameon=True)
    _save(figure, output_path)


def create_all_figures(gpkg_path: Path, output_dir: Path) -> None:
    """Render all standard figures from a saved planning-screen GeoPackage."""
    study = gpd.read_file(gpkg_path)
    plot_accessibility_map(study, output_dir / "accessibility_equity_map.png")
    plot_scenario_change_map(study, output_dir / "scenario_access_change_map.png")
    plot_equity_distribution(study, output_dir / "equity_access_distribution.png")


if __name__ == "__main__":
    package_dir = Path(__file__).resolve().parent
    create_all_figures(package_dir / "outputs" / "planning_screen.gpkg", package_dir / "outputs")

"""Deterministic, report-ready visualizations for the SUMO operations screen."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

PALETTE = {"baseline": "#5B7083", "peak_retimed": "#007C91"}


def _style() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams.update({"figure.dpi": 140, "savefig.dpi": 300, "axes.titleweight": "bold", "font.family": "DejaVu Sans"})


def plot_input_audit(profile: pd.DataFrame, demand: pd.DataFrame, output_path: str | Path) -> None:
    """Show the observed count separately from modeled input assumptions."""

    _style()
    output_path = Path(output_path)
    quarters = profile["timestamp"].dt.strftime("%H:%M").tolist()
    observed = profile["volume_15min"].to_numpy()
    movement_order = ["north_to_south", "south_to_north", "east_to_west", "west_to_east"]
    pivot = demand.pivot(index="begin_s", columns="movement", values="vehicles_15min").reindex(columns=movement_order).sort_index()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.3), gridspec_kw={"width_ratios": [1.0, 1.15]})
    ax1.plot(quarters, observed, marker="o", linewidth=2.5, color="#1C4966", label="Observed NYC DOT ATR movement")
    ax1.fill_between(range(len(observed)), observed * 0.95, observed * 1.05, color="#1C4966", alpha=0.14, label="±5% display band")
    ax1.set(title="Official 15-minute ATR profile", xlabel="Observation quarter-hour", ylabel="Vehicles / 15 min")
    ax1.legend(frameon=True, fontsize=10)
    ax1.text(0.02, 0.03, "Band is visual context only; it is not a sensor error estimate.", transform=ax1.transAxes, fontsize=9)

    colors = ["#1C4966", "#73A6C2", "#F0B44D", "#C7802E"]
    pivot.plot(kind="bar", stacked=True, color=colors, ax=ax2, width=0.78)
    ax2.set(title="SUMO input audit: observed vs. assumed movements", xlabel="Simulation interval (minutes)", ylabel="Vehicles / 15 min")
    ax2.set_xticklabels([f"{int(v / 60)}–{int(v / 60 + 15)}" for v in pivot.index], rotation=0)
    ax2.legend(title="Movement", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    fig.text(0.59, 0.015, "Only north_to_south is observed. Other movements are explicit screening assumptions.", ha="center", fontsize=9)
    fig.subplots_adjust(bottom=0.22, right=0.86, wspace=0.24)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def plot_kpi_comparison(kpis: pd.DataFrame, output_path: str | Path) -> None:
    """Compare central KPI results across seed replications without false precision."""

    _style()
    metrics = [
        ("mean_delay_s", "Mean time loss (s/trip)"),
        ("mean_stopped_delay_s", "Mean stopped delay (s/trip)"),
        ("mean_queue_proxy_veh", "Mean queue proxy (veh)"),
        ("total_co2_g", "Total CO$_2$ (g/run)"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, (metric, label) in zip(axes.flat, metrics):
        rows = []
        for scenario, values in kpis.groupby("scenario"):
            value = values[metric].dropna().to_numpy()
            rows.append((scenario, value.mean(), np.quantile(value, 0.025), np.quantile(value, 0.975)))
        rows.sort(key=lambda x: x[0])
        for i, (scenario, mean, lo, hi) in enumerate(rows):
            ax.errorbar(i, mean, yerr=[[mean - lo], [hi - mean]], fmt="o", capsize=6, markersize=9, color=PALETTE[scenario], linewidth=2)
            ax.scatter(np.full(len(kpis[kpis.scenario == scenario]), i) + np.linspace(-0.08, 0.08, len(kpis[kpis.scenario == scenario])), kpis.loc[kpis.scenario == scenario, metric], color=PALETTE[scenario], alpha=0.35, s=38)
        ax.set_xticks(range(len(rows)), [r[0].replace("_", " ").title() for r in rows])
        ax.set_ylabel(label)
        ax.set_title(label)
        ax.text(0.02, 0.02, "Point = seed mean; bar = empirical 2.5–97.5 percentile", transform=ax.transAxes, fontsize=8.8)
    fig.suptitle("SUMO operations screen: scenario comparison with seed uncertainty", y=1.02, fontsize=17, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def plot_queue_trajectory(queues: pd.DataFrame, output_path: str | Path) -> None:
    """Plot mean detector queue proxy by scenario and time."""

    _style()
    grouped = queues.groupby(["scenario", "end_s"], as_index=False).agg(
        mean_queue=("mean_queue_veh", "mean"), low=("mean_queue_veh", lambda x: np.quantile(x, 0.025)), high=("mean_queue_veh", lambda x: np.quantile(x, 0.975))
    )
    fig, ax = plt.subplots(figsize=(12.5, 5.5))
    for scenario, frame in grouped.groupby("scenario"):
        x, mean, low, high = (frame["end_s"].to_numpy() / 60, frame["mean_queue"].to_numpy(), frame["low"].to_numpy(), frame["high"].to_numpy())
        ax.plot(x, mean, label=scenario.replace("_", " ").title(), color=PALETTE[scenario], linewidth=2.5)
        ax.fill_between(x, low, high, color=PALETTE[scenario], alpha=0.16)
    ax.set(title="Queue proxy trajectory across incoming detector lanes", xlabel="Simulation time (minutes)", ylabel="Mean max jam length (vehicles)")
    ax.legend(title="Signal policy")
    ax.text(0.01, 0.02, "Detector queue proxy is a screening metric, not a field-observed queue validation result.", transform=ax.transAxes, fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def make_all_figures(project_dir: str | Path) -> list[Path]:
    """Generate and return the three portfolio visualizations."""

    project_dir = Path(project_dir)
    output = project_dir / "outputs"
    profile = pd.read_csv(output / "public_atr_profile.csv", parse_dates=["timestamp"])
    demand = pd.read_csv(output / "sumo_demand_input_audit.csv")
    kpis = pd.read_csv(output / "seed_level_kpis.csv")
    queues = pd.read_csv(output / "queue_detector_results.csv")
    paths = [output / "01_input_audit.png", output / "02_kpi_comparison.png", output / "03_queue_trajectory.png"]
    plot_input_audit(profile, demand, paths[0])
    plot_kpi_comparison(kpis, paths[1])
    plot_queue_trajectory(queues, paths[2])
    return paths


if __name__ == "__main__":
    make_all_figures(Path(__file__).resolve().parent)

"""Parse SUMO outputs into documented operational and environmental KPIs."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


def _float(element: ET.Element, attribute: str, default: float = 0.0) -> float:
    return float(element.attrib.get(attribute, default))


def parse_tripinfo(tripinfo_path: str | Path, scenario: str, seed: int) -> pd.DataFrame:
    """Parse completed-trip outcomes and embedded HBEFA emissions."""

    root = ET.parse(tripinfo_path).getroot()
    rows = []
    for trip in root.findall("tripinfo"):
        emissions = trip.find("emissions")
        row = {
            "scenario": scenario,
            "seed": int(seed),
            "vehicle_id": trip.attrib.get("id"),
            "duration_s": _float(trip, "duration"),
            "time_loss_s": _float(trip, "timeLoss"),
            "waiting_time_s": _float(trip, "waitingTime"),
            "depart_delay_s": _float(trip, "departDelay"),
            "route_length_m": _float(trip, "routeLength"),
            "co2_mg": _float(emissions, "CO2_abs") if emissions is not None else np.nan,
            "nox_mg": _float(emissions, "NOx_abs") if emissions is not None else np.nan,
            "fuel_mg": _float(emissions, "fuel_abs") if emissions is not None else np.nan,
        }
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["scenario", "seed", "vehicle_id", "duration_s", "time_loss_s"])
    return pd.DataFrame(rows)


def parse_lanearea(lanearea_path: str | Path, scenario: str, seed: int) -> pd.DataFrame:
    """Extract 60-second queue proxies from lane-area detector intervals."""

    root = ET.parse(lanearea_path).getroot()
    rows = []
    for item in root.findall("interval"):
        rows.append(
            {
                "scenario": scenario,
                "seed": int(seed),
                "detector": item.attrib.get("id"),
                "begin_s": _float(item, "begin"),
                "end_s": _float(item, "end"),
                "mean_queue_veh": _float(item, "meanMaxJamLengthInVehicles"),
                "max_queue_veh": _float(item, "maxJamLengthInVehicles"),
                "mean_halts": _float(item, "meanHaltsPerVehicle"),
            }
        )
    return pd.DataFrame(rows)


def run_kpis(trips: pd.DataFrame, lanearea: pd.DataFrame) -> pd.DataFrame:
    """Aggregate completed trips; label queue measures as detector proxies."""

    if trips.empty:
        raise ValueError("No completed trips were recorded; inspect demand, simulation horizon, and network connectivity.")
    group = trips.groupby(["scenario", "seed"], as_index=False).agg(
        completed_trips=("vehicle_id", "nunique"),
        mean_travel_time_s=("duration_s", "mean"),
        mean_delay_s=("time_loss_s", "mean"),
        mean_stopped_delay_s=("waiting_time_s", "mean"),
        mean_depart_delay_s=("depart_delay_s", "mean"),
        vehicle_km=("route_length_m", lambda x: x.sum() / 1000.0),
        total_co2_g=("co2_mg", lambda x: x.sum(skipna=True) / 1000.0),
        total_nox_g=("nox_mg", lambda x: x.sum(skipna=True) / 1000.0),
        total_fuel_g=("fuel_mg", lambda x: x.sum(skipna=True) / 1000.0),
    )
    if lanearea.empty:
        group["mean_queue_proxy_veh"] = np.nan
        group["max_queue_proxy_veh"] = np.nan
    else:
        queues = lanearea.groupby(["scenario", "seed"], as_index=False).agg(
            mean_queue_proxy_veh=("mean_queue_veh", "mean"),
            max_queue_proxy_veh=("max_queue_veh", "max"),
        )
        group = group.merge(queues, on=["scenario", "seed"], how="left")
    return group


def summarize_runs(kpis: pd.DataFrame) -> pd.DataFrame:
    """Return seed-level mean and percentile intervals for each scenario KPI."""

    id_columns = {"scenario", "seed"}
    records: list[dict[str, float | str]] = []
    for scenario, frame in kpis.groupby("scenario"):
        for metric in [c for c in frame.columns if c not in id_columns]:
            values = frame[metric].dropna().to_numpy(dtype=float)
            if len(values) == 0:
                continue
            records.append(
                {
                    "scenario": scenario,
                    "metric": metric,
                    "mean": values.mean(),
                    "p02_5": np.quantile(values, 0.025),
                    "p97_5": np.quantile(values, 0.975),
                    "n_replications": len(values),
                }
            )
    return pd.DataFrame(records)


def compare_to_baseline(kpis: pd.DataFrame, baseline: str = "baseline") -> pd.DataFrame:
    """Compute paired seed-wise deltas versus baseline, avoiding a causal claim."""

    numeric = [c for c in kpis.columns if c not in {"scenario", "seed"}]
    baseline_frame = kpis.loc[kpis["scenario"] == baseline, ["seed", *numeric]].set_index("seed")
    rows = []
    for scenario, frame in kpis.groupby("scenario"):
        if scenario == baseline:
            continue
        joined = frame.set_index("seed")[numeric].join(baseline_frame, lsuffix="", rsuffix="_baseline", how="inner")
        for metric in numeric:
            delta = joined[metric] - joined[f"{metric}_baseline"]
            if delta.notna().any():
                rows.append(
                    {
                        "scenario": scenario,
                        "metric": metric,
                        "mean_delta_vs_baseline": delta.mean(),
                        "p02_5_delta": delta.quantile(0.025),
                        "p97_5_delta": delta.quantile(0.975),
                        "percent_change_vs_baseline": 100 * delta.mean() / baseline_frame[metric].mean(),
                        "n_paired_seeds": int(delta.notna().sum()),
                    }
                )
    return pd.DataFrame(rows)


def write_run_manifest(path: str | Path, payload: dict) -> None:
    """Persist the assumptions, source query, commands, and outputs of a run."""

    Path(path).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

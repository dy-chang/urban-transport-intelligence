"""Accessibility, equity, and scenario-screening measures for DOT/MPO planning."""

from __future__ import annotations

from typing import Iterable, Mapping, Optional, Sequence

import numpy as np
import pandas as pd


EQUITY_COMPONENTS = (
    "low_income_share",
    "zero_vehicle_share",
    "non_white_share",
)


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Divide with explicit zero-denominator handling."""
    return numerator.div(denominator.replace(0, np.nan)).fillna(0.0)


def build_equity_index(frame: pd.DataFrame) -> pd.DataFrame:
    """Construct a transparent, non-diagnostic equity-screening index.

    The index is the mean of three shares: residents below poverty, households
    without a vehicle, and population that is not non-Hispanic White. Agencies
    should replace this with their adopted Environmental Justice / Title VI
    criteria before using it in a formal decision process.
    """
    required = {
        "population",
        "population_below_poverty",
        "households",
        "households_no_vehicle",
        "non_hispanic_white_population",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing columns for equity screen: {sorted(missing)}")
    result = frame.copy()
    result["low_income_share"] = safe_divide(result["population_below_poverty"], result["population"])
    result["zero_vehicle_share"] = safe_divide(result["households_no_vehicle"], result["households"])
    result["non_white_share"] = 1.0 - safe_divide(result["non_hispanic_white_population"], result["population"])
    result["equity_screen_score"] = result[list(EQUITY_COMPONENTS)].mean(axis=1)
    result["equity_priority"] = (result["equity_screen_score"] >= result["equity_screen_score"].median()).astype(int)
    return result


def cumulative_accessibility(
    opportunity_vector: Sequence[float],
    impedance_minutes: np.ndarray,
    cutoff_minutes: float = 30.0,
) -> np.ndarray:
    """Calculate opportunities reachable within a specified time threshold."""
    opportunities = np.asarray(opportunity_vector, dtype=float)
    impedance = np.asarray(impedance_minutes, dtype=float)
    if impedance.shape != (len(opportunities), len(opportunities)):
        raise ValueError("Impedance matrix dimensions must match opportunities.")
    if cutoff_minutes <= 0:
        raise ValueError("Cutoff must be positive.")
    return (impedance <= cutoff_minutes).astype(float) @ opportunities


def gravity_accessibility(
    opportunity_vector: Sequence[float],
    impedance_minutes: np.ndarray,
    beta: float = 0.08,
) -> np.ndarray:
    """Calculate gravity-based opportunity access using exponential decay."""
    opportunities = np.asarray(opportunity_vector, dtype=float)
    impedance = np.asarray(impedance_minutes, dtype=float)
    if impedance.shape != (len(opportunities), len(opportunities)):
        raise ValueError("Impedance matrix dimensions must match opportunities.")
    return np.exp(-beta * impedance) @ opportunities


def summarize_equity_gap(
    frame: pd.DataFrame,
    measure: str = "jobs_access_30min",
    priority_flag: str = "equity_priority",
    population_weight: str = "population",
) -> pd.DataFrame:
    """Summarize weighted access differences between priority and other tracts."""
    required = {measure, priority_flag, population_weight}
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing columns for equity summary: {sorted(missing)}")
    rows = []
    for label, subset in frame.groupby(priority_flag, dropna=False):
        weights = subset[population_weight].clip(lower=0)
        weighted_average = np.average(subset[measure], weights=weights) if weights.sum() else np.nan
        rows.append({
            "group": "equity_priority" if label == 1 else "other_tracts",
            "tracts": int(len(subset)),
            "population": float(weights.sum()),
            f"weighted_mean_{measure}": float(weighted_average),
        })
    summary = pd.DataFrame(rows)
    if len(summary) == 2:
        values = summary.set_index("group")[f"weighted_mean_{measure}"]
        gap = values.get("equity_priority", np.nan) - values.get("other_tracts", np.nan)
        summary["priority_minus_other_gap"] = gap
    return summary


def time_reduction_scenario(
    impedance_minutes: np.ndarray,
    improvement_mask: np.ndarray,
    reduction_fraction: float,
) -> np.ndarray:
    """Apply a documented generalized-cost scenario for early project screening.

    ``improvement_mask`` identifies OD pairs affected by a hypothetical transit,
    active-transportation, or corridor investment. The function does not claim
    a real project effect; it makes the sensitivity assumption inspectable.
    """
    impedance = np.asarray(impedance_minutes, dtype=float).copy()
    mask = np.asarray(improvement_mask, dtype=bool)
    if impedance.shape != mask.shape:
        raise ValueError("Improvement mask must match impedance matrix dimensions.")
    if not 0 <= reduction_fraction < 1:
        raise ValueError("Reduction fraction must be in [0, 1).")
    impedance[mask] *= 1.0 - reduction_fraction
    return impedance

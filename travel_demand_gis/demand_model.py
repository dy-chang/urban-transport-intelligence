"""Transparent aggregate travel-demand model components.

This module implements a production-attraction gravity model suitable for
sketch planning or scenario screening. For final project decisions, impedance,
trip ends, and validation targets should be replaced with locally calibrated
network skim matrices and observed counts / OD data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


@dataclass
class GravityModel:
    """Doubly constrained gravity model solved with iterative proportional fitting."""

    beta: float = 0.08
    max_iterations: int = 1_000
    convergence_tolerance: float = 1e-7

    def deterrence(self, impedance_minutes: np.ndarray) -> np.ndarray:
        """Return a negative-exponential impedance factor matrix."""
        impedance = np.asarray(impedance_minutes, dtype=float)
        if impedance.ndim != 2:
            raise ValueError("Impedance matrix must be two-dimensional.")
        if np.any(impedance < 0) or not np.isfinite(impedance).all():
            raise ValueError("Impedance values must be finite and non-negative.")
        return np.exp(-self.beta * impedance)

    def fit_predict(
        self,
        productions: Sequence[float],
        attractions: Sequence[float],
        impedance_minutes: np.ndarray,
    ) -> np.ndarray:
        """Balance OD flows to exact production and attraction marginals.

        The solution begins with the friction-factor prior and alternates row
        and column scaling. It is mathematically equivalent to IPF/Furness
        balancing of a seed matrix.
        """
        p = np.asarray(productions, dtype=float)
        a = np.asarray(attractions, dtype=float)
        if p.ndim != 1 or a.ndim != 1 or len(p) != len(a):
            raise ValueError("Productions and attractions must be equally sized one-dimensional arrays.")
        if np.any(p < 0) or np.any(a < 0):
            raise ValueError("Trip ends must be non-negative.")
        if not np.isclose(p.sum(), a.sum(), rtol=1e-6, atol=1e-6):
            raise ValueError("Productions and attractions must sum to the same total.")

        friction = self.deterrence(impedance_minutes)
        if friction.shape != (len(p), len(a)):
            raise ValueError("Impedance dimensions must match number of zones.")
        seed = np.outer(np.maximum(p, 1e-12), np.maximum(a, 1e-12)) * friction
        flows = seed.copy()

        for iteration in range(self.max_iterations):
            row_totals = flows.sum(axis=1)
            row_scale = np.divide(p, row_totals, out=np.ones_like(p), where=row_totals > 0)
            flows *= row_scale[:, None]

            column_totals = flows.sum(axis=0)
            column_scale = np.divide(a, column_totals, out=np.ones_like(a), where=column_totals > 0)
            flows *= column_scale[None, :]

            max_error = max(
                np.max(np.abs(flows.sum(axis=1) - p)),
                np.max(np.abs(flows.sum(axis=0) - a)),
            )
            if max_error <= self.convergence_tolerance * max(1.0, p.sum()):
                return flows
        raise RuntimeError("Gravity model did not converge; inspect zero trip ends or impedance matrix.")


def calibrate_beta(
    productions: Sequence[float],
    attractions: Sequence[float],
    impedance_minutes: np.ndarray,
    observed_mean_impedance: float,
    candidates: Iterable[float] = np.linspace(0.01, 0.25, 49),
) -> Tuple[float, pd.DataFrame]:
    """Select friction beta by matching observed mean trip impedance.

    This light-weight one-dimensional calibration is useful when a regional
    model lacks a full survey-based estimation process. The returned audit
    table should be retained with model documentation.
    """
    observed_mean_impedance = float(observed_mean_impedance)
    if observed_mean_impedance <= 0:
        raise ValueError("Observed mean impedance must be positive.")
    rows = []
    for beta in candidates:
        model = GravityModel(beta=float(beta))
        flows = model.fit_predict(productions, attractions, impedance_minutes)
        modeled_mean = float((flows * impedance_minutes).sum() / flows.sum())
        rows.append({
            "beta": float(beta),
            "modeled_mean_impedance": modeled_mean,
            "absolute_error": abs(modeled_mean - observed_mean_impedance),
        })
    diagnostics = pd.DataFrame(rows).sort_values("absolute_error").reset_index(drop=True)
    return float(diagnostics.loc[0, "beta"]), diagnostics


def haversine_time_matrix(
    longitude: Sequence[float],
    latitude: Sequence[float],
    assumed_speed_kph: float = 30.0,
    circuity_factor: float = 1.25,
) -> np.ndarray:
    """Build an auditable sketch-planning time matrix from zone centroids.

    The resulting matrix is intentionally a screening approximation. MPO/DOT
    production models should replace it with a network / GTFS skim matrix.
    """
    lon = np.radians(np.asarray(longitude, dtype=float))
    lat = np.radians(np.asarray(latitude, dtype=float))
    if len(lon) != len(lat) or assumed_speed_kph <= 0 or circuity_factor < 1:
        raise ValueError("Invalid centroid coordinates or impedance assumptions.")
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    km = 2 * 6_371.0088 * np.arcsin(np.sqrt(a)) * circuity_factor
    minutes = km / assumed_speed_kph * 60.0
    np.fill_diagonal(minutes, 1.0)
    return minutes

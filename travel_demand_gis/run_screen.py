"""Run an open-data DOT/MPO travel-demand and accessibility planning screen.

Example
-------
python -m travel_demand_gis.run_screen --state 11 --county 001 --state-abbr dc

The default geography is Washington, DC because it is compact enough for a
portfolio example. Replace state/county codes with an MPO's study area and use
locally adopted network skims before formal planning application.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Tuple

import geopandas as gpd
import numpy as np
import pandas as pd

from .data_sources import ACSClient, CensusGeometryClient
from .demand_model import GravityModel, calibrate_beta, haversine_time_matrix
from .lodes import LODESClient, aggregate_od_to_tract
from .planning_metrics import (
    build_equity_index,
    cumulative_accessibility,
    gravity_accessibility,
    summarize_equity_gap,
    time_reduction_scenario,
)


def _build_trip_ends_from_lodes(zone_ids: pd.Series, state_abbr: str, year: int, cache_dir: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Derive regional production and attraction marginals from public LODES OD flows."""
    lodes = LODESClient(state_abbreviation=state_abbr, year=year, cache_dir=cache_dir)
    od = aggregate_od_to_tract(lodes.get_main_od())
    zone_set = set(zone_ids)
    od = od.loc[od["origin_geoid"].isin(zone_set) & od["destination_geoid"].isin(zone_set)].copy()
    if od.empty:
        raise ValueError("No within-study-area LODES OD flows found for the selected geography.")
    productions = od.groupby("origin_geoid")["flow"].sum().reindex(zone_ids, fill_value=0.0).to_numpy(dtype=float)
    attractions = od.groupby("destination_geoid")["flow"].sum().reindex(zone_ids, fill_value=0.0).to_numpy(dtype=float)
    return productions, attractions


def execute_screen(
    state_fips: str,
    county_fips: str,
    state_abbr: str,
    acs_year: int,
    lodes_year: int,
    base_dir: Path,
    use_lodes: bool = True,
) -> tuple[gpd.GeoDataFrame, dict, pd.DataFrame]:
    """Execute data acquisition, model construction, and planning indicators."""
    data_dir = base_dir / "data"
    acs = ACSClient(year=acs_year, cache_dir=data_dir).get_tract_features(state_fips, county_fips)
    tracts = CensusGeometryClient(year=acs_year, cache_dir=data_dir).get_state_tracts(state_fips)
    tracts["geoid"] = tracts["geoid"].astype(str)
    study = tracts.loc[tracts["COUNTYFP"] == county_fips.zfill(3)].merge(acs, on="geoid", how="inner")
    study = study.loc[study.geometry.notna() & (study["workers"].fillna(0) > 0)].copy()
    if len(study) < 2:
        raise ValueError("The selected geography must contain at least two populated Census tracts.")
    study = build_equity_index(study)

    projected = study.to_crs("EPSG:3857")
    centroids = projected.geometry.centroid.to_crs("EPSG:4326")
    impedance = haversine_time_matrix(centroids.x, centroids.y, assumed_speed_kph=30.0, circuity_factor=1.25)
    zone_ids = study["geoid"].astype(str).reset_index(drop=True)
    study = study.reset_index(drop=True)

    if use_lodes:
        productions, attractions = _build_trip_ends_from_lodes(zone_ids, state_abbr, lodes_year, data_dir)
    else:
        # Explicit fallback only for demonstrating code flow when LODES coverage
        # is unavailable; it is not a substitute for observed workplace totals.
        productions = study["workers"].fillna(0.0).to_numpy(dtype=float)
        attractions = productions.copy()

    total = min(productions.sum(), attractions.sum())
    if total <= 0:
        raise ValueError("Trip-end totals are zero; inspect the selected data inputs.")
    # Ensure equal marginals for a closed, within-study-area gravity model.
    productions = productions * (total / productions.sum())
    attractions = attractions * (total / attractions.sum())
    observed_mean = np.average(
        study["mean_commute_minutes"].clip(lower=1.0),
        weights=study["workers"].clip(lower=0.0),
    )
    beta, calibration = calibrate_beta(productions, attractions, impedance, observed_mean)
    flows = GravityModel(beta=beta).fit_predict(productions, attractions, impedance)

    jobs = attractions
    study["productions_lodes"] = productions
    study["attractions_lodes"] = attractions
    study["jobs_access_30min"] = cumulative_accessibility(jobs, impedance, cutoff_minutes=30.0)
    study["jobs_access_gravity"] = gravity_accessibility(jobs, impedance, beta=beta)

    # Illustrative project-screening sensitivity: reduce generalized cost on
    # OD pairs already near the 30-minute access threshold.
    improvement_mask = (impedance >= 12.0) & (impedance <= 30.0)
    scenario_impedance = time_reduction_scenario(impedance, improvement_mask, reduction_fraction=0.20)
    scenario_access = cumulative_accessibility(jobs, scenario_impedance, cutoff_minutes=30.0)
    study["scenario_jobs_access_30min"] = scenario_access
    study["scenario_access_change"] = scenario_access - study["jobs_access_30min"]

    equity_summary = summarize_equity_gap(study, measure="jobs_access_30min")
    scenario_summary = summarize_equity_gap(study.assign(jobs_access_30min=scenario_access), measure="jobs_access_30min")
    summary = {
        "geography": {"state_fips": state_fips, "county_fips": county_fips, "tract_count": int(len(study))},
        "data_years": {"acs": acs_year, "lodes": lodes_year if use_lodes else None},
        "method": {
            "model": "doubly constrained negative-exponential gravity model",
            "calibrated_beta": beta,
            "observed_mean_commute_minutes": float(observed_mean),
            "impedance": "centroid haversine distance x 1.25 circuity at 30 kph; replace with network skim",
            "scenario": "20% generalized-cost reduction for OD pairs with baseline impedance of 12-30 minutes",
        },
        "demand": {
            "within_area_trip_ends": float(productions.sum()),
            "modeled_mean_impedance_minutes": float((flows * impedance).sum() / flows.sum()),
        },
        "equity_baseline": equity_summary.to_dict(orient="records"),
        "equity_scenario": scenario_summary.to_dict(orient="records"),
    }
    return study, summary, calibration


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an open-data DOT/MPO demand and access planning screen.")
    parser.add_argument("--state", default="11", help="Two-digit Census state FIPS (default: DC=11).")
    parser.add_argument("--county", default="001", help="Three-digit Census county FIPS (default: DC=001).")
    parser.add_argument("--state-abbr", default="dc", help="Two-letter LODES state abbreviation (default: dc).")
    parser.add_argument("--acs-year", default=2023, type=int, help="ACS 5-year release year.")
    parser.add_argument("--lodes-year", default=2022, type=int, help="LODES release year.")
    parser.add_argument("--without-lodes", action="store_true", help="Use ACS workers for both trip ends when LODES is unavailable.")
    parser.add_argument("--output", default="outputs", help="Output directory relative to this package.")
    args = parser.parse_args()

    package_dir = Path(__file__).resolve().parent
    output_dir = package_dir / args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    study, summary, calibration = execute_screen(
        args.state, args.county, args.state_abbr, args.acs_year, args.lodes_year,
        package_dir, use_lodes=not args.without_lodes,
    )
    study.to_file(output_dir / "planning_screen.gpkg", driver="GPKG")
    study.drop(columns="geometry").to_csv(output_dir / "tract_metrics.csv", index=False)
    calibration.to_csv(output_dir / "gravity_calibration.csv", index=False)
    (output_dir / "screen_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

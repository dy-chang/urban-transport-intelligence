"""Public-data acquisition and feature engineering for Chicago crash analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd
import requests

CRASHES_ENDPOINT: Final[str] = "https://data.cityofchicago.org/resource/85ca-t3if.json"
DEFAULT_FIELDS: Final[list[str]] = [
    "crash_record_id",
    "crash_date",
    "posted_speed_limit",
    "weather_condition",
    "lighting_condition",
    "trafficway_type",
    "traffic_control_device",
    "roadway_surface_cond",
    "injuries_total",
    "injuries_fatal",
    "injuries_incapacitating",
    "injuries_non_incapacitating",
    "injuries_reported_not_evident",
    "injuries_no_indication",
    "injuries_unknown",
    "crash_hour",
    "crash_day_of_week",
    "crash_month",
    "latitude",
    "longitude",
]


def query_crashes(
    start_date: str = "2018-01-01T00:00:00.000",
    end_date: str = "2025-01-01T00:00:00.000",
    limit: int = 150_000,
    app_token: str | None = None,
    timeout_seconds: int = 60,
) -> pd.DataFrame:
    """Download a completed analysis period from the official Socrata endpoint.

    The request selects only documented columns and filters by crash timestamp.
    A City of Chicago app token is optional for the modest portfolio extract but
    can be supplied to accommodate higher API quotas in production.
    """
    if limit <= 0:
        raise ValueError("limit must be positive")
    params = {
        "$select": ",".join(DEFAULT_FIELDS),
        "$where": f"crash_date between '{start_date}' and '{end_date}'",
        "$order": "crash_date ASC",
        "$limit": str(limit),
    }
    headers = {"X-App-Token": app_token} if app_token else None
    response = requests.get(CRASHES_ENDPOINT, params=params, headers=headers, timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Expected a JSON list from the Socrata endpoint.")
    return pd.DataFrame(payload)


def fetch_or_load(
    cache_path: str | Path,
    refresh: bool = False,
    **query_kwargs: object,
) -> pd.DataFrame:
    """Cache a raw official extract locally without committing it to Git."""
    cache_path = Path(cache_path)
    if cache_path.exists() and not refresh:
        return pd.read_parquet(cache_path) if cache_path.suffix == ".parquet" else pd.read_csv(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame = query_crashes(**query_kwargs)
    if cache_path.suffix == ".parquet":
        frame.to_parquet(cache_path, index=False)
    else:
        frame.to_csv(cache_path, index=False, compression="infer")
    return frame


def _normalize_category(series: pd.Series, fallback: str = "UNKNOWN") -> pd.Series:
    return series.fillna(fallback).astype(str).str.strip().str.upper().replace({"": fallback, "NAN": fallback})


def prepare_analysis_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Construct an auditable crash-level analysis table.

    The binary outcome equals one if a crash had at least one fatal,
    incapacitating, non-incapacitating, or reported-not-evident injury.  This
    outcome deliberately uses crash-level totals rather than joining the people
    table, avoiding a one-to-many-record denominator error.
    """
    required = {"crash_record_id", "crash_date", "injuries_total"}
    missing = required.difference(raw.columns)
    if missing:
        raise KeyError(f"Raw data are missing required columns: {sorted(missing)}")

    frame = raw.copy()
    frame["crash_date"] = pd.to_datetime(frame["crash_date"], errors="coerce")
    frame = frame.dropna(subset=["crash_record_id", "crash_date"]).drop_duplicates("crash_record_id")
    numeric_columns = [
        "injuries_total",
        "injuries_fatal",
        "injuries_incapacitating",
        "injuries_non_incapacitating",
        "injuries_reported_not_evident",
        "posted_speed_limit",
        "crash_hour",
        "crash_day_of_week",
        "crash_month",
        "latitude",
        "longitude",
    ]
    for column in numeric_columns:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["injury_crash"] = (frame["injuries_total"].fillna(0) > 0).astype(int)
    frame["year"] = frame["crash_date"].dt.year
    frame["month_start"] = frame["crash_date"].dt.to_period("M").dt.to_timestamp()
    hour = frame["crash_hour"].fillna(frame["crash_date"].dt.hour)
    frame["daypart"] = pd.cut(
        hour,
        bins=[-1, 5, 11, 16, 20, 23],
        labels=["LATE_NIGHT", "AM_PEAK", "MIDDAY", "PM_PEAK", "EVENING"],
    ).astype(str).replace("nan", "UNKNOWN")
    lighting = _normalize_category(frame.get("lighting_condition", pd.Series(index=frame.index, dtype=object)))
    frame["lighting_group"] = pd.Series("DARK_OR_UNKNOWN", index=frame.index)
    frame.loc[lighting.str.contains("DAYLIGHT", regex=False), "lighting_group"] = "DAYLIGHT"
    frame.loc[lighting.str.contains("DARK", regex=False), "lighting_group"] = "DARKNESS"
    frame.loc[lighting.str.contains("DAWN|DUSK", regex=True), "lighting_group"] = "DAWN_DUSK"

    weather = _normalize_category(frame.get("weather_condition", pd.Series(index=frame.index, dtype=object)))
    frame["weather_group"] = "OTHER_OR_UNKNOWN"
    frame.loc[weather.str.contains("CLEAR", regex=False), "weather_group"] = "CLEAR"
    frame.loc[weather.str.contains("RAIN|SNOW|SLEET|FOG|BLOWING", regex=True), "weather_group"] = "ADVERSE"
    surface = _normalize_category(frame.get("roadway_surface_cond", pd.Series(index=frame.index, dtype=object)))
    frame["surface_group"] = "OTHER_OR_UNKNOWN"
    frame.loc[surface.str.contains("DRY", regex=False), "surface_group"] = "DRY"
    frame.loc[surface.str.contains("WET|SNOW|ICE|SAND|SLUSH", regex=True), "surface_group"] = "NON_DRY"

    trafficway = _normalize_category(frame.get("trafficway_type", pd.Series(index=frame.index, dtype=object)))
    frame["intersection_context"] = "NON_INTERSECTION_OR_UNKNOWN"
    frame.loc[trafficway.str.contains("INTERSECTION", regex=False), "intersection_context"] = "INTERSECTION"
    frame["speed_group"] = pd.cut(
        frame["posted_speed_limit"].clip(lower=0, upper=80),
        bins=[-1, 20, 30, 40, 80],
        labels=["<=20", "21_30", "31_40", ">40"],
    ).astype(str).replace("nan", "UNKNOWN")

    selected = [
        "crash_record_id", "crash_date", "year", "month_start", "injury_crash", "injuries_total",
        "lighting_group", "weather_group", "surface_group", "intersection_context", "speed_group", "daypart",
        "latitude", "longitude",
    ]
    return frame.loc[:, [column for column in selected if column in frame.columns]].reset_index(drop=True)

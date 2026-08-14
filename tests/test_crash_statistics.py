from __future__ import annotations

import pandas as pd

from crash_statistics.data_pipeline import prepare_analysis_frame
from crash_statistics.statistics import monthly_rates, stratified_bootstrap_rates, wilson_interval


def test_prepare_analysis_frame_creates_crash_level_outcome() -> None:
    raw = pd.DataFrame(
        {
            "crash_record_id": ["A", "B", "B"],
            "crash_date": ["2024-01-01 08:00:00", "2024-01-02 21:00:00", "2024-01-02 21:00:00"],
            "injuries_total": [0, 2, 2],
            "posted_speed_limit": [20, 35, 35],
            "lighting_condition": ["DAYLIGHT", "DARKNESS", "DARKNESS"],
            "weather_condition": ["CLEAR", "RAIN", "RAIN"],
            "roadway_surface_cond": ["DRY", "WET", "WET"],
            "trafficway_type": ["NOT DIVIDED", "FOUR WAY", "FOUR WAY"],
            "crash_hour": [8, 21, 21],
        }
    )
    prepared = prepare_analysis_frame(raw)
    assert len(prepared) == 2
    assert prepared.set_index("crash_record_id").loc["A", "injury_crash"] == 0
    assert prepared.set_index("crash_record_id").loc["B", "injury_crash"] == 1
    assert set(prepared["weather_group"]) == {"CLEAR", "ADVERSE"}


def test_stratified_bootstrap_returns_bounded_rates() -> None:
    frame = pd.DataFrame(
        {
            "lighting_group": ["DAYLIGHT"] * 5 + ["DARKNESS"] * 5,
            "injury_crash": [0, 0, 0, 1, 0, 1, 1, 0, 1, 1],
        }
    )
    result = stratified_bootstrap_rates(frame, "lighting_group", "injury_crash", n_bootstrap=200, seed=7)
    assert set(result["group"]) == {"DAYLIGHT", "DARKNESS"}
    assert (result["lower_ci"] <= result["point_estimate"]).all()
    assert (result["point_estimate"] <= result["upper_ci"]).all()
    assert ((result[["lower_ci", "upper_ci"]] >= 0) & (result[["lower_ci", "upper_ci"]] <= 1)).all().all()


def test_wilson_intervals_and_monthly_rates_are_valid() -> None:
    intervals = wilson_interval(pd.Series([5]), pd.Series([10]))
    assert 0 < intervals.loc[0, "lower_ci"] < 0.5 < intervals.loc[0, "upper_ci"] < 1
    frame = pd.DataFrame(
        {
            "crash_date": pd.to_datetime(["2024-01-01", "2024-01-15", "2024-02-01"]),
            "injury_crash": [0, 1, 1],
        }
    )
    monthly = monthly_rates(frame)
    assert monthly["crashes"].sum() == 3
    assert set(monthly["rate"].round(3)) == {0.5, 1.0}

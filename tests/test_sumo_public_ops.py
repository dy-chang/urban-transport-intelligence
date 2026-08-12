from pathlib import Path

import pandas as pd

from sumo_public_ops.metrics import compare_to_baseline, parse_tripinfo, run_kpis
from sumo_public_ops.public_counts import create_screening_demand


def test_create_screening_demand_labels_observed_and_assumed(tmp_path: Path) -> None:
    profile = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2011-01-20 08:00", "2011-01-20 08:15"]),
            "volume_15min": [100, 120],
        }
    )
    demand = create_screening_demand(profile, tmp_path / "demand.csv")
    assert len(demand) == 8
    assert demand.loc[demand["movement"] == "north_to_south", "input_class"].eq("observed_ATR").all()
    assert demand.loc[demand["movement"] != "north_to_south", "input_class"].eq("scenario_assumption").all()
    assert demand["begin_s"].min() == 0
    assert demand["end_s"].max() == 1800


def test_tripinfo_parser_and_kpis_use_sumo_emission_mass_units(tmp_path: Path) -> None:
    xml = """<tripinfos>
      <tripinfo id="v0" duration="50" timeLoss="20" waitingTime="10" departDelay="0" routeLength="1000">
        <emissions CO2_abs="2000" NOx_abs="3" fuel_abs="700"/>
      </tripinfo>
    </tripinfos>"""
    path = tmp_path / "tripinfo.xml"
    path.write_text(xml, encoding="utf-8")
    trips = parse_tripinfo(path, "baseline", 1)
    result = run_kpis(trips, pd.DataFrame())
    assert result.loc[0, "total_co2_g"] == 2.0
    assert result.loc[0, "total_fuel_g"] == 0.7
    assert result.loc[0, "mean_delay_s"] == 20.0


def test_paired_scenario_comparison_is_seed_aligned() -> None:
    kpis = pd.DataFrame(
        {
            "scenario": ["baseline", "baseline", "peak_retimed", "peak_retimed"],
            "seed": [1, 2, 1, 2],
            "mean_delay_s": [10.0, 12.0, 8.0, 9.0],
        }
    )
    comparison = compare_to_baseline(kpis)
    row = comparison.loc[comparison["metric"] == "mean_delay_s"].iloc[0]
    assert row["n_paired_seeds"] == 2
    assert row["mean_delta_vs_baseline"] == -2.5

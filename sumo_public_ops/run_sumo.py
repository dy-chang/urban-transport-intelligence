"""End-to-end public-data SUMO operations-screening runner.

Usage
-----
PYTHONPATH=. python3 -m sumo_public_ops.run_sumo --replications 5 --refresh-counts
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from .metrics import compare_to_baseline, parse_lanearea, parse_tripinfo, run_kpis, summarize_runs, write_run_manifest
from .network import build_representative_network, build_routes, write_signal_program
from .public_counts import CountQuery, bootstrap_profile_intervals, create_screening_demand, fetch_nyc_atr_profile


def require_sumo() -> str:
    executable = shutil.which("sumo")
    if not executable:
        raise RuntimeError("SUMO is not on PATH. Install Eclipse SUMO and ensure `sumo` is executable.")
    return executable


def execute_scenario(
    project_dir: Path,
    network_file: Path,
    routes_file: Path,
    scenario: str,
    seed: int,
    horizon_s: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run one seed and return trip- and detector-level result tables."""

    run_dir = project_dir / "outputs" / "runs" / scenario / f"seed_{seed:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    additional = write_signal_program(network_file, run_dir / "signals.add.xml", scenario)
    tripinfo = run_dir / "tripinfo.xml"
    summary = run_dir / "summary.xml"
    command = [
        require_sumo(),
        "--net-file", str(network_file.resolve()),
        "--route-files", str(routes_file.resolve()),
        "--additional-files", str(additional.resolve()),
        "--begin", "0",
        "--end", str(horizon_s),
        "--seed", str(seed),
        "--time-to-teleport", "-1",
        "--tripinfo-output", str(tripinfo.resolve()),
        "--tripinfo-output.write-unfinished", "true",
        "--summary-output", str(summary.resolve()),
        "--device.emissions.probability", "1",
        "--no-step-log", "true",
        "--duration-log.disable", "true",
    ]
    completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True)
    (run_dir / "command.txt").write_text(" ".join(command) + "\n", encoding="utf-8")
    (run_dir / "stdout.log").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"SUMO failed for {scenario}, seed={seed}: {completed.stderr[-1200:]}")

    lanearea = run_dir / "lanearea.xml"
    return parse_tripinfo(tripinfo, scenario, seed), parse_lanearea(lanearea, scenario, seed)


def run_study(
    project_dir: str | Path,
    replications: int = 5,
    refresh_counts: bool = False,
    query: CountQuery = CountQuery(),
) -> dict[str, pd.DataFrame]:
    """Execute baseline and retiming scenarios using one documented ATR profile."""

    project_dir = Path(project_dir)
    data_dir = project_dir / "data"
    profile, source_metadata = fetch_nyc_atr_profile(data_dir / "raw", query=query, refresh=refresh_counts)
    demand = create_screening_demand(profile, data_dir / "processed_demand.csv")
    uncertainty = bootstrap_profile_intervals(profile)
    uncertainty.to_csv(project_dir / "outputs" / "atr_profile_bootstrap_interval.csv", index=False)

    network_file = build_representative_network(project_dir / "network")
    routes_file = build_routes(data_dir / "processed_demand.csv", project_dir / "scenarios" / "screening_demand.rou.xml")
    horizon_s = int(demand["end_s"].max() + 900)
    all_trips, all_queues = [], []
    for scenario in ("baseline", "peak_retimed"):
        for seed in range(1, replications + 1):
            trips, queues = execute_scenario(project_dir, network_file, routes_file, scenario, seed, horizon_s)
            all_trips.append(trips)
            all_queues.append(queues)

    trip_df = pd.concat(all_trips, ignore_index=True)
    queue_df = pd.concat(all_queues, ignore_index=True)
    kpis = run_kpis(trip_df, queue_df)
    summary = summarize_runs(kpis)
    deltas = compare_to_baseline(kpis)
    output = project_dir / "outputs"
    output.mkdir(exist_ok=True)
    profile.to_csv(output / "public_atr_profile.csv", index=False)
    demand.to_csv(output / "sumo_demand_input_audit.csv", index=False)
    trip_df.to_csv(output / "trip_level_results.csv", index=False)
    queue_df.to_csv(output / "queue_detector_results.csv", index=False)
    kpis.to_csv(output / "seed_level_kpis.csv", index=False)
    summary.to_csv(output / "kpi_uncertainty_summary.csv", index=False)
    deltas.to_csv(output / "scenario_deltas_vs_baseline.csv", index=False)

    write_run_manifest(
        output / "run_manifest.json",
        {
            "created_at_utc": datetime.now(UTC).isoformat(),
            "analysis_level": "screening microsimulation; not a field-calibrated design model",
            "source_metadata": source_metadata,
            "network": {
                "type": "representative two-lane four-leg network generated with netconvert",
                "network_file": str(network_file.relative_to(project_dir)),
                "real_network_path": "Use network.osm_to_sumo_command() after OSM topology and TLS QA.",
            },
            "demand": {
                "observed_movement": "north_to_south",
                "unobserved_movements": "Scaled scenario assumptions documented in sumo_demand_input_audit.csv",
                "turning_movements": "Straight-through only in benchmark; replace with TMC or route-sampling calibration for a study model.",
            },
            "scenarios": {
                "baseline": "32s NS / 26s EW green plus clearance within a 70s cycle",
                "peak_retimed": "42s NS / 16s EW green plus clearance within a 70s cycle",
            },
            "replications": replications,
            "seeds": list(range(1, replications + 1)),
            "horizon_s": horizon_s,
            "outputs": [
                "public_atr_profile.csv", "sumo_demand_input_audit.csv", "seed_level_kpis.csv",
                "kpi_uncertainty_summary.csv", "scenario_deltas_vs_baseline.csv",
            ],
        },
    )
    return {"profile": profile, "demand": demand, "trips": trip_df, "queues": queue_df, "kpis": kpis, "summary": summary, "deltas": deltas}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the public-data SUMO operations-screening portfolio example.")
    parser.add_argument("--replications", type=int, default=5, help="Number of seeds per scenario (minimum: 2).")
    parser.add_argument("--refresh-counts", action="store_true", help="Refresh the official NYC Open Data response.")
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    if args.replications < 2:
        parser.error("Use at least two replications to calculate a simulation uncertainty interval.")
    result = run_study(args.project_dir, replications=args.replications, refresh_counts=args.refresh_counts)
    print(result["deltas"].to_string(index=False))


if __name__ == "__main__":
    main()

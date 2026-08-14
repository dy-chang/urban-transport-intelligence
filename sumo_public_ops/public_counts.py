"""Official public-count acquisition and transparent demand-screen construction.

The functions in this module intentionally preserve the distinction between an
observed directional ATR count and unobserved cross-street or turning demand.
The latter are scenario assumptions written into the run manifest, not facts
inferred from the NYC DOT dataset.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

NYC_ATR_ENDPOINT = "https://data.cityofnewyork.us/resource/7ym2-wayt.json"


@dataclass(frozen=True)
class CountQuery:
    """A reproducible NYC DOT ATR query for the portfolio reference example."""

    request_id: str = "1985"
    year: int = 2011
    month: int = 1
    day: int = 20
    hour: int = 8

    def socrata_params(self) -> dict[str, str]:
        fields = "requestid,boro,yr,m,d,hh,mm,vol,segmentid,wktgeom,street,fromst,tost,direction"
        where = (
            f"requestid='{self.request_id}' AND yr={self.year} AND m={self.month} "
            f"AND d={self.day} AND hh={self.hour}"
        )
        return {"$select": fields, "$where": where, "$order": "mm ASC", "$limit": "100"}


def fetch_nyc_atr_profile(
    cache_dir: str | Path,
    query: CountQuery = CountQuery(),
    timeout: int = 30,
    refresh: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fetch a 15-minute official ATR profile and retain request provenance.

    The default query selects a morning observation from the official NYC DOT
    dataset. Users should replace it with a study-specific request ID and date
    after checking the data-collection calendar and field documentation.
    """

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    stem = f"nyc_atr_{query.request_id}_{query.year:04d}{query.month:02d}{query.day:02d}_{query.hour:02d}"
    csv_path, metadata_path = cache_dir / f"{stem}.csv", cache_dir / f"{stem}.metadata.json"

    if csv_path.exists() and metadata_path.exists() and not refresh:
        return pd.read_csv(csv_path), json.loads(metadata_path.read_text(encoding="utf-8"))

    response = requests.get(NYC_ATR_ENDPOINT, params=query.socrata_params(), timeout=timeout)
    response.raise_for_status()
    rows = response.json()
    if not rows:
        raise ValueError(f"No official ATR rows matched {query!r}. Choose a valid study window.")

    profile = pd.DataFrame(rows)
    numeric = ["yr", "m", "d", "hh", "mm", "vol", "segmentid"]
    for column in numeric:
        if column in profile:
            profile[column] = pd.to_numeric(profile[column], errors="coerce")
    profile = profile.dropna(subset=["vol", "mm"]).copy()
    profile["timestamp"] = pd.to_datetime(
        dict(year=profile["yr"], month=profile["m"], day=profile["d"], hour=profile["hh"], minute=profile["mm"])
    )
    profile = profile.sort_values("timestamp").reset_index(drop=True)
    profile["volume_15min"] = profile["vol"].astype(int)

    if (profile["volume_15min"] < 0).any() or profile["mm"].duplicated().any():
        raise ValueError("ATR input violates basic non-negative or unique-quarter validation.")

    metadata = {
        "source_name": "NYC DOT Automated Traffic Volume Counts",
        "source_url": "https://data.cityofnewyork.us/Transportation/Automated-Traffic-Volume-Counts/7ym2-wayt",
        "api_endpoint": NYC_ATR_ENDPOINT,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "query": asdict(query),
        "socrata_params": query.socrata_params(),
        "row_count": int(len(profile)),
        "quality_note": "ATR counts are sampled observations; this is not a continuous or full-year profile.",
    }
    profile.to_csv(csv_path, index=False)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return profile, metadata


def create_screening_demand(
    profile: pd.DataFrame,
    output_csv: str | Path,
    secondary_direction_factor: float = 0.55,
    cross_street_factor: float = 0.50,
) -> pd.DataFrame:
    """Translate observed counts into explicit scenario input flows.

    `north_to_south` is the observed mainline movement in the reference
    dataset. The other movements are *not observed*: they are documented
    scaling assumptions used only to make a runnable screening scenario.
    """

    if not 0 < secondary_direction_factor <= 1 or not 0 < cross_street_factor <= 1:
        raise ValueError("Demand multipliers must lie in (0, 1].")
    required = {"timestamp", "volume_15min"}
    missing = required - set(profile.columns)
    if missing:
        raise KeyError(f"Profile missing required columns: {sorted(missing)}")

    rows: list[dict[str, Any]] = []
    for row in profile.itertuples(index=False):
        observed = int(row.volume_15min)
        base = {"begin_s": int(row.timestamp.minute * 60), "end_s": int((row.timestamp.minute + 15) * 60)}
        values = {
            "north_to_south": observed,
            "south_to_north": round(observed * secondary_direction_factor),
            "east_to_west": round(observed * cross_street_factor),
            "west_to_east": round(observed * cross_street_factor * 0.9),
        }
        for movement, vehicles in values.items():
            rows.append(
                {
                    **base,
                    "movement": movement,
                    "vehicles_15min": int(vehicles),
                    "input_class": "observed_ATR" if movement == "north_to_south" else "scenario_assumption",
                    "assumption": (
                        "NYC DOT ATR observed directional count"
                        if movement == "north_to_south"
                        else "Scaled from observed mainline count; replace with field TMC/ATR count before decision use"
                    ),
                }
            )
    demand = pd.DataFrame(rows)
    # SUMO intervals start at zero; the first selected quarter-hour begins at zero.
    first_begin = int(demand["begin_s"].min())
    demand["begin_s"] -= first_begin
    demand["end_s"] -= first_begin
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    demand.to_csv(output_csv, index=False)
    return demand


def bootstrap_profile_intervals(profile: pd.DataFrame, n_resamples: int = 500, seed: int = 2026) -> pd.DataFrame:
    """Estimate a transparent uncertainty band for the sampled ATR profile."""

    volumes = profile["volume_15min"].to_numpy(dtype=float)
    if len(volumes) < 2:
        return pd.DataFrame({"stat": ["mean"], "lower": [volumes.mean()], "upper": [volumes.mean()]})
    rng = np.random.default_rng(seed)
    samples = rng.choice(volumes, size=(n_resamples, len(volumes)), replace=True).mean(axis=1)
    return pd.DataFrame(
        {"stat": ["mean_15min_volume"], "lower": [np.quantile(samples, 0.025)], "upper": [np.quantile(samples, 0.975)]}
    )

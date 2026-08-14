"""LEHD LODES origin–destination data utilities.

LODES provides workplace-area and residence-area employment flows at Census
block resolution. The routines here aggregate the public files to tract-level
trip ends and OD flows for a transparent regional sketch-planning input.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd
import requests


@dataclass
class LODESClient:
    """Download a public LODES main-OD file from the Census LEHD distribution."""

    state_abbreviation: str
    year: int = 2022
    cache_dir: Path = Path("data")
    job_type: Literal["JT00", "JT01", "JT02", "JT03", "JT04", "JT05"] = "JT00"
    timeout_seconds: int = 180

    def get_main_od(self) -> pd.DataFrame:
        """Return state main-job OD flows and cache the original gzip file."""
        state = self.state_abbreviation.lower()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.cache_dir / f"{state}_od_main_{self.job_type}_{self.year}.csv.gz"
        if not cache_path.exists():
            url = (
                "https://lehd.ces.census.gov/data/lodes/LODES8/"
                f"{state}/od/{state}_od_main_{self.job_type}_{self.year}.csv.gz"
            )
            response = requests.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
            cache_path.write_bytes(response.content)
        return pd.read_csv(cache_path, compression="gzip", dtype={"h_geocode": str, "w_geocode": str})


def aggregate_od_to_tract(od_flows: pd.DataFrame) -> pd.DataFrame:
    """Aggregate block-level LODES OD flows to Census tract flows.

    The LODES ``S000`` column represents all jobs. GEOIDs are maintained as
    zero-padded strings to avoid losing spatial identifiers in spreadsheet-like
    workflows.
    """
    required = {"h_geocode", "w_geocode", "S000"}
    missing = required.difference(od_flows.columns)
    if missing:
        raise KeyError(f"LODES flow table lacks required fields: {sorted(missing)}")
    flows = od_flows.loc[:, ["h_geocode", "w_geocode", "S000"]].copy()
    flows["origin_geoid"] = flows["h_geocode"].astype(str).str.zfill(15).str[:11]
    flows["destination_geoid"] = flows["w_geocode"].astype(str).str.zfill(15).str[:11]
    flows["flow"] = pd.to_numeric(flows["S000"], errors="coerce").fillna(0.0)
    return flows.groupby(["origin_geoid", "destination_geoid"], as_index=False)["flow"].sum()

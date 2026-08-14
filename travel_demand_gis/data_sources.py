"""Official public-data clients used by the planning screen.

The clients deliberately keep data provenance explicit: every download is from
a U.S. Census Bureau endpoint and can be cached locally for reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
import os

import geopandas as gpd
import numpy as np
import pandas as pd
import requests


ACS_TRACT_FIELDS: Dict[str, str] = {
    "NAME": "name",
    "B01003_001E": "population",
    "B08301_001E": "workers",
    "B08301_003E": "drive_alone_workers",
    "B08301_010E": "transit_workers",
    "B08301_018E": "walk_workers",
    "B08301_020E": "work_from_home_workers",
    "B08303_002E": "commute_lt5",
    "B08303_003E": "commute_5_9",
    "B08303_004E": "commute_10_14",
    "B08303_005E": "commute_15_19",
    "B08303_006E": "commute_20_24",
    "B08303_007E": "commute_25_29",
    "B08303_008E": "commute_30_34",
    "B08303_009E": "commute_35_39",
    "B08303_010E": "commute_40_44",
    "B08303_011E": "commute_45_59",
    "B08303_012E": "commute_60_89",
    "B08303_013E": "commute_90_plus",
    "B19013_001E": "median_household_income",
    "B17001_002E": "population_below_poverty",
    "B08201_001E": "households",
    "B08201_002E": "households_no_vehicle",
    "B03002_003E": "non_hispanic_white_population",
}


@dataclass
class ACSClient:
    """Download and cache ACS 5-year tract estimates from the Census API."""

    year: int = 2023
    cache_dir: Path = Path("data")
    timeout_seconds: int = 60
    api_key: Optional[str] = None

    def get_tract_features(self, state_fips: str, county_fips: str = "*") -> pd.DataFrame:
        """Return tract-level travel-demand and equity inputs for a geography.

        Parameters use Census FIPS codes. Passing ``county_fips='*'`` retrieves
        all tracts in the state; an MPO workflow will normally specify each
        county in the modeled region.
        """
        state_fips = state_fips.zfill(2)
        county_fips = "*" if county_fips == "*" else county_fips.zfill(3)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.cache_dir / f"acs_{self.year}_tract_{state_fips}_{county_fips}.csv"
        if cache_path.exists():
            return pd.read_csv(cache_path, dtype={"state": str, "county": str, "tract": str, "geoid": str})

        variables = ",".join(ACS_TRACT_FIELDS)
        url = f"https://api.census.gov/data/{self.year}/acs/acs5"
        api_key = self.api_key or os.getenv("CENSUS_API_KEY")
        params = {"get": variables, "for": "tract:*", "in": f"state:{state_fips} county:{county_fips}"}
        if api_key:
            params["key"] = api_key
        response = requests.get(url, params=params, timeout=self.timeout_seconds, allow_redirects=False)
        if response.status_code in {301, 302, 307, 308} and "missing_key" in response.headers.get("Location", ""):
            raise RuntimeError(
                "The Census API requires a key for this request. Obtain a free key from "
                "https://api.census.gov/data/key_signup.html and set CENSUS_API_KEY."
            )
        response.raise_for_status()
        payload = response.json()
        if len(payload) < 2:
            raise ValueError("Census API returned no tract records for the requested geography.")

        frame = pd.DataFrame(payload[1:], columns=payload[0]).rename(columns=ACS_TRACT_FIELDS)
        numeric_columns = list(ACS_TRACT_FIELDS.values())
        numeric_columns.remove("name")
        for column in numeric_columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").mask(lambda series: series < 0)
        frame["geoid"] = frame["state"].astype(str).str.zfill(2) + frame["county"].astype(str).str.zfill(3) + frame["tract"].astype(str).str.zfill(6)
        commute_bins = [
            "commute_lt5", "commute_5_9", "commute_10_14", "commute_15_19",
            "commute_20_24", "commute_25_29", "commute_30_34", "commute_35_39",
            "commute_40_44", "commute_45_59", "commute_60_89", "commute_90_plus",
        ]
        midpoint_minutes = [2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 52.5, 75.0, 100.0]
        bin_counts = frame[commute_bins].fillna(0.0).to_numpy(dtype=float)
        bin_total = bin_counts.sum(axis=1)
        frame["mean_commute_minutes"] = np.divide(
            bin_counts @ np.asarray(midpoint_minutes), bin_total,
            out=np.zeros(len(frame), dtype=float), where=bin_total > 0,
        )
        frame.to_csv(cache_path, index=False)
        return frame


@dataclass
class CensusGeometryClient:
    """Download a generalized Census tract boundary file for map products."""

    year: int = 2023
    cache_dir: Path = Path("data")
    timeout_seconds: int = 120

    def get_state_tracts(self, state_fips: str) -> gpd.GeoDataFrame:
        """Return Census tract geometries for a state, cached as a GeoPackage."""
        state_fips = state_fips.zfill(2)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.cache_dir / f"cb_{self.year}_{state_fips}_tract_500k.gpkg"
        if cache_path.exists():
            return gpd.read_file(cache_path)

        zip_url = (
            f"https://www2.census.gov/geo/tiger/GENZ{self.year}/shp/"
            f"cb_{self.year}_{state_fips}_tract_500k.zip"
        )
        zip_path = self.cache_dir / f"cb_{self.year}_{state_fips}_tract_500k.zip"
        response = requests.get(zip_url, timeout=self.timeout_seconds)
        response.raise_for_status()
        zip_path.write_bytes(response.content)
        tracts = gpd.read_file(f"zip://{zip_path}")
        tracts = tracts.rename(columns={"GEOID": "geoid"})
        tracts.to_file(cache_path, driver="GPKG")
        return tracts

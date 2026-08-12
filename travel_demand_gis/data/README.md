# Data Cache Policy

This directory is intentionally empty in version control except for this note. The pipeline downloads official ACS, Census geometry, and LODES inputs at runtime and caches them here so runs are reproducible without committing large source datasets.

Use the following source hierarchy and retain the downloaded vintage with each analytical run:

| Source | Retrieval route | Cache artifact |
|---|---|---|
| ACS 5-year | Census Data API with `CENSUS_API_KEY` | `acs_<year>_tract_<state>_<county>.csv` |
| Census tract boundaries | Census generalized boundary download | `cb_<year>_<state>_tract_500k.gpkg` |
| LODES OD flows | Census LEHD LODES 8 public distribution | `<state>_od_main_JT00_<year>.csv.gz` |

Raw data are not redistributed here. Before publishing a planning product, review each agency’s data license, vintage, geographic coverage, and confidentiality guidance.

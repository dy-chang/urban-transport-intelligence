# Open-Data Travel Demand, Accessibility & Equity Planning Screen

> **Portfolio module for DOT / MPO planning teams**  
> **Focus**: transparent sketch planning, travel-demand model foundations, GIS accessibility, housing–transportation integration, and equity screening.

This module demonstrates a reproducible workflow for converting official public data into an auditable planning screen. It is designed to complement—not replace—a regionally calibrated activity-based or four-step travel model. The implementation explicitly separates **data acquisition**, **trip-end development**, **gravity distribution**, **accessibility analysis**, **equity screening**, and **scenario sensitivity**.

The policy alignment is direct. FHWA states that the IIJA calls for comparison of travel-demand forecasts with observed data, data support for improving plans and forecasts, and multimodal evaluation tools for States and MPOs.[1] The same program emphasizes safe and accessible multimodal options and housing coordination.[1] FHWA also identifies open GIS data, EPA Smart Location measures, Census transportation data, LODES, and critical-infrastructure datasets as useful inputs to accessibility analysis.[2]

## Why This Is Relevant to a DOT or MPO

| Current planning need | Portfolio response | Decision use |
|---|---|---|
| **Forecast transparency and validation** | A doubly constrained gravity model with an inspectable impedance function and a documented beta calibration table. | Validates sketch-model assumptions before higher-cost network modeling. |
| **Housing–transportation coordination** | Combines tract workers, jobs, commute mode, commute-time distribution, income, poverty, and vehicle availability. | Screens areas where growth, housing, or access investments deserve further study. |
| **Multimodal accessibility** | Calculates cumulative and gravity-based access to employment, designed to accept network/GTFS skim matrices. | Establishes project performance measures beyond vehicle LOS. |
| **Equity and Title VI/EJ screening** | Reports access differences for a transparent equity-priority indicator, which is intentionally configurable to agency policy. | Identifies geographic areas requiring deeper engagement or benefits/burdens review. |
| **Open-data governance** | Caches source files, retains FIPS GEOIDs, writes GeoPackage/CSV/JSON outputs, and documents source provenance. | Supports peer review, public transparency, and iterative data maintenance. |

## Architecture

```text
ACS 5-year + TIGER/Line ─┐
                         ├─► zonal socioeconomic / demographic inputs ─► equity screen
LEHD LODES OD flows ─────┤                                              │
                         ├─► productions & attractions ─► gravity model ├─► accessibility measures
Network / GTFS skims ────┘      (default: centroid sketch impedance)    │
                                                                        └─► scenario comparison + GIS outputs
```

The default demonstration uses a county-scale geography. For a full MPO region, run each county, concatenate standardized tract inputs, and substitute adopted regional zone systems, land-use forecasts, and network skims.

## Public Data Contract

| Dataset | Unit of analysis | Variables used | Code entry point | Important caveat |
|---|---|---|---|---|
| **ACS 5-year** | Census tract | Workers, commute mode, time bins, income, poverty, vehicle availability, race/ethnicity. | `ACSClient` | Survey estimates should be accompanied by margins of error for formal findings. |
| **Census tract geometry** | Census tract | GEOID and polygon geometry. | `CensusGeometryClient` | Generalized boundaries are suitable for regional visualization, not parcel-scale work. |
| **LEHD LODES** | Block OD aggregated to tract | Residence-area, workplace-area and all-jobs OD flows. | `LODESClient`, `aggregate_od_to_tract` | State-only LODES files may omit cross-border commuter flows; expand the extract for multi-state MPOs. |
| **EPA Smart Location** | Block group | Built environment, transit service and destination access context. | Documented integration point | Join by crosswalk after confirming release-year compatibility. |
| **Network / GTFS skim** | Analysis zone OD pair | Time, cost, reliability, transfers, walk access. | `GravityModel.fit_predict` | Replace the centroid approximation before project decisions. |

The Census Bureau’s commuting resources describe available journey-to-work statistics, including mode, departure time, and travel time.[3] LODES provides detailed worker/job spatial distributions and home-to-work relationships.[4] EPA’s Smart Location products provide consistent neighborhood-scale measures of built environment and transit accessibility.[5]

## Methodology

### 1. Trip-end development and distribution

The pipeline derives productions and attractions from LODES OD flows, then balances them in a closed study-area model. It applies a negative-exponential impedance function:

\[
F_{ij}=\exp(-\beta c_{ij})
\]

A Furness / iterative-proportional-fitting procedure constrains the OD matrix to exact origin and destination marginals. `calibrate_beta()` searches a candidate set of beta values and selects the value that most closely matches the workers-weighted ACS mean commute time. The workflow writes `gravity_calibration.csv` so the choice remains reviewable.

### 2. Accessibility and equity measures

The module produces both **cumulative opportunities** within 30 minutes and a **gravity opportunity** measure with distance decay. It then compares population-weighted access for tracts above and below an explicit equity-screen threshold. This is a screening measure only; each agency must substitute its adopted Title VI, EJ, disability, age, limited-English-proficiency, rural, and other relevant criteria.

### 3. Scenario sensitivity

The included scenario applies a documented 20% generalized-cost reduction to OD pairs that have baseline sketched impedances between 12 and 30 minutes. It is deliberately labelled a **sensitivity case**, not a forecast of any real project. A production application should load model skims from a network assignment, transit model, or GTFS routing workflow.

## Installation and Run Instructions

```bash
# From the repository root
python -m pip install -r requirements.txt

# Census currently requires a free API key for programmatic ACS requests.
export CENSUS_API_KEY="your_key_from_api.census.gov"

# Washington, DC demonstration using Census + LODES public data
PYTHONPATH=. python -m travel_demand_gis.run_screen \
  --state 11 --county 001 --state-abbr dc \
  --acs-year 2023 --lodes-year 2022

# Generate maps and chart from saved results
PYTHONPATH=. python -m travel_demand_gis.visualize

# Run unit tests
PYTHONPATH=. pytest -q tests/test_travel_demand_gis.py
```

| Output | Format | Contents |
|---|---|---|
| `outputs/planning_screen.gpkg` | GeoPackage | Tract geometry, inputs, accessibility, equity, and scenario metrics. |
| `outputs/tract_metrics.csv` | CSV | Non-spatial tabular export for QA and dashboards. |
| `outputs/gravity_calibration.csv` | CSV | Candidate beta values, modeled mean impedance, and calibration error. |
| `outputs/screen_summary.json` | JSON | Data vintage, assumptions, demand totals, and equity summaries. |
| `outputs/*.png` | PNG | Accessibility/equity map, scenario-change map, and access distribution. |

## Professional Skillset Demonstrated

| Skill family | Concrete evidence in this module | Planning-team value |
|---|---|---|
| **Travel demand modeling** | Production/attraction balancing, exponential impedance, Furness/IPF, beta calibration, OD-matrix QA. | Transparent model foundations and scenario-ready demand logic. |
| **Spatial analysis & GIS** | FIPS-preserving joins, GeoPackage outputs, projection-aware centroids, choropleth and boundary overlays. | Reusable layers for LRTP, TIP, corridor, and equity analysis. |
| **Multimodal accessibility** | Cumulative and gravity opportunity metrics with a documented path to network/GTFS skims. | Performance measures aligned with access, not only traffic flow. |
| **Equity & planning policy** | Configurable equity screen, population-weighted group comparisons, housing/vehicle-income context. | Auditable early screening and more focused engagement. |
| **Public-data engineering** | Official API/download clients, local caching, stable GEOIDs, explicit data vintages, source register. | Repeatability and stronger data governance across planning cycles. |
| **Scientific computing & software engineering** | Typed modular Python, input validation, deterministic calculations, unit tests, CSV/JSON/GPKG exports. | Reviewable and maintainable analytical code. |
| **Visual communication** | 300-DPI maps and equity-access distributions, designed to be inserted into staff reports or public materials. | Accessible communication of complex model outputs. |

## Limitations and Responsible Use

> **This is a transparent portfolio-grade sketch-planning module, not an adopted regional model or a project-level environmental analysis.**

The code does not estimate discretionary travel, induced demand, tour chaining, freight, non-home-based travel, or dynamic network assignment. The default impedance is centroid-based and must be replaced with auto/transit/bike/walk skims before decision-making. LODES is a workplace/residence employment product, not a complete all-purpose trip table; it should be combined with local survey data, counts, household travel surveys, and validated model inputs for formal applications.

## References

[1] [FHWA, *Metropolitan Planning Program (MPP)*](https://highways.dot.gov/iija/fact-sheets/metropolitan-planning-program-mpp)

[2] [FHWA HEPGIS, *Accessibility Data and Resources*](https://hepgis-usdot.hub.arcgis.com/pages/c3121bfc82224774a909576385726c11)

[3] [U.S. Census Bureau, *Commuting (Journey to Work)*](https://www.census.gov/topics/employment/commuting.html)

[4] [U.S. Census Bureau, *LEHD Origin-Destination Employment Statistics (LODES)*](https://lehd.ces.census.gov/data/)

[5] [U.S. EPA, *Smart Location Mapping*](https://www.epa.gov/smartgrowth/smart-location-mapping)

[6] [FHWA, *GIS Open Data: Case Studies of Select Transportation Agencies*](https://www.gis.fhwa.dot.gov/case_studies/GIS_Open_Data_Case_Studies.aspx)

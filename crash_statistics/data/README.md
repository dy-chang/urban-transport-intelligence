# Raw Data Cache Policy

The analysis retrieves the City of Chicago `Traffic Crashes – Crashes` data through the official Socrata API at runtime. The cache is intentionally excluded from version control because it is a refreshable public-data extract rather than a project-authored deliverable.

| Item | Policy |
|---|---|
| Source | City of Chicago Data Portal, dataset `85ca-t3if` |
| Default window | 2018-01-01 through 2024-12-31, configured in `data_pipeline.py` |
| Cache location | `chicago_crashes_2018_2024.csv.gz` |
| Refresh | Run `python -m crash_statistics.run_analysis --refresh` |
| Provenance | Inspect the derived `outputs/run_manifest.json` after each run |

Do not commit raw records. Before a public-facing release, verify the current source terms, source vintage, coverage, and field definitions.

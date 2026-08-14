# Data and Input-Governance Notes

The module retrieves its reference traffic-volume profile from the official NYC DOT Automated Traffic Volume Counts API. The exact request, endpoint, retrieval time, and source URL are written to the `raw/*.metadata.json` companion file and copied into `outputs/run_manifest.json`.

Raw API responses are **not versioned** in this repository. They are reproducible public records but can be refreshed, corrected, or superseded by the publisher. The repository versions only the small, derived input and result tables needed for reviewer inspection.

| Artifact | Location | Version-control policy |
|---|---|---|
| Raw Socrata response and metadata | `data/raw/` | Ignored; regenerate with `--refresh-counts`. |
| Transformed flow ledger | `data/processed_demand.csv` and `outputs/sumo_demand_input_audit.csv` | Versioned as a transparent scenario input. |
| SUMO route file | `scenarios/screening_demand.rou.xml` | Versioned; generated from the flow ledger. |
| Study-ready field inputs | External controlled study-data store | Do not replace public benchmark values without updating source, date, QA, and assumptions in the manifest. |

The chosen ATR profile supplies only one directional count. Unobserved approaches and turning distributions in this benchmark are labeled **scenario assumptions**. They must be replaced with quality-checked observed counts, turning-movement counts, classifications, and field timing records before operational or design decisions are made.

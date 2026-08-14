#!/usr/bin/env python3
"""Print reproducible schemas and small samples for the Key Bridge detector–CHART analysis."""
from pathlib import Path
import json
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path('/home/ubuntu/transport_portfolio')
OUT = ROOT / 'network_shock_observatory' / 'outputs'
AUDIT = ROOT / '.drive_data_audit'


def parquet_profile(path: Path) -> dict:
    pf = pq.ParquetFile(path)
    table = pf.read_row_group(0)
    frame = table.to_pandas().head(5)
    return {
        'path': str(path),
        'schema': str(pf.schema_arrow),
        'rows': pf.metadata.num_rows,
        'sample': frame.to_dict(orient='records'),
    }


def csv_profile(path: Path) -> dict:
    frame = pd.read_csv(path, nrows=5)
    return {
        'path': str(path),
        'columns': list(frame.columns),
        'sample': frame.to_dict(orient='records'),
    }


profiles = {
    'detector_panel_2024': parquet_profile(OUT / 'event_panel_2024.parquet'),
    'detector_panel_2023': parquet_profile(OUT / 'event_panel_2023_seasonal.parquet'),
    'chart_2024': csv_profile(AUDIT / 'MDOT_CHART_2024.csv'),
    'chart_2023': csv_profile(AUDIT / 'MDOT_CHART_2023.csv'),
}

path = OUT / 'detector_chart_input_schema_audit.json'
path.write_text(json.dumps(profiles, indent=2, default=str) + '\n')
print(json.dumps(profiles, indent=2, default=str))
print(f'Wrote {path}')

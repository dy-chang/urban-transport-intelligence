#!/usr/bin/env python3
"""Diagnose each donor-pool eligibility criterion from the saved zone classification."""
from pathlib import Path
import json
import pandas as pd
import sys

PROJECT = Path('/home/ubuntu/transport_portfolio/network_shock_observatory')
OUT = PROJECT / 'outputs'
sys.path.insert(0, str(PROJECT / 'src'))
from build_detector_chart_panel import classify_detector_zones

meta = pd.read_csv(OUT / 'detector_chart_zone_classification_2024.csv')
panel = pd.read_parquet(OUT / 'event_panel_2024.parquet')
panel['time_bin'] = pd.to_datetime(panel['time_bin'])
panel = panel.loc[panel['day_of_week'] < 5].copy()
recomputed = classify_detector_zones(panel)

not_excluded = ~meta['road'].isin({'I-95', 'I-895', 'I-695'})
interstate = meta['road'].fillna('').str.startswith('I-')
distance = meta['distance_to_bridge_km'].between(30.0, 100.0)
coverage = meta['pre_speed_coverage'].ge(0.90)
volume = meta['pre_median_volume'].ge(20.0)
not_main = ~meta['analysis_group'].isin({'treatment', 'control'})
# The last condition must use the original geographic masks; saved main groups are equivalent
# only before donor labels are applied, so this diagnostic reports both.
eligible = not_excluded & interstate & distance & coverage & volume & not_main

component_columns = [c for c in meta.columns if c.startswith('donor_')]
component_counts = {c: int(meta[c].fillna(False).astype(bool).sum()) for c in component_columns}

result = {
    'n_zones': int(len(meta)),
    'saved_group_counts': meta['analysis_group'].value_counts().to_dict(),
    'recomputed_group_counts': recomputed['analysis_group'].value_counts().to_dict(),
    'saved_donor_component_true_counts': component_counts,
    'conditions': {
        'not_i95_i895_i695': int(not_excluded.sum()),
        'interstate': int(interstate.sum()),
        'distance_30_to_100_km': int(distance.sum()),
        'pre_speed_coverage_ge_0_90': int(coverage.sum()),
        'pre_median_volume_ge_20': int(volume.sum()),
        'not_saved_treatment_or_control': int(not_main.sum()),
        'all_conditions_using_saved_groups': int(eligible.sum()),
    },
    'eligible_rows': meta.loc[eligible, ['zone_id', 'road', 'direction', 'latitude', 'longitude', 'distance_to_bridge_km', 'pre_speed_coverage', 'pre_median_volume', 'analysis_group']].to_dict(orient='records'),
    'recomputed_candidate_rows': recomputed.loc[recomputed['analysis_group'].eq('donor_candidate'), ['zone_id', 'road', 'direction', 'latitude', 'longitude', 'distance_to_bridge_km', 'pre_speed_coverage', 'pre_median_volume']].to_dict(orient='records'),
}
(OUT / 'donor_rule_audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))

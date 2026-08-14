#!/usr/bin/env python3
"""Audit support retained by the CHART severe-context sensitivity restriction."""
from pathlib import Path
import json
import pandas as pd

OUT = Path('/home/ubuntu/transport_portfolio/network_shock_observatory/outputs')
EVENT = pd.Timestamp('2024-03-26')
POST_START = pd.Timestamp('2024-03-27')
POST_END = pd.Timestamp('2024-04-23 21:45:00')

corridor = pd.read_csv(OUT / 'detector_chart_corridor_15min_2024.csv', parse_dates=['time_bin'])
t = corridor.loc[
    corridor['analysis_group'].eq('treatment')
    & corridor['time_bin'].between(pd.Timestamp('2024-02-12 05:00:00'), POST_END)
    & ~corridor['time_bin'].dt.normalize().eq(EVENT)
].copy()
t['period'] = 'pre'
t.loc[t['time_bin'] >= POST_START, 'period'] = 'post'
support = t.groupby('period', observed=True).agg(
    all_bins=('time_bin', 'size'),
    nonsevere_bins=('any_severe_context_event', lambda s: int((~s).sum())),
    severe_bins=('any_severe_context_event', 'sum'),
    share_severe=('any_severe_context_event', 'mean'),
    mean_active_roadwork=('active_roadwork_count', 'mean'),
    mean_lane_closure_events=('active_lane_closure_event_count', 'mean'),
).reset_index()

events = pd.read_csv(OUT / 'chart_route_matched_events_2024.csv', parse_dates=['start_local', 'closed_local'])
events['duration_hours'] = (events['closed_local'] - events['start_local']).dt.total_seconds() / 3600
long = events.loc[
    events['route_context'].eq('treatment_route_context') & events['severe_context_event'].eq(True),
    ['event_id', 'Standardized Type', 'Agency-specific Type', 'Location', 'start_local', 'closed_local', 'duration_hours', 'Max Lanes Closed']
].sort_values('duration_hours', ascending=False).head(30)
result = {
    'support': support.to_dict(orient='records'),
    'longest_treatment_severe_events': long.to_dict(orient='records'),
}
(OUT / 'chart_severe_support_audit.json').write_text(json.dumps(result, indent=2, default=str) + '\n')
print(json.dumps(result, indent=2, default=str))

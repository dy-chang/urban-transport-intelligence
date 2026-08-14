#!/usr/bin/env python3
"""Build the reproducible 15-minute detector–CHART panel for the Key Bridge study.

This script deliberately uses route-level CHART matching, not a claimed detector-level
spatial join: CHART provides location text but no point geometry in the supplied extract.
The detector treatment corridor remains the pre-specified geographic I-95/I-895 box.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path('/home/ubuntu/transport_portfolio')
PROJECT = ROOT / 'network_shock_observatory'
OUT = PROJECT / 'outputs'
DATA = ROOT / '.drive_data_audit'
PANEL_2024 = OUT / 'event_panel_2024.parquet'

# Pre-specified detector treatment/control boxes from key_bridge_corridor_design.yaml.
TREATMENT_ROADS = {'I-95', 'I-895'}
CONTROL_ROADS = {'I-83', 'I-795'}
EXCLUDED_DONOR_ROADS = {'I-95', 'I-895', 'I-695'}
BRIDGE_LAT, BRIDGE_LON = 39.2086, -76.5292
MIN_DONOR_DISTANCE_KM, MAX_DONOR_DISTANCE_KM = 30.0, 100.0
MIN_PRE_COVERAGE = 0.90
MIN_PRE_MEDIAN_VOLUME = 20.0
LOCAL_TZ = 'America/New_York'
# The supplied CHART extract contains multi-month planned-roadway-closure records.
# They remain in the event inventory but not in the acute 15-minute incident measure.
ACUTE_DURATION_HOURS = 24.0


def haversine_km(lat: pd.Series, lon: pd.Series) -> pd.Series:
    r = 6371.0088
    phi1, phi2 = np.radians(lat), np.radians(BRIDGE_LAT)
    dphi = np.radians(BRIDGE_LAT - lat)
    dlambda = np.radians(BRIDGE_LON - lon)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def classify_detector_zones(panel: pd.DataFrame) -> pd.DataFrame:
    meta_cols = ['zone_id', 'road', 'direction', 'latitude', 'longitude']
    meta = panel[meta_cols].drop_duplicates('zone_id').copy()
    meta['distance_to_bridge_km'] = haversine_km(meta['latitude'], meta['longitude'])
    is_treatment = (
        meta['road'].isin(TREATMENT_ROADS)
        & meta['latitude'].between(39.20, 39.32)
        & meta['longitude'].between(-76.72, -76.52)
    )
    is_control = (
        meta['road'].isin(CONTROL_ROADS)
        & meta['latitude'].between(39.38, 39.60)
        & meta['longitude'].between(-76.85, -76.64)
    )
    meta['analysis_group'] = 'outside'
    meta.loc[is_treatment, 'analysis_group'] = 'treatment'
    meta.loc[is_control, 'analysis_group'] = 'control'
    meta['is_treatment_geographic'] = is_treatment
    meta['is_control_geographic'] = is_control

    pre = panel.loc[
        (panel['time_bin'] < pd.Timestamp('2024-03-26'))
        & (panel['day_of_week'] < 5),
        ['zone_id', 'valid_speed_observations', 'speed_mph', 'volume']
    ].copy()
    pre['valid_speed'] = (pre['valid_speed_observations'] > 0) & pre['speed_mph'].notna()
    quality = pre.groupby('zone_id', observed=True).agg(
        pre_rows=('valid_speed', 'size'),
        pre_speed_coverage=('valid_speed', 'mean'),
        pre_median_volume=('volume', 'median'),
    ).reset_index()
    meta = meta.merge(quality, on='zone_id', how='left', validate='one_to_one')
    # Retain each component for the public data-quality appendix and to make donor-pool
    # exclusions auditable rather than implicit.
    meta['donor_not_excluded_road'] = ~meta['road'].isin(EXCLUDED_DONOR_ROADS)
    meta['donor_is_interstate'] = meta['road'].fillna('').str.startswith('I-')
    meta['donor_distance_eligible'] = meta['distance_to_bridge_km'].between(MIN_DONOR_DISTANCE_KM, MAX_DONOR_DISTANCE_KM)
    meta['donor_speed_coverage_eligible'] = meta['pre_speed_coverage'] >= MIN_PRE_COVERAGE
    meta['donor_volume_eligible'] = meta['pre_median_volume'] >= MIN_PRE_MEDIAN_VOLUME
    # Use the flags carried through the merge, not the pre-merge Series indices.
    meta['donor_not_treatment'] = ~meta['is_treatment_geographic']
    meta['donor_not_control'] = ~meta['is_control_geographic']
    is_candidate = (
        meta['donor_not_excluded_road']
        & meta['donor_is_interstate']
        & meta['donor_distance_eligible']
        & meta['donor_speed_coverage_eligible']
        & meta['donor_volume_eligible']
        & meta['donor_not_treatment']
        & meta['donor_not_control']
    )
    meta['donor_candidate_eligible'] = is_candidate
    meta.loc[is_candidate, 'analysis_group'] = 'donor_candidate'
    return meta


def route_corridor(location: object) -> str | None:
    """Classify only incidents recorded *on* a study road segment.

    A mere I-95/I-83 token is not enough: e.g., a record beginning with I-695 AT I-95
    belongs to I-695, not to the I-95 treatment corridor.  Because no coordinates are
    provided in CHART, I-95 and I-83 are further limited to the exit/milepost/landmark
    ranges consistent with the pre-specified detector boxes.  This is deliberately
    conservative and is used only for route-level operational-context sensitivity work.
    """
    s = str(location).upper().strip()
    starts = lambda route: bool(re.match(rf'^\s*(?:INTERSTATE\s*)?{route}\b', s))

    # I-895 is a compact facility and lies within the treatment route context; match only
    # events whose primary reported roadway is I-895.
    if starts(r'I[ -]?895'):
        return 'treatment_route_context'

    if starts(r'I[ -]?95'):
        mm = [float(x) for x in re.findall(r'\b(?:MM|M\.M\.|MP)\s*([0-9]+(?:\.[0-9]+)?)', s)]
        exits = [int(x) for x in re.findall(r'\bEXIT\s+(\d+)', s)]
        i95_baltimore_landmarks = r"CATON|RUSSELL|FORT MCHENRY|KEY HWY|KEITH|O['’]DONNELL|EASTERN|MORAVIA|PULASKI|I[ -]?895|I[ -]?695|MD 43|WHITE MARSH|US 40"
        if any(48.0 <= x <= 65.0 for x in mm) or any(49 <= x <= 64 for x in exits) or re.search(i95_baltimore_landmarks, s):
            return 'treatment_route_context'
        return None

    # The full I-795 mainline is within the detector comparison box; primary-road matching
    # avoids picking up I-695 incidents merely mentioning the I-795 interchange.
    if starts(r'I[ -]?795'):
        return 'control_route_context'

    if starts(r'I[ -]?83'):
        exits = [int(x) for x in re.findall(r'\bEXIT\s+(\d+)', s)]
        i83_north_landmarks = r'BALT[IO]*MORE BELTWAY|RUXTON|PADONIA|TIMONIUM|SHAWAN|BELFAST|MT CARMEL|YORK RD|MD 439|DULANEY'
        if any(12 <= x <= 33 for x in exits) or re.search(i83_north_landmarks, s):
            return 'control_route_context'
    return None


def lane_fields(value: object) -> tuple[float, bool]:
    if pd.isna(value) or str(value).strip() == '':
        return np.nan, False
    s = str(value).strip().upper()
    nums = re.findall(r'\d+(?:\.\d+)?', s)
    if nums:
        numeric = float(nums[0])
        return numeric, numeric > 0
    # Text such as "ALL LANES" indicates a reported closure but does not reveal a numeric count.
    return np.nan, bool(re.search(r'ALL|LANE', s))


def prepare_chart(year: int, start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(DATA / f'MDOT_CHART_{year}.csv')
    raw = raw.reset_index(names='chart_row_id')
    raw['event_id'] = raw['chart_row_id'].map(lambda x: f'{year}_{x}')
    raw['start_local'] = pd.to_datetime(raw['Start time'], errors='coerce', utc=True).dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)
    raw['closed_local'] = pd.to_datetime(raw['Closed time'], errors='coerce', utc=True).dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)
    raw['route_context'] = raw['Location'].map(route_corridor)
    raw['standardized_type_norm'] = raw['Standardized Type'].fillna('').astype(str).str.strip().str.lower()
    raw['is_collision'] = raw['standardized_type_norm'].str.contains('collision|crash|accident', regex=True)
    raw['is_roadwork'] = raw['standardized_type_norm'].str.contains('roadwork|construction|maintenance', regex=True)
    raw['is_disabled_vehicle'] = raw['standardized_type_norm'].str.contains('disabled', regex=True)
    raw['is_obstruction'] = raw['standardized_type_norm'].str.contains('obstruction|debris', regex=True)
    lanes = raw['Max Lanes Closed'].map(lane_fields)
    raw['lanes_closed_numeric'] = lanes.map(lambda x: x[0])
    raw['lane_closure_reported'] = lanes.map(lambda x: x[1])
    raw['severe_context_event'] = raw['is_roadwork'] | raw['lane_closure_reported']
    raw['closed_before_start'] = raw['closed_local'] < raw['start_local']
    raw['valid_duration'] = raw['start_local'].notna() & raw['closed_local'].notna() & ~raw['closed_before_start']
    raw['duration_hours'] = (raw['closed_local'] - raw['start_local']).dt.total_seconds() / 3600.0
    raw['acute_duration_eligible'] = raw['valid_duration'] & raw['duration_hours'].le(ACUTE_DURATION_HOURS)
    raw['acute_severe_context_event'] = raw['severe_context_event'] & raw['acute_duration_eligible']
    raw['overlaps_window'] = raw['start_local'].lt(end) & raw['closed_local'].gt(start)
    relevant = raw.loc[
        raw['route_context'].notna() & raw['valid_duration'] & raw['overlaps_window']
    ].copy()
    audit = {
        'year': year,
        'input_events': int(len(raw)),
        'valid_start': int(raw['start_local'].notna().sum()),
        'valid_closed': int(raw['closed_local'].notna().sum()),
        'negative_duration': int(raw['closed_before_start'].sum()),
        'route_matched_all_dates': int(raw['route_context'].notna().sum()),
        'route_matched_window_valid_duration': int(len(relevant)),
        'route_context_counts_window': relevant['route_context'].value_counts().to_dict(),
        'acute_duration_threshold_hours': ACUTE_DURATION_HOURS,
        'acute_severe_context_events_window': int(relevant['acute_severe_context_event'].sum()),
        'long_duration_severe_context_events_window': int((relevant['severe_context_event'] & ~relevant['acute_duration_eligible']).sum()),
        'standardized_type_counts_window': relevant['Standardized Type'].fillna('Missing').value_counts().to_dict(),
        'location_matching_rule': 'primary-road match only. I-895 and I-795 are full-facility route contexts; I-95 and I-83 also require a Baltimore study-segment exit/milepost/landmark match. Event is not assigned to an individual detector zone.',
    }
    keep = [
        'event_id', 'chart_row_id', 'Agency', 'Standardized Type', 'Agency-specific Type',
        'Start time', 'Closed time', 'Location', 'Max Lanes Closed', 'start_local', 'closed_local',
        'route_context', 'is_collision', 'is_roadwork', 'is_disabled_vehicle', 'is_obstruction',
        'lanes_closed_numeric', 'lane_closure_reported', 'severe_context_event', 'duration_hours',
        'acute_duration_eligible', 'acute_severe_context_event'
    ]
    return relevant[keep], audit


def chart_burden_15min(events: pd.DataFrame, bins: pd.DatetimeIndex) -> pd.DataFrame:
    columns = [
        'active_event_count', 'active_collision_count', 'active_roadwork_count',
        'active_disabled_vehicle_count', 'active_obstruction_count', 'active_severe_context_count',
        'active_acute_severe_context_count', 'active_lane_closure_event_count', 'lanes_closed_observed_sum',
        'any_severe_context_event', 'any_acute_severe_context_event'
    ]
    out_frames = []
    freq = pd.Timedelta(minutes=15)
    for context in ['treatment_route_context', 'control_route_context']:
        arr = np.zeros((len(bins), len(columns) - 1), dtype=float)
        subset = events.loc[events['route_context'].eq(context)]
        for row in subset.itertuples(index=False):
            # A bin is active if [bin, bin+15 min) overlaps [start, closed). Events with zero duration
            # are not treated as an interval exposure.
            lo = pd.Timestamp(row.start_local).floor('15min')
            hi = pd.Timestamp(row.closed_local).ceil('15min')
            lo = max(lo, bins[0])
            hi = min(hi, bins[-1] + freq)
            if lo >= hi:
                continue
            # The detector panel deliberately covers weekday 05:00–21:45 only. Use its
            # observed-support mask rather than assuming a 24-hour contiguous grid.
            active = (bins >= lo) & (bins < hi)
            arr[active, 0] += 1
            arr[active, 1] += int(row.is_collision)
            arr[active, 2] += int(row.is_roadwork)
            arr[active, 3] += int(row.is_disabled_vehicle)
            arr[active, 4] += int(row.is_obstruction)
            arr[active, 5] += int(row.severe_context_event)
            arr[active, 6] += int(row.acute_severe_context_event)
            arr[active, 7] += int(row.lane_closure_reported)
            if pd.notna(row.lanes_closed_numeric):
                arr[active, 8] += float(row.lanes_closed_numeric)
        frame = pd.DataFrame(arr, columns=columns[:-1])
        frame.insert(0, 'time_bin', bins)
        frame.insert(1, 'route_context', context)
        frame['any_severe_context_event'] = frame['active_severe_context_count'].gt(0)
        frame['any_acute_severe_context_event'] = frame['active_acute_severe_context_count'].gt(0)
        out_frames.append(frame)
    return pd.concat(out_frames, ignore_index=True)


def aggregate_detector_context(panel: pd.DataFrame, zone_meta: pd.DataFrame, chart: pd.DataFrame) -> pd.DataFrame:
    needed = panel.merge(zone_meta[['zone_id', 'analysis_group']], on='zone_id', how='left', validate='many_to_one')
    needed = needed.loc[needed['analysis_group'].isin(['treatment', 'control'])].copy()
    needed['route_context'] = np.where(
        needed['analysis_group'].eq('treatment'), 'treatment_route_context', 'control_route_context'
    )
    needed['speed_numerator'] = needed['speed_x_volume'].where(needed['volume_for_speed'].gt(0), 0.0)
    needed['speed_denominator'] = needed['volume_for_speed'].where(needed['volume_for_speed'].gt(0), 0.0)
    agg = needed.groupby(['time_bin', 'analysis_group', 'route_context'], observed=True).agg(
        total_volume=('volume', 'sum'),
        speed_numerator=('speed_numerator', 'sum'),
        speed_denominator=('speed_denominator', 'sum'),
        mean_occupancy=('occupancy', 'mean'),
        zones_observed=('zone_id', 'nunique'),
        detector_rows=('zone_id', 'size'),
        valid_speed_zones=('valid_speed_observations', lambda s: int((s > 0).sum())),
    ).reset_index()
    agg['volume_weighted_speed_mph'] = agg['speed_numerator'] / agg['speed_denominator']
    agg['log1p_total_volume'] = np.log1p(agg['total_volume'])
    merged = agg.merge(chart, on=['time_bin', 'route_context'], how='left', validate='one_to_one')
    chart_cols = [c for c in chart.columns if c.startswith('active_') or c in {'lanes_closed_observed_sum', 'any_severe_context_event'}]
    for col in chart_cols:
        if col == 'any_severe_context_event':
            merged[col] = merged[col].fillna(False).astype(bool)
        else:
            merged[col] = merged[col].fillna(0.0)
    return merged


def main() -> None:
    panel = pd.read_parquet(PANEL_2024)
    panel['time_bin'] = pd.to_datetime(panel['time_bin'])
    panel = panel.loc[panel['day_of_week'] < 5].copy()
    # All 15-minute bins in the retained detector panel are used to avoid inventing observations.
    bins = pd.DatetimeIndex(sorted(panel['time_bin'].unique()))
    # The prepared detector event panel was intentionally extracted for weekday 05:00–21:45.
    # Verify this observed support rather than incorrectly requiring overnight observations.
    expected = pd.DatetimeIndex([
        day + pd.Timedelta(minutes=15 * slot)
        for day in pd.date_range(bins.min().normalize(), bins.max().normalize(), freq='D')
        if day.dayofweek < 5
        for slot in range(20, 88)  # 05:00 through 21:45, inclusive
    ])
    # Preserve global gaps as a data-quality finding; do not impute detector outcomes or
    # fabricate CHART exposure rows for intervals with no detector observation anywhere.
    support_missing = expected.difference(bins)
    support_extra = bins.difference(expected)

    zone_meta = classify_detector_zones(panel)
    panel = panel.merge(zone_meta[['zone_id', 'analysis_group']], on='zone_id', how='left', validate='many_to_one')
    start, end = bins.min(), bins.max() + pd.Timedelta(minutes=15)
    chart_2024, chart_2024_audit = prepare_chart(2024, start, end)
    chart_2023, chart_2023_audit = prepare_chart(
        2023, pd.Timestamp('2023-03-27 00:00:00'), pd.Timestamp('2023-04-24 00:00:00')
    )
    burden = chart_burden_15min(chart_2024, bins)
    corridor = aggregate_detector_context(panel.drop(columns=['analysis_group']), zone_meta, burden)

    # A zone-time panel is retained for SCM estimation; CHART burden is intentionally route-level.
    chart_map = burden.rename(columns={'route_context': 'chart_route_context'})
    panel_for_join = panel.copy()
    panel_for_join['chart_route_context'] = np.select(
        [panel_for_join['analysis_group'].eq('treatment'), panel_for_join['analysis_group'].eq('control')],
        ['treatment_route_context', 'control_route_context'],
        default='unmatched_detector_group'
    )
    joined = panel_for_join.merge(chart_map, on=['time_bin', 'chart_route_context'], how='left')
    chart_cols = [c for c in burden.columns if c.startswith('active_') or c in {'lanes_closed_observed_sum', 'any_severe_context_event'}]
    for col in chart_cols:
        if col == 'any_severe_context_event':
            joined[col] = joined[col].fillna(False).astype(bool)
        else:
            joined[col] = joined[col].fillna(0.0)

    # Keep SCM input compact and explicit: treated zones and external candidate donors only.
    scm = joined.loc[joined['analysis_group'].isin(['treatment', 'donor_candidate'])].copy()
    scm['scm_unit'] = np.where(scm['analysis_group'].eq('treatment'), 'TREATMENT_AGG_COMPONENT', scm['zone_id'].astype(str))

    # Seasonal CHART descriptive comparison is a separate, non-causal annual-rate table.
    def season_summary(x: pd.DataFrame, year: int) -> pd.DataFrame:
        return x.groupby('route_context', observed=True).agg(
            events=('event_id', 'nunique'),
            collisions=('is_collision', 'sum'),
            roadwork=('is_roadwork', 'sum'),
            disabled_vehicles=('is_disabled_vehicle', 'sum'),
            lane_closure_events=('lane_closure_reported', 'sum'),
            total_observed_minutes=('closed_local', lambda s: 0),
        ).reset_index().assign(year=year)
    # Duration summary is calculated directly; unavailable/invalid durations were excluded by construction.
    for x in (chart_2024, chart_2023):
        x['duration_minutes'] = (x['closed_local'] - x['start_local']).dt.total_seconds() / 60.0
    seasonal = pd.concat([
        chart_2024.groupby('route_context', observed=True).agg(
            events=('event_id', 'nunique'), collisions=('is_collision', 'sum'), roadwork=('is_roadwork', 'sum'),
            disabled_vehicles=('is_disabled_vehicle', 'sum'), lane_closure_events=('lane_closure_reported', 'sum'),
            observed_event_minutes=('duration_minutes', 'sum')
        ).reset_index().assign(year=2024),
        chart_2023.groupby('route_context', observed=True).agg(
            events=('event_id', 'nunique'), collisions=('is_collision', 'sum'), roadwork=('is_roadwork', 'sum'),
            disabled_vehicles=('is_disabled_vehicle', 'sum'), lane_closure_events=('lane_closure_reported', 'sum'),
            observed_event_minutes=('duration_minutes', 'sum')
        ).reset_index().assign(year=2023),
    ], ignore_index=True)

    zone_meta.to_csv(OUT / 'detector_chart_zone_classification_2024.csv', index=False)
    chart_2024.to_csv(OUT / 'chart_route_matched_events_2024.csv', index=False)
    chart_2023.to_csv(OUT / 'chart_route_matched_events_2023_seasonal.csv', index=False)
    burden.to_parquet(OUT / 'chart_route_burden_15min_2024.parquet', index=False)
    corridor.to_csv(OUT / 'detector_chart_corridor_15min_2024.csv', index=False)
    joined.to_parquet(OUT / 'detector_chart_zone_time_2024.parquet', index=False)
    scm.to_parquet(OUT / 'scm_zone_time_input_2024.parquet', index=False)
    seasonal.to_csv(OUT / 'chart_route_seasonal_descriptives_2023_2024.csv', index=False)

    audit = {
        'detector_window': {
            'start': str(bins.min()), 'end_exclusive': str(end), 'n_15min_bins': int(len(bins)),
            'declared_weekday_0500_2145_bins': int(len(expected)),
            'global_detector_bins_missing_no_imputation': int(len(support_missing)),
            'first_global_detector_bins_missing': [str(x) for x in support_missing[:10]],
            'unexpected_global_detector_bins': int(len(support_extra)),
        },
        'detector_rows_weekdays': int(len(panel)),
        'zone_group_counts': zone_meta['analysis_group'].value_counts().to_dict(),
        'donor_candidate_eligible_count': int(zone_meta['donor_candidate_eligible'].sum()),
        'zone_quality_by_group': zone_meta.groupby('analysis_group', observed=True).agg(
            zones=('zone_id', 'nunique'), median_pre_speed_coverage=('pre_speed_coverage', 'median'),
            median_pre_volume=('pre_median_volume', 'median')
        ).round(4).to_dict(orient='index'),
        'chart_2024': chart_2024_audit,
        'chart_2023_seasonal': chart_2023_audit,
        'join_boundary': 'CHART variables are conservatively matched route-segment context measures created from primary-road location text; they are not detector-zone exposures.',
        'zero_filling_rule': 'A zero burden means no valid-duration event with a direct route-token match was active in the bin. It does not prove no incident occurred on the roadway.',
        'severe_context_definition': 'All-duration severe context is standardized roadwork/construction/maintenance OR a CHART event with reported positive/textual lane closure. Acute severe context additionally requires valid CHART duration of 24 hours or less; multi-month planned-roadway-closure records remain in the inventory but are not treated as active acute incident exposure. Neither measure is included in the main total-effect SCM outcome model.',
    }
    (OUT / 'detector_chart_panel_quality_audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()

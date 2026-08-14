#!/usr/bin/env python3
"""CHART-informed sensitivity and descriptive context for the Key Bridge detector study.

Important causal boundary: CHART events after 2024-03-26 may themselves be consequences
or mediators of the collapse-induced network shock. They are therefore *not* controls in
the main detector-based SCM. This script labels every conditioned model as a sensitivity
or conditional association, never as the total causal effect.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PROJECT = Path('/home/ubuntu/transport_portfolio/network_shock_observatory')
OUT = PROJECT / 'outputs'
EVENT = pd.Timestamp('2024-03-26')
POST_START = pd.Timestamp('2024-03-27')
POST_END = pd.Timestamp('2024-04-23 21:45:00')
SEASON_START_DAY = '03-27'
SEASON_END_DAY_EXCLUSIVE = '04-24'
# This is a secondary, mediator-conditioned diagnostic rather than the primary SCM.
# 250 stratified day-block draws provide a reproducible percentile uncertainty summary
# without creating a false sense of precision from a route-text-matched context measure.
N_BOOT = 250
SEED = 20260813


def add_time_of_week_dummies(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    out = df.copy()
    out['tow'] = out['time_bin'].dt.dayofweek.astype(str) + '_' + out['time_bin'].dt.strftime('%H:%M')
    dummies = pd.get_dummies(out['tow'], prefix='tow', dtype=float)
    # The omitted category is a deterministic reference; all remaining time-of-week effects
    # simply absorb recurring differences in corridor pair gaps.
    dummies = dummies.iloc[:, 1:]
    out = pd.concat([out, dummies], axis=1)
    return out, list(dummies.columns)


def ols_coef(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, float]:
    coef, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ coef
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return coef, r2


def day_block_bootstrap(df: pd.DataFrame, y_col: str, x_cols: list[str], post_idx: int) -> tuple[float, float, float]:
    """Stratified resampling of complete pre/post days; percentile interval for post coefficient."""
    rng = np.random.default_rng(SEED)
    pre_days = np.array(sorted(df.loc[df['post'].eq(0), 'date'].unique()))
    post_days = np.array(sorted(df.loc[df['post'].eq(1), 'date'].unique()))
    by_day = {d: g.index.to_numpy() for d, g in df.groupby('date', observed=True)}
    draws = []
    for _ in range(N_BOOT):
        chosen = np.concatenate([
            *[by_day[d] for d in rng.choice(pre_days, size=len(pre_days), replace=True)],
            *[by_day[d] for d in rng.choice(post_days, size=len(post_days), replace=True)],
        ])
        sample = df.loc[chosen]
        x = sample[x_cols].to_numpy(dtype=float)
        y = sample[y_col].to_numpy(dtype=float)
        b, _ = ols_coef(y, x)
        draws.append(float(b[post_idx]))
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.50)), float(np.quantile(draws, 0.975))


def fit_pair_difference_models(corridor: pd.DataFrame) -> pd.DataFrame:
    """Fit detector corridor-pair gap models with and without CHART context differences."""
    use = corridor.loc[
        corridor['time_bin'].between(pd.Timestamp('2024-02-12 05:00:00'), POST_END)
        & ~corridor['time_bin'].dt.normalize().eq(EVENT)
    ].copy()
    fields = [
        'volume_weighted_speed_mph', 'log1p_total_volume', 'active_acute_severe_context_count',
        'active_collision_count', 'active_disabled_vehicle_count', 'lanes_closed_observed_sum'
    ]
    pivot = use.pivot(index='time_bin', columns='analysis_group', values=fields)
    pair = pd.DataFrame(index=pivot.index)
    pair['time_bin'] = pair.index
    pair['date'] = pair['time_bin'].dt.normalize()
    pair['post'] = (pair['time_bin'] >= POST_START).astype(int)
    pair['speed_gap_treatment_minus_control'] = pivot['volume_weighted_speed_mph']['treatment'] - pivot['volume_weighted_speed_mph']['control']
    pair['log_volume_gap_treatment_minus_control'] = pivot['log1p_total_volume']['treatment'] - pivot['log1p_total_volume']['control']
    pair['delta_acute_severe_context'] = pivot['active_acute_severe_context_count']['treatment'] - pivot['active_acute_severe_context_count']['control']
    pair['delta_collision'] = pivot['active_collision_count']['treatment'] - pivot['active_collision_count']['control']
    pair['delta_disabled_vehicle'] = pivot['active_disabled_vehicle_count']['treatment'] - pivot['active_disabled_vehicle_count']['control']
    pair['delta_lanes_closed_observed'] = pivot['lanes_closed_observed_sum']['treatment'] - pivot['lanes_closed_observed_sum']['control']
    pair = pair.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    pair, time_fe = add_time_of_week_dummies(pair)

    model_specs = {
        'unadjusted_pair_gap': [],
        'CHART_conditioned_pair_gap': [
            'delta_acute_severe_context', 'delta_collision', 'delta_disabled_vehicle', 'delta_lanes_closed_observed'
        ],
    }
    rows = []
    for outcome, y_col, scale in [
        ('speed_mph', 'speed_gap_treatment_minus_control', 'mph'),
        ('log_total_volume', 'log_volume_gap_treatment_minus_control', 'log points'),
    ]:
        for model_name, chart_vars in model_specs.items():
            x_cols = ['intercept', 'post'] + chart_vars + time_fe
            temp = pair.copy()
            temp['intercept'] = 1.0
            beta, r2 = ols_coef(temp[y_col].to_numpy(dtype=float), temp[x_cols].to_numpy(dtype=float))
            lo, med, hi = day_block_bootstrap(temp, y_col, x_cols, post_idx=1)
            row = {
                'outcome': outcome,
                'model': model_name,
                'post_treatment_minus_control_coefficient': float(beta[1]),
                'day_block_bootstrap_ci_2_5': lo,
                'day_block_bootstrap_median': med,
                'day_block_bootstrap_ci_97_5': hi,
                'n_15min_pair_observations': int(len(temp)),
                'n_calendar_days': int(temp['date'].nunique()),
                'r_squared': r2,
                'chart_context_terms': ', '.join(chart_vars) if chart_vars else 'none',
            }
            if outcome == 'log_total_volume':
                row['approximate_percent_change'] = float(100 * (np.exp(beta[1]) - 1))
            rows.append(row)
    pair.to_csv(OUT / 'chart_pair_difference_input_2024.csv', index=False)
    return pd.DataFrame(rows)


def scm_nonsevere_sensitivity() -> pd.DataFrame:
    """Re-fit detector SCM on times without a CHART severe context in the treatment route."""
    import sys
    sys.path.insert(0, str(PROJECT / 'src'))
    from estimate_true_synthetic_control import build_balanced_matrix, compute_scm_for_target_series

    frame = pd.read_parquet(OUT / 'detector_chart_zone_time_2024.parquet')
    frame['time_bin'] = pd.to_datetime(frame['time_bin'])
    corridor = pd.read_csv(OUT / 'detector_chart_corridor_15min_2024.csv', parse_dates=['time_bin'])
    severe = corridor.loc[corridor['analysis_group'].eq('treatment'), ['time_bin', 'any_acute_severe_context_event']].drop_duplicates('time_bin').set_index('time_bin')['any_acute_severe_context_event']
    rows = []
    for output_name, source_col in {'speed_mph': 'speed_mph', 'mean_zone_log1p_volume': 'log1p_volume'}.items():
        times, wide, y, treated_zones, donors = build_balanced_matrix(frame, source_col)
        no_severe = ~severe.reindex(times).fillna(False).to_numpy(dtype=bool)
        pre = np.asarray(times < EVENT, dtype=bool) & no_severe
        post = np.asarray((times >= POST_START) & (times <= POST_END), dtype=bool) & no_severe
        treated, synthetic, _, diag = compute_scm_for_target_series(wide, y, donors, pre)
        gap = treated - synthetic
        pre_rmspe = float(np.sqrt(np.mean(gap.loc[pre].to_numpy() ** 2)))
        post_rmspe = float(np.sqrt(np.mean(gap.loc[post].to_numpy() ** 2)))
        row = {
            'outcome': output_name,
            'conditioning': 'CHART treatment-route acute severe-context bins excluded (valid duration ≤24 hours)',
            'pre_15min_bins_retained': int(pre.sum()),
            'post_15min_bins_retained': int(post.sum()),
            'post_15min_bins_excluded': int(np.asarray((times >= POST_START) & (times <= POST_END), dtype=bool).sum() - post.sum()),
            'mean_gap_treated_minus_synthetic_full_post_retained_bins': float(gap.loc[post].mean()),
            'pre_rmspe': pre_rmspe,
            'post_rmspe': post_rmspe,
            'post_pre_rmspe_ratio': post_rmspe / pre_rmspe if pre_rmspe > 0 else np.nan,
            'effective_donor_count': diag['effective_donor_count'],
        }
        if output_name == 'mean_zone_log1p_volume':
            row['approximate_percent_change_from_gap'] = float(100 * (np.exp(row['mean_gap_treated_minus_synthetic_full_post_retained_bins']) - 1))
        rows.append(row)
    return pd.DataFrame(rows)


def seasonal_chart_descriptives() -> pd.DataFrame:
    rows = []
    for year, path in [(2023, OUT / 'chart_route_matched_events_2023_seasonal.csv'), (2024, OUT / 'chart_route_matched_events_2024.csv')]:
        events = pd.read_csv(path, parse_dates=['start_local', 'closed_local'])
        start = pd.Timestamp(f'{year}-{SEASON_START_DAY} 00:00:00')
        end = pd.Timestamp(f'{year}-{SEASON_END_DAY_EXCLUSIVE} 00:00:00')
        active = events.loc[(events['start_local'] < end) & (events['closed_local'] > start)].copy()
        active['overlap_start'] = active['start_local'].clip(lower=start)
        active['overlap_end'] = active['closed_local'].clip(upper=end)
        active['overlap_minutes'] = (active['overlap_end'] - active['overlap_start']).dt.total_seconds() / 60.0
        started = active.loc[active['start_local'].between(start, end, inclusive='left')].copy()
        for context, d in active.groupby('route_context', observed=True):
            s = started.loc[started['route_context'].eq(context)]
            rows.append({
                'year': year,
                'season_window': f'{start.date()} to {(end - pd.Timedelta(days=1)).date()}',
                'route_context': context,
                'active_events_overlapping_window': int(len(d)),
                'events_started_in_window': int(len(s)),
                'collisions_started_in_window': int(s['is_collision'].sum()),
                'roadwork_started_in_window': int(s['is_roadwork'].sum()),
                'disabled_vehicles_started_in_window': int(s['is_disabled_vehicle'].sum()),
                'lane_closure_events_started_in_window': int(s['lane_closure_reported'].sum()),
                'overlap_event_minutes_all_hours': float(d['overlap_minutes'].sum()),
                'days_in_window': int((end - start).days),
            })
    result = pd.DataFrame(rows)
    result['events_started_per_day'] = result['events_started_in_window'] / result['days_in_window']
    result['collision_started_per_day'] = result['collisions_started_in_window'] / result['days_in_window']
    return result


def chart_detector_context(corridor: pd.DataFrame) -> pd.DataFrame:
    use = corridor.loc[
        corridor['time_bin'].between(pd.Timestamp('2024-02-12 05:00:00'), POST_END)
        & ~corridor['time_bin'].dt.normalize().eq(EVENT)
    ].copy()
    use['period'] = np.where(use['time_bin'] < EVENT, 'pre', 'post')
    return use.groupby(['analysis_group', 'period'], observed=True).agg(
        n_15min_bins=('time_bin', 'size'),
        mean_speed_mph=('volume_weighted_speed_mph', 'mean'),
        mean_log_total_volume=('log1p_total_volume', 'mean'),
        mean_active_events=('active_event_count', 'mean'),
        mean_active_collisions=('active_collision_count', 'mean'),
        mean_active_roadwork=('active_roadwork_count', 'mean'),
        mean_active_disabled_vehicles=('active_disabled_vehicle_count', 'mean'),
        share_bins_acute_severe_context=('any_acute_severe_context_event', 'mean'),
        share_bins_all_duration_severe_context=('any_severe_context_event', 'mean'),
        mean_observed_lanes_closed=('lanes_closed_observed_sum', 'mean'),
    ).reset_index()


def make_figure(corridor: pd.DataFrame, seasonal: pd.DataFrame) -> None:
    d = corridor.copy()
    d['date'] = d['time_bin'].dt.normalize()
    daily = d.groupby(['analysis_group', 'date'], observed=True).agg(
        severe_share=('any_acute_severe_context_event', 'mean'),
        active_events=('active_event_count', 'mean')
    ).reset_index()
    daily['severe_share_3d'] = daily.groupby('analysis_group', observed=True)['severe_share'].transform(lambda x: x.rolling(3, min_periods=1).mean())
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.7), constrained_layout=True)
    colors = {'treatment': '#A04B00', 'control': '#132A45'}
    labels = {'treatment': 'I-95/I-895 treatment corridor', 'control': 'I-83/I-795 comparison corridor'}
    for group, g in daily.groupby('analysis_group', observed=True):
        axes[0].plot(g['date'], 100 * g['severe_share_3d'], lw=1.8, color=colors[group], label=labels[group])
    axes[0].axvline(EVENT, color='black', ls=':', lw=1)
    axes[0].set_title('CHART acute severe-context exposure (3-day rolling share)')
    axes[0].set_ylabel('Percent of observed 15-minute bins')
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].grid(axis='y', alpha=0.25)

    plot = seasonal.pivot(index='route_context', columns='year', values='events_started_per_day')
    plot = plot.reindex(['treatment_route_context', 'control_route_context'])
    x = np.arange(len(plot))
    width = 0.34
    axes[1].bar(x - width / 2, plot.get(2023, pd.Series(index=plot.index, dtype=float)), width, label='2023', color='#8FA7BF')
    axes[1].bar(x + width / 2, plot.get(2024, pd.Series(index=plot.index, dtype=float)), width, label='2024', color='#A04B00')
    axes[1].set_xticks(x, ['I-95/I-895\nroute context', 'I-83/I-795\nroute context'])
    axes[1].set_ylabel('Conservatively matched CHART events started per calendar day')
    axes[1].set_title('Same-calendar seasonal CHART event rate')
    axes[1].legend(frameon=False)
    axes[1].grid(axis='y', alpha=0.25)
    fig.suptitle('MDOT CHART acute operational context; descriptive, not causal adjustment', fontsize=13, fontweight='bold')
    fig.savefig(OUT / 'fig_chart_operational_context_2024.png', dpi=220, bbox_inches='tight')
    plt.close(fig)


def main() -> None:
    corridor = pd.read_csv(OUT / 'detector_chart_corridor_15min_2024.csv', parse_dates=['time_bin'])
    corridor = corridor.loc[corridor['analysis_group'].isin(['treatment', 'control'])].copy()
    sensitivity_scm = scm_nonsevere_sensitivity()
    pair_models = fit_pair_difference_models(corridor)
    seasonal = seasonal_chart_descriptives()
    context = chart_detector_context(corridor)
    sensitivity_scm.to_csv(OUT / 'chart_sensitive_scm_results_2024.csv', index=False)
    pair_models.to_csv(OUT / 'chart_conditioned_pair_gap_models_2024.csv', index=False)
    seasonal.to_csv(OUT / 'chart_same_calendar_seasonal_descriptives_2023_2024.csv', index=False)
    context.to_csv(OUT / 'chart_detector_context_pre_post_2024.csv', index=False)
    make_figure(corridor, seasonal)
    audit = {
        'causal_boundary': 'CHART post-event incidents may be mediators of collapse-induced congestion and rerouting. They are excluded from the main total-effect SCM. Non-severe restriction and CHART-conditioned pair-gap models are descriptive sensitivity analyses only.',
        'chart_spatial_rule': 'Primary-road text match; I-895/I-795 are full facility contexts; I-95/I-83 require Baltimore study-segment exit/milepost/landmark match. No event is assigned to a detector zone.',
        'pair_model': 'Treatment-minus-control 15-minute detector outcome gap regressed on post indicator, recurring weekday×time-of-day effects, and optional treatment-minus-control CHART context differences. Percentile intervals use 250 stratified pre/post day-block resamples.',
        'scm_sensitivity': 'SCM re-estimated using only times without a matched acute severe CHART context event (valid duration 24 hours or less) on the treatment route; conditioning changes the estimand and does not identify the total collapse effect.',
        'seasonal_descriptive_window': 'March 27–April 23 in each year; event counts are non-causal and based on conservative CHART route-segment text matching.',
        'n_bootstrap_day_blocks': N_BOOT,
        'seed': SEED,
    }
    (OUT / 'chart_sensitivity_analysis_audit_2024.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps({
        'scm_sensitivity': sensitivity_scm.to_dict(orient='records'),
        'pair_models': pair_models.to_dict(orient='records'),
        'seasonal': seasonal.to_dict(orient='records'),
        'context': context.to_dict(orient='records'),
        'audit': audit,
    }, indent=2, default=str))


if __name__ == '__main__':
    main()

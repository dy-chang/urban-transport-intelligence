#!/usr/bin/env python3
"""Estimate a genuine detector-based Synthetic Control for the Key Bridge corridor.

The primary estimator is a conventional simplex-constrained synthetic control:
nonnegative donor weights sum to one and are chosen using only pre-collapse 15-minute
outcomes.  The code never labels a simple comparison-corridor gap as SCM.

This is a traffic-operations analysis, not an individual-route-choice analysis.  The
outcome is the equally weighted mean across a balanced set of pre-specified treatment
zones.  Speed is in mph; log volume is the mean of zone-level log(1 + 15-minute volume).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize

ROOT = Path('/home/ubuntu/transport_portfolio/network_shock_observatory')
OUT = ROOT / 'outputs'
INPUT = OUT / 'detector_chart_zone_time_2024.parquet'
EVENT_DATE = pd.Timestamp('2024-03-26')
POST_START = pd.Timestamp('2024-03-27')
POST_END = pd.Timestamp('2024-04-23 21:45:00')
PSEUDO_EVENT = pd.Timestamp('2024-03-04')
PSEUDO_POST_START = pd.Timestamp('2024-03-05')
PSEUDO_POST_END = pd.Timestamp('2024-03-25 21:45:00')
# Tiny ridge stabilizer prevents arbitrary weight splitting among nearly collinear lanes
# while retaining the standard nonnegative, sum-to-one SCM geometry.
RIDGE_LAMBDA = 1e-6
MAX_ITER = 5000
TOL = 1e-10
OUTCOMES = {
    'speed_mph': 'speed_mph',
    'mean_zone_log1p_volume': 'log1p_volume',
}


def simplex_scm(y: np.ndarray, x: np.ndarray, ridge: float = RIDGE_LAMBDA) -> tuple[np.ndarray, dict]:
    """Fit conventional SCM weights with nonnegative weights that sum to one."""
    if x.ndim != 2 or len(y) != x.shape[0]:
        raise ValueError('Expected y[T] and x[T, J].')
    if not np.isfinite(y).all() or not np.isfinite(x).all():
        raise ValueError('SCM input contains non-finite values.')
    j = x.shape[1]
    if j < 2:
        raise ValueError('At least two donor units are required.')
    x0 = np.full(j, 1.0 / j)

    def fun(w: np.ndarray) -> float:
        residual = y - x @ w
        return float(np.mean(residual ** 2) + ridge * np.sum(w ** 2))

    def jac(w: np.ndarray) -> np.ndarray:
        residual = y - x @ w
        return (-2.0 / len(y)) * (x.T @ residual) + 2.0 * ridge * w

    result = minimize(
        fun, x0, jac=jac, method='SLSQP', bounds=[(0.0, 1.0)] * j,
        constraints={'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0, 'jac': lambda w: np.ones(j)},
        options={'maxiter': MAX_ITER, 'ftol': TOL, 'disp': False},
    )
    if not result.success or abs(result.x.sum() - 1.0) > 1e-7 or (result.x < -1e-9).any():
        raise RuntimeError(f'SCM optimization failed: {result.message}')
    diag = {
        'optimizer_success': bool(result.success),
        'optimizer_message': str(result.message),
        'objective': float(result.fun),
        'weight_sum': float(result.x.sum()),
        'minimum_weight': float(result.x.min()),
        'effective_donor_count': float(1.0 / np.sum(result.x ** 2)),
    }
    return result.x, diag


def build_balanced_matrix(frame: pd.DataFrame, outcome: str) -> tuple[pd.DatetimeIndex, pd.DataFrame, pd.Series, list[int], list[int]]:
    """Create a balanced donor matrix and a fixed, non-imputed treated-corridor outcome.

    Detector speeds are not reported where a low-volume zone has no valid speed reading.
    Requiring every individual treatment zone to have every reading would discard the whole
    treated corridor.  Instead, the treatment outcome is calculated directly from all
    pre-specified treatment zones at each observed 15-minute time: volume-weighted speed
    uses the supplied speed numerator/denominator; log volume is the mean across the fixed
    treatment zone set.  No missing outcome is imputed.  Donors remain individually
    balanced so the SCM weight matrix contains no missing values.
    """
    base = frame.loc[
        frame['analysis_group'].isin(['treatment', 'donor_candidate'])
        & frame['time_bin'].between(pd.Timestamp('2024-02-12 05:00:00'), POST_END)
        & ~frame['time_bin'].dt.normalize().eq(EVENT_DATE),
    ].copy()
    candidate_times = pd.DatetimeIndex(sorted(base['time_bin'].unique()))
    all_treated = sorted(base.loc[base['analysis_group'].eq('treatment'), 'zone_id'].drop_duplicates().astype(int).tolist())
    treated_base = base.loc[base['analysis_group'].eq('treatment')].copy()
    if outcome == 'speed_mph':
        treated_agg = treated_base.groupby('time_bin', observed=True).agg(
            numerator=('speed_x_volume', 'sum'), denominator=('volume_for_speed', 'sum')
        )
        treated_y = treated_agg['numerator'] / treated_agg['denominator']
    else:
        treated_y = treated_base.groupby('time_bin', observed=True)[outcome].mean()
    treated_y = treated_y.reindex(candidate_times)
    # Preserve the observed-data principle: bins with no corridor speed denominator are
    # removed from both treated and donor series, never filled or interpolated.
    expected_times = candidate_times[treated_y.notna().to_numpy()]
    dropped_treatment_outcome_bins = int(len(candidate_times) - len(expected_times))
    treated_y = treated_y.reindex(expected_times)

    donor_base = base.loc[:, ['time_bin', 'zone_id', 'analysis_group', outcome]].copy()
    donor_base[outcome] = pd.to_numeric(donor_base[outcome], errors='coerce')
    donor_base = donor_base.loc[donor_base['analysis_group'].eq('donor_candidate') & np.isfinite(donor_base[outcome])]
    counts = donor_base.groupby('zone_id', observed=True)['time_bin'].nunique()
    donors = sorted(counts.index[counts.eq(len(expected_times))].astype(int).tolist())
    if len(all_treated) < 5 or len(donors) < 5:
        raise ValueError(f'Insufficient units for {outcome}: treated={len(all_treated)}, complete donors={len(donors)}')
    wide = donor_base.loc[donor_base['zone_id'].isin(donors)].pivot(index='time_bin', columns='zone_id', values=outcome).reindex(expected_times)
    if wide.isna().any().any():
        raise ValueError('Unexpected missing donor value after complete-coverage selection.')
    wide.attrs['dropped_treatment_outcome_bins_no_imputation'] = dropped_treatment_outcome_bins
    return expected_times, wide, treated_y, all_treated, donors


def compute_scm_for_target_series(wide: pd.DataFrame, target_y: pd.Series, donor_units: Iterable[int], pre_mask: np.ndarray) -> tuple[pd.Series, pd.Series, np.ndarray, dict]:
    donor_units = list(donor_units)
    y = target_y.reindex(wide.index).to_numpy(dtype=float)
    x = wide[donor_units].to_numpy(dtype=float)
    weights, diag = simplex_scm(y[pre_mask], x[pre_mask, :])
    synthetic = x @ weights
    return pd.Series(y, index=wide.index), pd.Series(synthetic, index=wide.index), weights, diag


def compute_scm_for_target(wide: pd.DataFrame, target_units: Iterable[int], donor_units: Iterable[int], pre_mask: np.ndarray) -> tuple[pd.Series, pd.Series, np.ndarray, dict]:
    target_units = list(target_units)
    donor_units = list(donor_units)
    y = wide[target_units].mean(axis=1).to_numpy(dtype=float)
    x = wide[donor_units].to_numpy(dtype=float)
    weights, diag = simplex_scm(y[pre_mask], x[pre_mask, :])
    synthetic = x @ weights
    return pd.Series(y, index=wide.index), pd.Series(synthetic, index=wide.index), weights, diag


def period_effects(times: pd.DatetimeIndex, gap: pd.Series, pre_mask: np.ndarray, post_mask: np.ndarray, outcome_name: str) -> list[dict]:
    rows = []
    pre_gap = gap.loc[pre_mask]
    for label, n_days in [('first_5_weekdays', 5), ('first_10_weekdays', 10), ('full_20_weekdays', 20)]:
        post_dates = pd.DatetimeIndex(sorted(pd.Series(times[post_mask].normalize()).unique()))[:n_days]
        mask = pd.Series(times.normalize().isin(post_dates), index=times)
        value = gap.loc[mask.values].mean()
        row = {
            'outcome': outcome_name,
            'window': label,
            'post_15min_bins': int(mask.sum()),
            'post_weekdays': int(len(post_dates)),
            'mean_gap_treated_minus_synthetic': float(value),
            'pre_mean_gap': float(pre_gap.mean()),
            'pre_rmspe': float(np.sqrt(np.mean(pre_gap.to_numpy() ** 2))),
            'post_rmspe': float(np.sqrt(np.mean(gap.loc[mask.values].to_numpy() ** 2))),
        }
        row['post_pre_rmspe_ratio'] = row['post_rmspe'] / row['pre_rmspe'] if row['pre_rmspe'] > 0 else np.nan
        if outcome_name == 'mean_zone_log1p_volume':
            row['approximate_percent_change_from_gap'] = float(100.0 * (np.exp(value) - 1.0))
        rows.append(row)
    return rows


def placebo_diagnostics(wide: pd.DataFrame, donor_units: list[int], pre_mask: np.ndarray, post_mask: np.ndarray, outcome_name: str, treated_ratio: float) -> list[dict]:
    """In-space placebos use other eligible donor zones; treatment units are never donors."""
    rows = []
    for pseudo in donor_units:
        other = [z for z in donor_units if z != pseudo]
        y, synth, _, diag = compute_scm_for_target(wide, [pseudo], other, pre_mask)
        gap = y - synth
        pre_rmspe = float(np.sqrt(np.mean(gap.loc[pre_mask].to_numpy() ** 2)))
        post_rmspe = float(np.sqrt(np.mean(gap.loc[post_mask].to_numpy() ** 2)))
        ratio = post_rmspe / pre_rmspe if pre_rmspe > 0 else np.nan
        rows.append({
            'outcome': outcome_name,
            'pseudo_treated_zone': int(pseudo),
            'pre_rmspe': pre_rmspe,
            'post_rmspe': post_rmspe,
            'post_pre_rmspe_ratio': ratio,
            'effective_donor_count': diag['effective_donor_count'],
            'ratio_at_least_as_large_as_actual': bool(ratio >= treated_ratio) if np.isfinite(ratio) else False,
        })
    return rows


def temporal_placebo_and_leave_one_out(
    times: pd.DatetimeIndex, wide: pd.DataFrame, treatment_outcome: pd.Series, donors: list[int], outcome_name: str
) -> tuple[dict, list[dict]]:
    """Run a pre-collapse pseudo-event and a one-donor-deleted sensitivity without reusing post data for fitting."""
    pseudo_pre = np.asarray(times < PSEUDO_EVENT, dtype=bool)
    pseudo_post = np.asarray((times >= PSEUDO_POST_START) & (times <= PSEUDO_POST_END), dtype=bool)
    pseudo_y, pseudo_synthetic, _, pseudo_diag = compute_scm_for_target_series(wide, treatment_outcome, donors, pseudo_pre)
    pseudo_gap = pseudo_y - pseudo_synthetic
    pseudo_pre_rmspe = float(np.sqrt(np.mean(pseudo_gap.loc[pseudo_pre].to_numpy() ** 2)))
    pseudo_post_rmspe = float(np.sqrt(np.mean(pseudo_gap.loc[pseudo_post].to_numpy() ** 2)))
    temporal = {
        'outcome': outcome_name,
        'pseudo_event_date': str(PSEUDO_EVENT.date()),
        'pre_15min_bins': int(pseudo_pre.sum()),
        'pseudo_post_15min_bins': int(pseudo_post.sum()),
        'mean_pseudo_post_gap_treated_minus_synthetic': float(pseudo_gap.loc[pseudo_post].mean()),
        'pseudo_pre_rmspe': pseudo_pre_rmspe,
        'pseudo_post_rmspe': pseudo_post_rmspe,
        'pseudo_post_pre_rmspe_ratio': pseudo_post_rmspe / pseudo_pre_rmspe if pseudo_pre_rmspe > 0 else np.nan,
        'effective_donor_count': pseudo_diag['effective_donor_count'],
    }
    actual_pre = np.asarray(times < EVENT_DATE, dtype=bool)
    actual_post = np.asarray((times >= POST_START) & (times <= POST_END), dtype=bool)
    loo_rows = []
    for excluded in donors:
        donor_subset = [z for z in donors if z != excluded]
        y, synth, _, _ = compute_scm_for_target_series(wide, treatment_outcome, donor_subset, actual_pre)
        gap = y - synth
        loo_rows.append({
            'outcome': outcome_name,
            'excluded_donor_zone': int(excluded),
            'full_20_weekday_mean_gap_treated_minus_synthetic': float(gap.loc[actual_post].mean()),
            'pre_rmspe': float(np.sqrt(np.mean(gap.loc[actual_pre].to_numpy() ** 2))),
            'post_pre_rmspe_ratio': float(np.sqrt(np.mean(gap.loc[actual_post].to_numpy() ** 2)) / np.sqrt(np.mean(gap.loc[actual_pre].to_numpy() ** 2))),
        })
    return temporal, loo_rows


def plot_results(ts: pd.DataFrame, placebo: pd.DataFrame, estimates: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    labels = {'speed_mph': 'Mean zone speed (mph)', 'mean_zone_log1p_volume': 'Mean zone log(1 + 15-min volume)'}
    for row_i, outcome in enumerate(OUTCOMES):
        d = ts.loc[ts['outcome'].eq(outcome)].copy()
        ax = axes[row_i, 0]
        ax.plot(d['time_bin'], d['treated'], color='#132A45', lw=1.3, label='Treated corridor')
        ax.plot(d['time_bin'], d['synthetic'], color='#A04B00', lw=1.3, ls='--', label='Synthetic control')
        ax.axvline(EVENT_DATE, color='black', lw=1, ls=':')
        ax.set_title(f'{labels[outcome]}: observed versus synthetic')
        ax.set_ylabel(labels[outcome])
        ax.legend(frameon=False, loc='best')
        ax.grid(axis='y', alpha=0.25)

        ax = axes[row_i, 1]
        p = placebo.loc[placebo['outcome'].eq(outcome)].copy()
        actual = estimates.loc[(estimates['outcome'].eq(outcome)) & (estimates['window'].eq('full_20_weekdays')), 'post_pre_rmspe_ratio'].iloc[0]
        ax.hist(p['post_pre_rmspe_ratio'].dropna(), bins=15, color='#8FA7BF', edgecolor='white')
        ax.axvline(actual, color='#A04B00', lw=2, label=f'Actual ratio: {actual:.2f}')
        p_value = (1 + int((p['post_pre_rmspe_ratio'] >= actual).sum())) / (1 + len(p))
        ax.set_title(f'{labels[outcome]}: in-space placebo RMSPE ratios (p={p_value:.3f})')
        ax.set_xlabel('Post/pre RMSPE ratio')
        ax.set_ylabel('Donor-zone placebos')
        ax.legend(frameon=False)
        ax.grid(axis='y', alpha=0.25)
    fig.suptitle('Key Bridge corridor synthetic-control diagnostics', fontsize=15, fontweight='bold')
    fig.savefig(OUT / 'fig_true_synthetic_control_2024.png', dpi=220, bbox_inches='tight')
    plt.close(fig)


def main() -> None:
    frame = pd.read_parquet(INPUT)
    frame['time_bin'] = pd.to_datetime(frame['time_bin'])
    # Exclude weekend rows from the existing weekday-design panel defensively.
    frame = frame.loc[frame['time_bin'].dt.dayofweek < 5].copy()
    all_estimates, all_ts, all_weights, all_placebos, audit_outcomes = [], [], [], [], {}
    temporal_placebos, leave_one_out_rows = [], []

    for output_name, source_col in OUTCOMES.items():
        times, wide, treatment_outcome, treated_zones, donors = build_balanced_matrix(frame, source_col)
        n_treated = len(treated_zones)
        pre_mask = np.asarray(times < EVENT_DATE, dtype=bool)
        post_mask = np.asarray((times >= POST_START) & (times <= POST_END), dtype=bool)
        if not pre_mask.any() or not post_mask.any():
            raise ValueError('Required pre/post periods are empty.')
        treated_y, synthetic_y, weights, diag = compute_scm_for_target_series(wide, treatment_outcome, donors, pre_mask)
        gap = treated_y - synthetic_y
        est = period_effects(times, gap, pre_mask, post_mask, output_name)
        actual_ratio = [r for r in est if r['window'] == 'full_20_weekdays'][0]['post_pre_rmspe_ratio']
        placebo_rows = placebo_diagnostics(wide, donors, pre_mask, post_mask, output_name, actual_ratio)
        temporal, loo = temporal_placebo_and_leave_one_out(times, wide, treatment_outcome, donors, output_name)
        temporal_placebos.append(temporal)
        leave_one_out_rows.extend(loo)
        placebo_df = pd.DataFrame(placebo_rows)
        p_value = (1 + int(placebo_df['ratio_at_least_as_large_as_actual'].sum())) / (1 + len(placebo_df))
        for r in est:
            r['in_space_randomization_p_value_full_20_weekday_ratio'] = p_value
            r['n_treatment_zones_fixed_corridor'] = n_treated
            r['n_donor_zones_balanced'] = len(donors)
            r['n_pre_15min_bins'] = int(pre_mask.sum())
            r['n_post_15min_bins_full'] = int(post_mask.sum())
            r['ridge_lambda_for_stability'] = RIDGE_LAMBDA
        all_estimates.extend(est)
        all_placebos.extend(placebo_rows)
        for z, w in zip(donors, weights):
            all_weights.append({'outcome': output_name, 'zone_id': int(z), 'weight': float(w), 'weight_gt_1e_6': bool(w > 1e-6)})
        output_ts = pd.DataFrame({
            'time_bin': times, 'outcome': output_name, 'treated': treated_y.to_numpy(),
            'synthetic': synthetic_y.to_numpy(), 'gap_treated_minus_synthetic': gap.to_numpy(),
            'period': np.where(pre_mask, 'pre', 'post')
        })
        all_ts.append(output_ts)
        audit_outcomes[output_name] = {
            'source_column': source_col,
            'n_treatment_zones_fixed_corridor': n_treated,
            'n_donor_zones_balanced': len(donors),
            'treatment_zone_ids': treated_zones,
            'donor_zone_ids': donors,
            'n_pre_15min_bins': int(pre_mask.sum()),
            'n_post_15min_bins': int(post_mask.sum()),
            'dropped_treatment_outcome_bins_no_imputation': int(wide.attrs.get('dropped_treatment_outcome_bins_no_imputation', 0)),
            'fit_diagnostics': diag,
            'main_effect_definition': 'mean 15-minute treated-minus-synthetic gap across the named weekday window',
        }

    estimates = pd.DataFrame(all_estimates)
    ts = pd.concat(all_ts, ignore_index=True)
    weights = pd.DataFrame(all_weights)
    placebo = pd.DataFrame(all_placebos)
    estimates.to_csv(OUT / 'true_scm_effect_estimates_2024.csv', index=False)
    ts.to_csv(OUT / 'true_scm_time_series_2024.csv', index=False)
    weights.to_csv(OUT / 'true_scm_donor_weights_2024.csv', index=False)
    placebo.to_csv(OUT / 'true_scm_in_space_placebos_2024.csv', index=False)
    pd.DataFrame(temporal_placebos).to_csv(OUT / 'true_scm_in_time_placebo_2024.csv', index=False)
    pd.DataFrame(leave_one_out_rows).to_csv(OUT / 'true_scm_leave_one_donor_out_2024.csv', index=False)
    plot_results(ts, placebo, estimates)

    audit = {
        'design': 'Conventional synthetic control with simplex-constrained nonnegative donor weights summing to one; weights fitted only on pre-collapse 15-minute outcomes.',
        'event': 'Francis Scott Key Bridge collapse, 2024-03-26; event date excluded; post begins 2024-03-27.',
        'treatment_outcome': 'Equally weighted mean of balanced detector zones within the pre-specified I-95/I-895 geographic treatment corridor.',
        'donor_pool': 'External Maryland Interstate detector zones 30–100 km from Key Bridge, excluding I-95, I-895, I-695, and the pre-specified I-83/I-795 comparison corridor; complete detector coverage and median pre-volume thresholds are enforced.',
        'no_outcome_imputation': True,
        'uncertainty': 'Two-sided model uncertainty is assessed with in-space donor-zone randomization inference using post/pre RMSPE ratios. It is not a repeated-sampling confidence interval. A pre-collapse pseudo-event and leave-one-donor-out checks are reported as diagnostic robustness analyses.',
        'temporal_placebo_event': str(PSEUDO_EVENT.date()),
        'outcomes': audit_outcomes,
    }
    (OUT / 'true_scm_analysis_audit_2024.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps({'estimates': estimates.to_dict(orient='records'), 'audit': audit}, indent=2))


if __name__ == '__main__':
    main()

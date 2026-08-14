#!/usr/bin/env python3
"""Create manuscript-readable daily summaries from the executed detector–CHART analyses."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

OUT = Path('/home/ubuntu/transport_portfolio/network_shock_observatory/outputs')
EVENT = pd.Timestamp('2024-03-26')


def main() -> None:
    ts = pd.read_csv(OUT / 'true_scm_time_series_2024.csv', parse_dates=['time_bin'])
    ts['date'] = ts['time_bin'].dt.normalize()
    daily = ts.groupby(['outcome', 'date'], observed=True).agg(
        treated=('treated', 'mean'), synthetic=('synthetic', 'mean'), gap=('gap_treated_minus_synthetic', 'mean')
    ).reset_index()
    daily.to_csv(OUT / 'true_scm_daily_summary_2024.csv', index=False)

    labels = {
        'speed_mph': ('Daily mean speed (mph)', 'Daily treated − synthetic speed gap (mph)'),
        'mean_zone_log1p_volume': ('Daily mean zone log(1 + 15-min volume)', 'Daily treated − synthetic log-volume gap'),
    }
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex='col', constrained_layout=True)
    for row, outcome in enumerate(['speed_mph', 'mean_zone_log1p_volume']):
        d = daily.loc[daily['outcome'].eq(outcome)].copy()
        ylabel, gaplabel = labels[outcome]
        ax = axes[row, 0]
        ax.plot(d['date'], d['treated'], color='#132A45', lw=2, marker='o', ms=2.4, label='Treated corridor')
        ax.plot(d['date'], d['synthetic'], color='#A04B00', lw=2, ls='--', label='Synthetic control')
        ax.axvline(EVENT, color='black', ls=':', lw=1)
        ax.set_title(ylabel)
        ax.set_ylabel(ylabel)
        ax.legend(frameon=False, fontsize=8)
        ax.grid(axis='y', alpha=0.25)

        ax = axes[row, 1]
        ax.plot(d['date'], d['gap'], color='#5A2A0A', lw=1.8, marker='o', ms=2.3)
        ax.axhline(0, color='black', lw=0.8)
        ax.axvline(EVENT, color='black', ls=':', lw=1)
        ax.set_title(gaplabel)
        ax.set_ylabel(gaplabel)
        ax.grid(axis='y', alpha=0.25)
    fig.suptitle('Key Bridge corridor detector outcomes: daily aggregation of 15-minute SCM series', fontsize=14, fontweight='bold')
    fig.savefig(OUT / 'fig_true_scm_daily_effects_2024.png', dpi=220, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()

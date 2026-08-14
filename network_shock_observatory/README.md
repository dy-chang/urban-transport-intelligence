# Network Shock Observatory: Key Bridge Detector–CHART Analysis

This module evaluates traffic operations on the official I-95/I-895 cross-harbor diversion approaches after the 26 March 2024 Francis Scott Key Bridge collapse. It is a **reproducible research package**, not a public release of proprietary detector records.

## What the executed analysis finds

A 2024 pre-event-fitted conventional synthetic control estimates a mean **−5.43 mph** speed gap between the I-95/I-895 treatment corridor and its synthetic counterfactual over the first 20 post-event weekdays. The in-space donor-placebo p-value is **0.125** with seven complete speed donors, so the result is reported as **bounded evidence of operational deterioration**, not as point-identified causal proof. The companion log-volume effect is +0.080 (approximately +8.34%) but has a donor-placebo p-value of 0.818 and is not treated as a robust volume finding.

The full methods, diagnostics, CHART sensitivity analyses, and interpretation limits are in [`docs/key_bridge_detector_chart_executed_analysis_2024.md`](docs/key_bridge_detector_chart_executed_analysis_2024.md).

## Data provenance and public-release boundary

| Data source | Supplied coverage | Role | Versioned here? |
| --- | --- | --- | --- |
| Maryland INRIX/MDOT detector panel | 2022–2024, 5-minute lane/zone records | Primary speed and volume outcomes | **No.** Proprietary/controlled raw data and derived time panels are ignored. |
| MDOT CHART incident log | 2020–2024 annual CSVs | Route-segment operational context and sensitivity analyses | Raw copies are not included; compact derived audit results are versioned. |

The published repository includes source code, documentation, compact estimates, metadata, figures, and validation audits. It excludes raw detector files, local CHART copies, and large zone–time panels. Users with authorized inputs can recreate all derived outputs.

## Study design

The pre-specified treatment corridor contains 36 detector zones on I-95/I-895 within the Baltimore cross-harbor diversion approach. The I-83/I-795 corridor has 21 zones and is used for an incident-context pair-gap sensitivity analysis. The primary SCM donor pool comprises external Interstate zones 30–100 km from Key Bridge; I-95, I-895, I-695, and I-83/I-795 are excluded.

The primary estimator has nonnegative, sum-to-one donor weights fitted only to pre-collapse 15-minute outcomes. Speed uses a volume-weighted fixed-corridor treatment outcome; volume uses mean zone-level `log(1 + 15-minute volume)`. The event date is excluded, weekdays are retained, and no detector outcome is imputed.

> **CHART caveat:** Incident logs are matched conservatively to route-segment context from primary-road location text; they are not event-to-detector-zone joins. Post-event incidents can be mediators of the bridge-collapse disruption. Accordingly, CHART is excluded from the primary total-effect SCM and used only in descriptive and explicitly conditioned sensitivity analyses.

## Reproduction

Place the authorized annual detector Parquet files and annual CHART CSV files in the local paths documented in the scripts. Then run:

```bash
cd network_shock_observatory
python3 src/build_detector_chart_panel.py
python3 src/estimate_true_synthetic_control.py
python3 src/analyze_chart_sensitivity_and_context.py
python3 src/make_detector_chart_summary_figures.py
```

The input and quality-control record is written to `outputs/detector_chart_panel_quality_audit.json`. The core executed results are written to `outputs/true_scm_effect_estimates_2024.csv`.

## Key artifacts

| Artifact | Description |
| --- | --- |
| `configs/key_bridge_corridor_design.yaml` | Pre-specified event window, corridor definitions, and original DiD configuration. |
| `src/build_detector_chart_panel.py` | Detector–CHART construction, conservative CHART match, donor screen, and acute-context handling. |
| `src/estimate_true_synthetic_control.py` | Conventional SCM, in-space/in-time placebos, and leave-one-donor-out diagnostics. |
| `src/analyze_chart_sensitivity_and_context.py` | Acute CHART sensitivity, pair-gap model, and same-calendar descriptive event comparison. |
| `docs/key_bridge_detector_chart_executed_analysis_2024.md` | Executed analytical report with supported conclusions and limitations. |
| `outputs/fig_true_scm_daily_effects_2024.png` | Manuscript-readable daily aggregation of the 15-minute SCM series. |
| `outputs/fig_chart_operational_context_2024.png` | Descriptive CHART acute operating context. |

## Interpretation limits

This module does not identify individual rerouting, travel-time reliability for individual trips, a crash/safety effect, or a network-wide welfare effect. It also does not claim a weather-adjusted, spatial-lag, augmented synthetic-control, or synthetic-difference-in-differences result because those estimators/covariates are not part of the executed code. The existing same-weekday DiD/event-study output is retained as a separate supplementary analysis and carries its documented pre-trend warning.

## References

Abadie, A., Diamond, A., and Hainmueller, J. (2010). “Synthetic Control Methods for Comparative Case Studies: Estimating the Effect of California’s Tobacco Control Program.” *Journal of the American Statistical Association*, 105(490), 493–505. [https://doi.org/10.1198/jasa.2009.ap08746](https://doi.org/10.1198/jasa.2009.ap08746)

Abadie, A. (2021). “Using Synthetic Controls: Feasibility, Data Requirements, and Methodological Aspects.” *Journal of Economic Literature*, 59(2), 391–425. [https://doi.org/10.1257/jel.20191450](https://doi.org/10.1257/jel.20191450)

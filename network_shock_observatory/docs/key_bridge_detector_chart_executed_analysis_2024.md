# Executed Analysis Report: Key Bridge Corridor Operations

**Study version:** 13 August 2026

**Author:** Manus AI
**Scope:** Maryland detector panel and MDOT CHART incident log only

## Executive finding

This execution finds a **large and temporally specific deterioration in detector-measured speed** on the pre-specified I-95/I-895 cross-harbor diversion corridor after the 26 March 2024 Key Bridge collapse. A genuine, simplex-constrained synthetic control fitted only to pre-event 15-minute detector outcomes estimates a **−5.43 mph** mean treated-minus-synthetic speed gap over the first 20 post-event weekdays. The corresponding in-space placebo randomization p-value is **0.125** because none of seven donor-zone placebos has a post/pre RMSPE ratio as large as the treated series, but the small donor count limits the attainable p-value. The detector volume signal is weaker: its 20-weekday log-volume gap is **+0.080**, approximately **+8.34%**, with an in-space placebo p-value of **0.818**.

> The defensible conclusion is operational, not absolute causal proof: the detector evidence is consistent with a material post-collapse speed deterioration on the official diversion approaches, robust to the executed CHART acute-context restriction and donor leave-one-out tests. It does **not** establish individual rerouting, network-wide causal effects, or a safety effect.

![Daily detector SCM results](../outputs/fig_true_scm_daily_effects_2024.png)

## 1. Data actually used

| Component | Executed specification | Quality and interpretation boundary |
| --- | --- | --- |
| Detector outcomes | Maryland INRIX/MDOT detector panel aggregated to 15-minute bins, weekdays 05:00–21:45, 12 February–23 April 2024. | Outcomes are speed, volume, occupancy, and data-quality fields. No detector outcome was imputed. |
| Treatment corridor | 36 I-95/I-895 detector zones in the pre-specified Baltimore geographic box. | The definition follows the study configuration, not post-event detector behavior. |
| Comparison corridor | 21 I-83/I-795 detector zones in a spatially separated Baltimore-area box. | Used for CHART-conditioned pair-gap sensitivity and descriptive context; not included in the primary external donor pool. |
| Synthetic-control donor candidates | 71 external Interstate zones, 30–100 km from Key Bridge, excluding I-95, I-895, I-695, and the comparison corridor; 90% pre-speed coverage and median pre-volume ≥20 required. | Complete-coverage rules reduce the balanced pool to 7 speed donors and 10 log-volume donors. This is a material inference limitation. |
| MDOT CHART | Event-level start/close time, standardized type, location text, and maximum lanes closed. | CHART was conservatively classified to **route-segment context**, not to individual detector zones. I-95/I-83 require a Baltimore segment exit/milepost/landmark match; I-895/I-795 require primary-road matching. |

The prepared detector panel contains 1,333,065 weekday zone–time rows and 433 zones. It provides 3,524 observed global 15-minute bins against 3,536 declared weekday 05:00–21:45 bins; the 12 missing global bins were retained as a data-quality finding and were not filled. The actual speed SCM uses 2,099 pre-event bins and 1,355 post-event bins after dropping two treatment-corridor bins without a valid aggregate speed denominator. The event date itself is excluded.

The 2024 CHART file has 106,217 records. Conservative location matching retains 3,160 valid-duration events in the 12 February–23 April study window: 2,849 on the I-95/I-895 route context and 311 on the I-83/I-795 route context. These figures are **event-log counts**, not incident rates per vehicle-mile and not detector-zone assignments.

## 2. Estimator and identification boundary

The primary estimator is a real synthetic control, not a comparison-corridor mean gap. For each outcome, donor weights \(w_j\) solve

\[
\min_{w}\;\frac{1}{T_0}\sum_{t\leq T_0}(Y_{Tt}-\sum_j w_jY_{jt})^2+10^{-6}\sum_jw_j^2,
\quad w_j\geq0,\quad\sum_jw_j=1.
\]

Weights are fitted only with the 2024 pre-collapse period. The treated series is a fixed-corridor aggregation of all 36 treatment zones: volume-weighted speed for speed, and the mean zone-level \(\log(1+\text{15-minute volume})\) for volume. The tiny ridge term resolves otherwise arbitrary splitting between nearly collinear donors while preserving the conventional nonnegative, sum-to-one synthetic-control geometry. Synthetic-control methods require that the donor-weighted counterfactual is credible in the absence of the shock; they do not remove the need to examine pre-fit and donor-placebo diagnostics [1]–[3].

Uncertainty is reported using **in-space donor-zone randomization inference**: each balanced donor is treated as a pseudo-treated unit, using all other donors to form its synthetic comparison. The reported quantity is the post/pre RMSPE ratio. This is not a repeated-sampling confidence interval. A 4 March 2024 in-time pseudo-event and leave-one-donor-out re-estimation are additional diagnostics.

CHART is intentionally excluded from the primary total-effect SCM. A collision, breakdown, incident response, or lane closure recorded after the collapse may be part of the mechanism through which the collapse affected traffic. Conditioning on it can block part of the very effect of interest. CHART is therefore used for descriptive operating context and explicitly labelled sensitivity analyses only.

## 3. Primary detector synthetic-control results

| Outcome | Post window | Mean treated − synthetic gap | Pre RMSPE | Post/pre RMSPE ratio | In-space p-value | Interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Speed | First 5 weekdays | −5.14 mph | 2.81 mph | 2.61 | 0.125 | Immediate speed deterioration. |
| Speed | First 10 weekdays | −5.45 mph | 2.81 mph | 2.79 | 0.125 | Similar magnitude through two weeks. |
| **Speed** | **First 20 weekdays** | **−5.43 mph** | **2.81 mph** | **2.79** | **0.125** | Strong operational signal; bounded by small donor pool and nonzero pre-fit error. |
| Log volume | First 5 weekdays | +0.057 log points (+5.83%) | 0.226 | 0.93 | 0.818 | No unusual post-shock RMSPE inflation. |
| Log volume | First 10 weekdays | +0.059 log points (+6.13%) | 0.226 | 1.08 | 0.818 | Weak relative to donor placebo distribution. |
| **Log volume** | **First 20 weekdays** | **+0.080 log points (+8.34%)** | **0.226** | **1.09** | **0.818** | Directionally positive but not distinguishable from donor-placebo variation. |

The speed pseudo-event result is comparatively small: for a 4 March pseudo-event, the mean pseudo-post speed gap is **+0.19 mph** and the RMSPE ratio is **1.07**, versus **−5.43 mph** and **2.79** after the real event. For log volume, the pseudo gap is +0.040 and the pseudo RMSPE ratio is 1.09, close to the real-event ratio of 1.09. Leave-one-donor-out speed estimates range only from **−5.58 to −5.24 mph**, whereas log-volume estimates range from **−0.028 to +0.128 log points**. These results further separate a stable speed finding from an uncertain volume finding.

The interpretation must remain calibrated. The speed in-space result is unusual relative to the seven available speed donor placebos, but a conventional p-value below 0.05 cannot be achieved with seven placebos under this randomization calculation. In addition, the 2.81-mph pre-period RMSPE means the counterfactual does not perfectly track the treated corridor. The paper should say that the detector evidence **supports a substantial speed deterioration consistent with the network shock**, not that it proves a precisely identified causal effect.

## 4. MDOT CHART operational-context analysis

The original all-duration severe-event definition was unsuitable for a 15-minute sensitivity restriction because the supplied CHART data include planned-roadway-closure records that span months. For example, multiple road-maintenance events begin in February or March and remain open through June or later. Treating them as an acute active incident makes every treatment-route detector bin “severe,” which is a data-definition artifact rather than a valid sensitivity sample.

Accordingly, an **acute severe context** is defined as roadwork/construction/maintenance or a reported lane closure with valid duration **≤24 hours**. Long-duration CHART records remain in the event inventory but are not interpreted as active acute incident exposure. This choice is transparent, mechanically reproducible, and should be presented as a sensitivity rule rather than an external ground truth.

| CHART-informed analysis | Speed result | Volume result | Correct interpretation |
| --- | ---: | ---: | --- |
| Acute-context restricted SCM | −4.58 mph; 1,285 pre and 721 post bins retained; 634 post bins removed | +0.102 log points (+10.72%) | Speed deterioration persists after excluding matched acute-severe treatment-route bins. This is a **conditioned estimand**, not the total collapse effect. |
| Pair-gap model, no CHART terms | −4.83 mph; 250 day-block bootstrap interval [−5.45, −4.24] | −0.056 log points; [−0.126, +0.030] | Detector difference between treatment and I-83/I-795 after weekday×time-of-day adjustment. |
| Pair-gap model, CHART-conditioned | −4.67 mph; [−5.41, −3.95] | −0.071 log points; [−0.150, +0.028] | Conditional association after adjusting route-context differences in acute severity, collisions, disabled vehicles, and reported closed lanes. **Do not call this a causal controlled effect.** |

The CHART-conditioned speed coefficient differs from the unadjusted pair-gap coefficient by only 0.16 mph. This pattern is consistent with, but does not prove, a speed deterioration that is not solely an artifact of the observed acute CHART context differences. The volume coefficients retain intervals spanning zero in both specifications.

![CHART operating context](../outputs/fig_chart_operational_context_2024.png)

A same-calendar descriptive comparison, 27 March–23 April, shows that conservatively matched I-95/I-895 events started at **42.36 per day in 2024**, compared with **37.86 per day in 2023**. Collision starts rise from **5.39 to 7.75 per day**. The I-83/I-795 route context falls from **5.79 to 4.75 events per day**, while its collision starts fall from **0.75 to 0.64 per day**. These are not safety effects: changed reporting, exposure, network conditions, and the post-collapse response may all contribute.

## 5. What can and cannot be claimed

| Claim | Status | Reason |
| --- | --- | --- |
| The pre-specified I-95/I-895 corridor experienced lower detector speeds relative to a pre-event synthetic counterfactual after the collapse. | **Supported, with bounded inference.** | −5.43 mph full-post SCM gap; speed placebo ratio exceeds all seven donor placebo ratios; pseudo-event and leave-one-out checks are compatible with the finding. |
| The collapse caused exactly a 5.43-mph speed loss everywhere on the diversion corridor. | **Not supported.** | Imperfect pre-fit, small complete donor pool, possible spillovers/unmeasured common shocks, and corridor aggregation prevent this precision claim. |
| Traffic volume causally increased. | **Not supported.** | Positive point estimate but volume placebo p=0.818; leave-one-out results are unstable in sign and magnitude. |
| CHART incidents explain away the speed result. | **Not supported.** | Acute-context restriction and conditional pair-gap model retain a similar negative speed gap. |
| CHART controls establish an incident-adjusted causal total effect. | **Not supported.** | Post-event incidents can be mediators; their text-derived route context is not a detector-zone causal exposure. |
| The event increased crashes or reduced safety. | **Not evaluated.** | CHART incident logs are not a complete crash-outcome dataset, and 2024 crash-report data were not used. |

## 6. Reproducibility and deliverables

Run the following scripts from `network_shock_observatory` after the immutable annual detector panels and annual CHART CSVs have been placed in the documented local locations.

```bash
python3 src/build_detector_chart_panel.py
python3 src/estimate_true_synthetic_control.py
python3 src/analyze_chart_sensitivity_and_context.py
python3 src/make_detector_chart_summary_figures.py
```

| Artifact | Purpose |
| --- | --- |
| `src/build_detector_chart_panel.py` | Conservative route-text CHART match, 15-minute active-event burdens, detector quality audit, donor screening. |
| `src/estimate_true_synthetic_control.py` | Actual simplex SCM weights, treatment/synthetic series, in-space placebo, in-time placebo, leave-one-out results. |
| `src/analyze_chart_sensitivity_and_context.py` | Acute CHART-context restriction, pair-gap sensitivity, day-block uncertainty summary, seasonal CHART descriptives. |
| `outputs/detector_chart_panel_quality_audit.json` | Full sample, matching, missing-bin, long-duration record, and data-boundary audit. |
| `outputs/true_scm_effect_estimates_2024.csv` | Main detector results. |
| `outputs/true_scm_in_space_placebos_2024.csv` | Randomization diagnostic. |
| `outputs/chart_sensitive_scm_results_2024.csv` | Acute CHART-context SCM sensitivity. |
| `outputs/chart_conditioned_pair_gap_models_2024.csv` | Conditional pair-gap sensitivity results. |
| `outputs/chart_same_calendar_seasonal_descriptives_2023_2024.csv` | Descriptive same-calendar CHART comparison. |

## 7. Required manuscript wording

The empirical paper should describe the primary result as follows:

> “A pre-event-fitted, nonnegative synthetic control indicates that the official I-95/I-895 diversion approaches operated 5.43 mph below their synthetic counterfactual over the first 20 post-collapse weekdays. The treated post/pre RMSPE ratio exceeded those of all seven balanced donor-zone placebos; nevertheless, the corresponding finite-placebo randomization p-value was 0.125 and pre-event RMSPE was 2.81 mph. We therefore interpret the finding as evidence of a substantial, but not point-identified, deterioration in corridor operations.”

The CHART paragraph should state:

> “Incident-management records were used to characterize contemporaneous route-segment operating context and for prespecified sensitivity analyses, not as automatic main-model controls. Because post-collapse incidents and lane closures may be mediators of the disruption, CHART-conditioned estimates are interpreted as conditional associations rather than the total causal effect.”

## References

[1] Abadie, A., Diamond, A., and Hainmueller, J. (2010). “Synthetic Control Methods for Comparative Case Studies: Estimating the Effect of California’s Tobacco Control Program.” *Journal of the American Statistical Association*, 105(490), 493–505. [https://doi.org/10.1198/jasa.2009.ap08746](https://doi.org/10.1198/jasa.2009.ap08746)

[2] Abadie, A., Diamond, A., and Hainmueller, J. (2015). “Comparative Politics and the Synthetic Control Method.” *American Journal of Political Science*, 59(2), 495–510. [https://doi.org/10.1111/ajps.12116](https://doi.org/10.1111/ajps.12116)

[3] Abadie, A. (2021). “Using Synthetic Controls: Feasibility, Data Requirements, and Methodological Aspects.” *Journal of Economic Literature*, 59(2), 391–425. [https://doi.org/10.1257/jel.20191450](https://doi.org/10.1257/jel.20191450)

# Visual QA Notes — Key Bridge Detector–CHART Analysis

## Reviewed figures

| Figure | QA result | Interpretation and action |
| --- | --- | --- |
| `fig_true_synthetic_control_2024.png` | Axis labels, event marker, observed/synthetic legend, and placebo-ratio annotations render correctly. | The 15-minute trace is intentionally dense and shows pronounced intraday variation. It is a diagnostic plot rather than the preferred manuscript main figure. A daily-aggregated gap plot should be generated for the manuscript to improve readability while retaining the full 15-minute series as an appendix diagnostic. |
| `fig_chart_operational_context_2024.png` | Acute-event definition is visibly labelled; treatment/control labels, event marker, same-calendar event-rate bars, axes, and legend all render correctly. | The figure supports descriptive operational-context interpretation only. It must retain the caption statement that it is not a causal adjustment because CHART post-event incidents may be mediators and are route-segment text matches rather than detector-zone exposures. |

## Key visual findings

The detector diagnostic clearly separates a modest pre-event speed discrepancy from a markedly larger post-event treated-minus-synthetic gap. The placebo histogram places the speed RMSPE ratio beyond all seven donor-zone ratios, but the donor pool is small and the randomization p-value is therefore reported as 0.125 rather than overstated as conventional significance.

The CHART figure shows that treatment-route acute severe-context exposure was substantially more frequent than in the I-83/I-795 comparison route context both before and after the event. Therefore, CHART variables are retained as contextual and sensitivity measures, not as automatic main-model controls.

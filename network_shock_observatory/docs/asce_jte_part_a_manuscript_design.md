# ASCE JTE Part A Manuscript Design Memo

## Target article

**Working title:** *Traffic Operations after a Bridge-Collapse Network Shock: Detector-Based Synthetic-Control Evidence from the Francis Scott Key Bridge Closure*

**Target journal:** *Journal of Transportation Engineering, Part A: Systems* (ASCE)

**Article type:** Technical Paper. The topic matches the journal's stated interests in traffic-management technology and road/bridge management. The manuscript will follow the ASCE technical-paper order: title page, abstract, optional Practical Applications, unnumbered word-heading sections, conclusion, data availability, acknowledgments/disclaimer, and author–date references. The final submission should use ASCE's current Word or Overleaf template, double-spaced single column, with separately uploaded figures and continuous line numbering.

## Narrative design

| Section | Central purpose | Evidence permitted in the draft | Prohibited / avoided claim |
| --- | --- | --- | --- |
| Introduction | Establish an unplanned network shock and the need for operational evidence. | Official MDOT detour advice, NTSB incident account, and executed detector findings. | Bridge-design, vessel-causation, safety, or economic-loss claims beyond cited official sources. |
| Literature Review | Position study next to I-35W disruption evidence and credible comparative event-study practice. | Zhu et al. (2010); Abadie et al. (2010, 2015); Abadie (2021); Callaway and Sant’Anna (2021); Sun and Abraham (2021). | Claim that a staggered-adoption DiD estimator was executed. |
| Data | Describe detector outcomes, treatment geography, donor screen, and CHART context. | Verified counts, time windows, route-text matching and long-duration event audit. | Individual trip, origin–destination, crash, weather, or detector-zone-specific incident assignment. |
| Methodology | State primary conventional SCM and diagnostic/sensitivity layers. | Simplex donor weights fitted pre-event; in-space/in-time placebo; leave-one-out; acute CHART conditioning. | ASCM/SDID, spatial lag, weather control, formal causal mediation, or confidence intervals for SCM randomization inference. |
| Results and Discussion | Report speed evidence, qualified volume result, and operational context. | Full executed estimates, plot, CHART same-calendar descriptive comparison. | “Statistically significant at 5%,” universal 5.43-mph causal effect, CHART-adjusted total effect, or crash effect. |
| Conclusion | Set transferable DOT/MPO practice implications and limits. | Corridor monitoring, CHART duration audit, fast operational screening. | Networkwide welfare, individual behavior, safety, or policy-effect claims. |

## Tables and figures

| Item | Content | Main-text role |
| --- | --- | --- |
| Table 1 | Sources, temporal support, spatial units, and analytical role | Makes two-source design transparent. |
| Table 2 | Treatment, comparison, donor-pool screening and retained units | Makes counterfactual construction auditable. |
| Table 3 | SCM effects over 5/10/20 post-event weekdays, RMSPE, placebo p-values | Primary numerical finding. |
| Table 4 | In-time placebo, leave-one-out range, acute-CHART restriction, pair-gap sensitivity | Bounded robustness evidence. |
| Figure 1 | Daily treated and synthetic speed/log-volume series plus gaps | Main operational result. |
| Figure 2 | Acute CHART route context and same-calendar event-rate comparison | Context/mechanism, expressly non-causal. |

## Required language controls

1. Use **“estimated treated-minus-synthetic gap”**, **“operational deterioration consistent with the network shock”**, and **“bounded evidence”** for the primary speed result.
2. Report the finite-placebo randomization p-value of 0.125; do not describe it as conventionally significant.
3. Describe the log-volume result as directionally positive but not unusual relative to donor placebos.
4. State that post-event CHART incidents can be mediators, so CHART-conditioned models change the estimand and are not the main total-effect model.
5. Use author–year ASCE citation syntax in the manuscript. The Markdown deliverable will retain linked reference-style source URLs as an electronic drafting aid; before submission, convert links and bibliography typography into the current ASCE template.

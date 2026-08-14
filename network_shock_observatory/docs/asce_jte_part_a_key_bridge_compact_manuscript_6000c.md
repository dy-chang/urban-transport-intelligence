# Traffic Operations after the Key Bridge Collapse: Detector-Based Synthetic-Control Evidence

**Daeyeol Chang**

*Affiliation, ORCID, and corresponding-author email to be inserted.*

## Abstract

The March 26, 2024, Francis Scott Key Bridge collapse removed an Interstate 695 harbor crossing and redirected traffic toward Baltimore tunnel approaches. This study evaluates short-run operations on the officially advised I-95/I-895 diversion corridor using 15-min Maryland detector data and MDOT CHART incident records. A conventional synthetic control was fitted only to pre-collapse outcomes for 36 treatment zones. During the first 20 post-collapse weekdays, treatment-corridor speed was 8.74 km/h (5.43 mph) below its synthetic counterfactual. The treated post/pre RMSPE ratio exceeded all seven speed-donor placebos, but the finite-placebo p-value was 0.125 and pre-event fit was imperfect. The corresponding log-volume gap was +0.080 (approximately +8.34%) but was not unusual relative to donor placebos (p = 0.818). CHART records are used as route-segment context and sensitivity evidence, not automatic main-model controls, because post-collapse incidents may be mediators. The results provide bounded evidence of substantial speed deterioration on the diversion approaches.

**Keywords:** transportation resilience; traffic operations; bridge collapse; synthetic control; detector data; incident management

## Practical Applications

This study provides an auditable workflow for agencies after an unplanned link loss. Agencies can define treatment corridors from official detour guidance, use high-frequency detector data as operational outcomes, fit a counterfactual before the event, and use incident logs to describe contemporaneous context. For the Key Bridge disruption, the I-95/I-895 approaches operated 8.74 km/h below the fitted counterfactual over the first 20 weekdays. This evidence is suitable for detour management, traveler-information review, and operational after-action assessment; it is not a networkwide welfare, individual-rerouting, or safety estimate. A duration audit is essential when incident files contain multi-month planned-roadway closures. This study retains such records in the event inventory but defines acute context using valid events lasting 24 h or less.

## Introduction

At approximately 1:29 a.m. on March 26, 2024, the containership *Dali* struck a pier supporting the Francis Scott Key Bridge, causing collapse of a substantial portion of the I-695 bridge (NTSB 2025). Maryland’s immediate advisory directed north–south traffic to the I-95 Fort McHenry Tunnel or I-895 Baltimore Harbor Tunnel (MDOT SHA 2024). The event offers a rare opportunity to assess an agency-identified diversion corridor without selecting locations after observed congestion.

## Literature Review

Bridge failures disrupt route and travel decisions while networks re-equilibrate. Zhu et al. (2010) combined detector, transit, and survey evidence after the I-35W collapse; Chang and Nojima (2001) demonstrated the value of system-performance measures after disaster. Synthetic control forms a transparent counterfactual for an exposed aggregate unit, conditional on credible pre-event fit and donor diagnostics (Abadie et al. 2010; Abadie 2021). CHART-conditioned analyses are secondary because post-event incidents may lie on the disruption pathway.

## Data and Methodology

The weekday panel spans February 12–April 23, 2024, 05:00–21:45, and includes 433 detector zones. The treatment corridor contains 36 I-95/I-895 zones. The primary donor candidate pool contains 71 external Interstate zones 30–100 km from Key Bridge, excluding I-95, I-895, I-695, and the I-83/I-795 comparison corridor. Complete common support retains seven speed donors and 10 log-volume donors. No detector value was imputed.

For treatment outcome \(Y_{Tt}\) and donor outcomes \(Y_{jt}\), nonnegative weights are fit only before the collapse:

\[
\min_w\;T_0^{-1}\sum_{t\leq T_0}(Y_{Tt}-\sum_j w_jY_{jt})^2+10^{-6}\sum_jw_j^2,\quad w_j\geq0,\;\sum_jw_j=1.
\]

Speed is volume weighted across treatment zones; volume is mean zone-level \(\log(1+\text{volume})\). We report 5-, 10-, and 20-weekday gaps, in-space donor randomization, a March 4 pseudo-event, and donor leave-one-out results. CHART locations are conservatively matched to route context, not detector zones. Acute severe context denotes roadwork or reported lane closure lasting 24 h or less.

## Results and Discussion

Over 20 post-collapse weekdays, speed was 8.74 km/h (5.43 mph) below synthetic control; pre-event RMSPE was 4.52 km/h (2.81 mph), the RMSPE ratio was 2.79, and the finite-placebo p-value was 0.125. The March 4 placebo gap was +0.30 km/h with a ratio of 1.07. Removing one donor at a time yielded speed gaps from −8.99 to −8.43 km/h. Thus, speed evidence is temporally specific and donor-stable but not point-identified causal proof.

The +0.080 log-volume gap (+8.34%) has p = 0.818 and is not a robust volume finding. Excluding treatment bins with acute severe CHART context retains a −7.37-km/h speed gap. An I-95/I-895-minus-I-83/I-795 pair-gap model estimates −7.77 km/h without CHART terms and −7.52 km/h after conditioning on acute context, collisions, disabled vehicles, and closed lanes. The latter is a conditional association, not an incident-adjusted total effect. Conservatively matched treatment-route event starts rose from 37.86/day in the March 27–April 23, 2023, window to 42.36/day in 2024; this descriptive result is not a safety effect.

## Conclusion

Detector evidence supports a material post-collapse speed deterioration on the officially advised I-95/I-895 approaches. The study does not identify individual rerouting, weather-adjusted effects, travel-time reliability, crashes, or networkwide welfare. Its practical contribution is a reproducible detector–incident workflow that preserves the distinction between outcome measurement and post-event operational context.

## Data Availability Statement

Code, configuration, compact outputs, figures, and quality audits are available at https://github.com/dy-chang/urban-transport-intelligence/tree/main/network_shock_observatory. Detector files are controlled and not redistributed; CHART route-context results are reproducible from documented matching rules.

## References

Abadie, A. 2021. “Using synthetic controls: Feasibility, data requirements, and methodological aspects.” *J. Econ. Lit.* 59 (2): 391–425. https://doi.org/10.1257/jel.20191450.

Abadie, A., A. Diamond, and J. Hainmueller. 2010. “Synthetic control methods for comparative case studies.” *J. Am. Stat. Assoc.* 105 (490): 493–505. https://doi.org/10.1198/jasa.2009.ap08746.

Chang, S. E., and N. Nojima. 2001. “Measuring post-disaster transportation system performance.” *Transp. Res. Part A Policy Pract.* 35 (6): 475–494. https://doi.org/10.1016/S0965-8564(00)00003-3.

MDOT SHA. 2024. “Updated traffic alert: Detours in place following collapse of Interstate 695 bridge.” Accessed August 14, 2026. https://roads.maryland.gov/mdotsha/pages/pressreleasedetails.aspx?newsId=4983&PageId=818.

NTSB. 2025. “Contact of containership *Dali* with Francis Scott Key Bridge and subsequent bridge collapse.” DCA24MM031. https://www.ntsb.gov/investigations/Pages/DCA24MM031.aspx.

Zhu, S., D. Levinson, H. X. Liu, and K. Harder. 2010. “The traffic and behavioral effects of the I-35W Mississippi River bridge collapse.” *Transp. Res. Part A Policy Pract.* 44 (10): 771–784. https://doi.org/10.1016/j.tra.2010.07.001.

## Tables and Figure Callouts

**Table 1.** Primary 20-weekday SCM results: speed gap = −8.74 km/h (−5.43 mph), pre-RMSPE = 4.52 km/h, RMSPE ratio = 2.79, finite-placebo p = 0.125; log-volume gap = +0.080 (+8.34%), RMSPE ratio = 1.09, p = 0.818.

**Figure 1.** Daily treated and synthetic detector outcomes and gaps.

![Daily detector SCM outcomes](../outputs/fig_true_scm_daily_effects_2024.png)

**Figure 2.** Acute CHART route context and same-calendar descriptive comparison.

![CHART operating context](../outputs/fig_chart_operational_context_2024.png)

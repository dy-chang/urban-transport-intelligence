# SUMO Public-Data Operations Screening — Research Notes

## Intended portfolio use

This module demonstrates a **screening-level microsimulation workflow** for a public transportation agency: acquire public counts, preserve data provenance and quality flags, transform observations into a documented SUMO demand input, compare operational scenarios, and communicate travel-time, queue, reliability, and emission outcomes. It is not presented as a corridor design model or a field-validated signal-timing plan.

## Sources and implementation basis

| Source | Verified use in the workflow | Important boundary |
|---|---|---|
| NYC DOT Automated Traffic Volume Counts | Official, 15-minute automated traffic recorder (ATR) observations. The dataset exposes timestamp components, volume, segment ID, WKT geometry, street context, and direction. | Counts do not cover every day of the year, and the number of observed days can differ by location and year. Use only an explicitly selected, quality-checked time window. |
| OpenStreetMap + SUMO `netconvert` | OSM data can be converted natively to a SUMO network. SUMO documentation recommends reviewing imported network geometry and traffic lights. | OSM topology, lane, speed, and signal attributes require QA before operational or design use. |
| SUMO count-to-demand tools | SUMO supports edge, turn, and OD counts; `routeSampler` can use edge/turn/OD counts and a plausible candidate-route set. | A count-constrained route solution is not unique. Route and turning assumptions must be explicit and sensitivity-tested. |
| SUMO outputs | SUMO emits trip, lane-area detector, queue, and emission outputs that support aggregate performance comparison. | Microsimulation results are conditional on demand, behavior, network, and control assumptions. They do not establish a causal project effect. |

## Selected portfolio scenario

**Scenario:** peak-period signal-operation screening at a representative four-leg urban intersection. The repository uses a compact, open-source SUMO network for a deterministic runnable example while exposing an OSM-to-SUMO importer for a real study-area network. A publicly retrieved NYC DOT ATR count profile determines demand magnitude. Directional balancing and turning proportions are transparent scenario assumptions, not claimed observed turning counts.

The operational comparison is a baseline balanced signal program versus an explicitly documented peak-direction retiming program. The outcome scoreboard will report completed trips, mean travel time, mean delay/stopped time, queue proxy, throughput, CO2, NOx, fuel, and seed-to-seed uncertainty intervals.

## References

[1] [NYC Open Data, *Automated Traffic Volume Counts*](https://data.cityofnewyork.us/Transportation/Automated-Traffic-Volume-Counts/7ym2-wayt)

[2] [NYC DOT, *Data Feeds, Dashboards & Open Data*](https://www.nyc.gov/html/dot/html/about/datafeeds.shtml)

[3] [Eclipse SUMO, *Routes from Observation Points*](https://sumo.dlr.de/docs/Demand/Routes_from_Observation_Points.html)

[4] [Eclipse SUMO, *OpenStreetMap Import*](https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html)

## Visualization QA

The input-audit figure was revised to make the observed mainline ATR movement visually distinct from scaled cross-street assumptions and to use 15-minute labels rather than raw seconds. The scenario-comparison figure clearly shows seed-level scatter, empirical percentile bars, and separate y-scales for time loss, stopped delay, detector queue proxy, and CO2. These figures are appropriate for a screening memorandum when accompanied by the stated model limitations; they must not be presented as field validation or causal impact evidence.

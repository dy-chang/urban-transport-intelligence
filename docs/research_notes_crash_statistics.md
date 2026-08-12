# Advanced Crash Statistics & Visualization Portfolio: Research Notes

## Official public-data source selected

The City of Chicago publishes a `Traffic Crashes - Crashes` dataset on its public Open Data Portal. According to the portal and the Data.gov catalog, it contains information about traffic crashes on Chicago streets that are within the jurisdiction of the Chicago Police Department.[1] The City’s Complete Streets traffic-safety resources state that the crash datasets and locations used by CDOT to analyze crashes are publicly available through the portal.[2]

The City also publishes complementary People and Vehicles tables. The People table contains person-level involvement and injury information and can be joined to crash records; the project uses the crash-level table for a directly interpretable model of injury-crash risk.[3]

## Project direction

The proposed module will demonstrate reproducible acquisition from the Socrata Open Data API, rigorous cleaning and feature provenance, logistic regression with odds-ratio confidence intervals, stratified bootstrap uncertainty intervals, calibration and discrimination diagnostics, and publication-quality visualizations. It will document that the analysis identifies statistical associations rather than causal effects.

## References

[1] [City of Chicago Data Portal, *Traffic Crashes – Crashes*](https://data.cityofchicago.org/Transportation/Traffic-Crashes-Crashes/85ca-t3if)

[2] [City of Chicago, *Traffic Safety Data Resources*](https://www.chicago.gov/city/en/sites/complete-streets-chicago/home/traffic-safety/data-resources.html)

[3] [City of Chicago Data Portal, *Traffic Crashes – People*](https://data.cityofchicago.org/Transportation/Traffic-Crashes-People/u6pd-qa9d/about_data)

## Official-source constraints retained in the project

The crash table is daily updated and has citywide coverage from September 2017 onward. It excludes crashes in the city limits where CPD was not the responding police agency, such as many interstate, freeway-ramp, and boundary-road crashes. The City notes that several reported variables, including roadway, weather, and speed-limit attributes, are based on the reporting officer’s best information and may differ from later assessments. The module will therefore use a 2018–2024 completed-period example, preserve `UNKNOWN` categories rather than silently imputing them, and label model coefficients as associations rather than causal effects.[1]

The People table can be linked by `CRASH_RECORD_ID` and contains person-level injury information, but it has a one-to-many relationship to crashes. To avoid treating person records as independent crash observations, the primary inference model will use the crash-level `INJURIES_*` outcome fields. Person-level linkage is documented as an extension rather than included in the main model.[1][3]

The City’s traffic-safety resources publish annual crash reports, monthly fatal-crash summaries, and community-area/ward maps, providing a direct public-agency audience for uncertainty-aware safety analysis and clear geographic communication.[2]

## Visualization QA note

The generated heatmap is readable at report resolution and clearly labels the values as observed injury-crash rates rather than causal effects. The forest plot uses a log odds-ratio scale, displays 95% Wald intervals, and includes an explicit null-association line at 1.0. These conventions will be documented in the README so the project demonstrates uncertainty communication, not only point-estimate ranking.

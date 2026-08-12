# Urban Spatiotemporal Intelligence & Safety Analytics Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-ee4c2c.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Production Ready](https://img.shields.io/badge/Status-Research%20Portfolio-success.svg)]()

> **Author**: Transportation Engineering PhD & Senior Data Scientist  
> **Domain**: Intelligent Transportation Systems (ITS), Spatiotemporal Machine Learning, Causal Econometrics in Transportation Safety  

---

## 1. Executive Summary

This repository presents an end-to-end, production-grade data science and advanced analytics framework tailored for modern **Intelligent Transportation Systems (ITS)** and **Urban Mobility Engineering**. Designed with the rigorous analytical standards of a Transportation Engineering Ph.D., this project integrates large-scale spatial-temporal data processing, graph neural network concepts, gradient boosting benchmarks, and rigorous causal inference methodologies to solve critical urban transportation challenges: traffic congestion prediction and urban traffic safety policy evaluation [1] [2].

By leveraging authoritative open datasets (such as the PeMS highway performance measurement system, NYC TLC trip record data, and urban traffic monitoring sensor networks), this portfolio demonstrates how advanced statistical learning and econometric models can extract actionable insights for urban planners, traffic engineers, and policy makers.

---

## 2. Core Methodological Architecture

The analytical pipeline is structured into three distinct, highly modular pillars:

| Pillar | Focus Domain | Key Methodologies & Libraries | Primary Deliverables |
| :--- | :--- | :--- | :--- |
| **I. Spatiotemporal Traffic Forecasting** | Real-time traffic speed & flow prediction | Spatial-Temporal Graph Convolutional Networks (ST-GCN), LightGBM with Spatial Lags, KD-Tree Spatial Indexing | 5-minute ahead speed forecasting with uncertainty quantification |
| **II. Causal Traffic Safety Evaluation** | Vision Zero & speed limit policy impact | Difference-in-Differences (DiD) with Cluster-Robust SE, Interrupted Time Series (ITS) | Quantifying ATT (Average Treatment Effect on the Treated) of urban speed reduction policies |
| **III. Spatial Accessibility & Network Analysis** | Multimodal transit equity & OD routing | OSMnx, NetworkX, GTFS Parsers, GeoPandas Spatial Joins | Isochrone mapping, transit desert index, and bottleneck identification |

---

## 3. Repository Structure

```text
urban-transport-intelligence/
├── data/                  # Sample datasets and raw data ingestion scripts
├── notebooks/             # Interactive exploratory data analysis & model training
├── src/
│   ├── __init__.py
│   ├── preprocessing.py   # Missing data imputation, spatial graph construction
│   ├── modeling.py        # LightGBM spatial-lag baseline & ST-GCN architecture
│   ├── causal_inference.py# DiD econometric models for safety interventions
│   └── visualize.py       # Publication-quality plot generation utilities
├── docs/
│   └── assets/            # Embedded high-resolution analysis figures
├── tests/                 # Unit tests for preprocessing and model pipelines
├── requirements.txt       # Project dependencies
└── README.md              # Comprehensive project documentation
```

---

## 4. Empirical Results & Visualizations

### 4.1. Spatiotemporal Traffic State Forecasting

Accurate short-term traffic forecasting is fundamental to advanced traveler information systems (ATIS) and dynamic traffic management. Using spatial lag features combined with gradient boosting and graph-based inductive biases, the model achieves robust predictive accuracy under congested regimes.

![Traffic Forecast](docs/assets/traffic_forecast.png)
*Figure 1: Comparison between actual highway speeds and predicted trajectories over a 4-hour horizon, demonstrating low MAE and reliable uncertainty bounds.*

### 4.2. Causal Impact of Urban Safety Interventions

Evaluating urban interventions (such as "Safe Speed 5030" or corridor-wide automated enforcement) often suffers from confounding temporal trends. We apply a robust **Difference-in-Differences (DiD)** econometric framework controlling for parallel trends.

![Safety Impact](docs/assets/safety_impact.png)
*Figure 2: Interrupted Time Series and Difference-in-Differences trajectory showing weekly collision frequency before and after policy intervention compared with a synthetic control group.*

---

## 5. Quick Start & Reproducibility

To set up the environment and reproduce the analysis pipeline locally:

```bash
# Clone the repository
git clone https://github.com/yourusername/urban-transport-intelligence.git
cd urban-transport-intelligence

# Install dependencies
pip install -r requirements.txt

# Run preprocessing and modeling pipeline
python3 src/preprocessing.py
python3 src/modeling.py
python3 src/visualize.py
```

---

## 6. References

1. Zhang, J., Zheng, Y., & Qi, D. (2017). Deep spatio-temporal residual networks for citywide crowd flows prediction. *AAAI Conference on Artificial Intelligence*.
2. Angrist, J. D., & Pischke, J. S. (2009). *Mostly Harmless Econometrics: An Empiricist's Companion*. Princeton University Press.
3. PeMS (Performance Measurement System). California Department of Transportation (Caltrans). Available at: [https://pems.dot.ca.gov/](https://pems.dot.ca.gov/)

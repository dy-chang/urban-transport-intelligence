"""Open-data travel demand, accessibility, and equity screening toolkit.

The package is designed as a transparent pre-model / sketch-planning layer for
DOT and MPO workflows. It pulls official Census data, implements a doubly
constrained gravity model, and produces geography-aware accessibility and
equity indicators that can be replaced with locally calibrated inputs.
"""

from .data_sources import ACSClient, CensusGeometryClient
from .demand_model import GravityModel, calibrate_beta
from .planning_metrics import build_equity_index, summarize_equity_gap

__all__ = [
    "ACSClient",
    "CensusGeometryClient",
    "GravityModel",
    "build_equity_index",
    "calibrate_beta",
    "summarize_equity_gap",
]

__version__ = "0.1.0"

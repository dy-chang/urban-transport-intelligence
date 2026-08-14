"""Unit tests for the travel-demand and planning-screen components."""

import numpy as np
import pandas as pd

from travel_demand_gis.demand_model import GravityModel, haversine_time_matrix
from travel_demand_gis.planning_metrics import build_equity_index, cumulative_accessibility


def test_gravity_model_balances_trip_ends():
    productions = np.array([100.0, 150.0, 50.0])
    attractions = np.array([75.0, 125.0, 100.0])
    impedance = np.array([[1.0, 15.0, 25.0], [15.0, 1.0, 10.0], [25.0, 10.0, 1.0]])
    flows = GravityModel(beta=0.08).fit_predict(productions, attractions, impedance)
    assert np.allclose(flows.sum(axis=1), productions)
    assert np.allclose(flows.sum(axis=0), attractions)
    assert np.isclose(flows.sum(), productions.sum())


def test_haversine_sketch_impedance_is_symmetric():
    impedance = haversine_time_matrix([-77.04, -77.00], [38.90, 38.92])
    assert impedance.shape == (2, 2)
    assert np.allclose(impedance, impedance.T)
    assert np.all(np.diag(impedance) == 1.0)


def test_equity_index_and_cumulative_accessibility():
    frame = pd.DataFrame({
        "population": [1_000, 2_000],
        "population_below_poverty": [300, 100],
        "households": [450, 800],
        "households_no_vehicle": [180, 40],
        "non_hispanic_white_population": [200, 1_600],
    })
    result = build_equity_index(frame)
    assert result.loc[0, "equity_screen_score"] > result.loc[1, "equity_screen_score"]
    accessibility = cumulative_accessibility([100, 200], np.array([[1.0, 20.0], [20.0, 1.0]]), 30.0)
    assert np.array_equal(accessibility, np.array([300.0, 300.0]))

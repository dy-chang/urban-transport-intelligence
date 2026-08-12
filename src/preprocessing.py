"""
Spatial-Temporal Traffic Data Preprocessing Module
Author: Transportation Engineering PhD Portfolio
Description: Handles missing data imputation, spatial graph construction, and feature engineering for traffic flow and speed forecasting.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from scipy.spatial import KDTree

class TrafficDataPreprocessor:
    def __init__(self, time_interval_min: int = 5):
        self.time_interval_min = time_interval_min
        self.scaler = StandardScaler()
        
    def impute_missing_data(self, df: pd.DataFrame, method: str = 'interpolate') -> pd.DataFrame:
        """
        Imputes missing values in loop detector or GPS probe speed/flow time series.
        """
        df_clean = df.copy()
        if method == 'interpolate':
            # Temporal linear interpolation followed by spatial KNN imputation if needed
            df_clean = df_clean.interpolate(method='time', limit_direction='both')
            df_clean = df_clean.fillna(method='bfill').fillna(method='ffill')
        elif method == 'knn':
            # Advanced spatial-temporal imputation placeholder
            pass
        return df_clean

    def extract_temporal_features(self, df: pd.DataFrame, timestamp_col: str) -> pd.DataFrame:
        """
        Extracts cyclical time features (hour of day, day of week, is_weekend) for machine learning models.
        """
        df_feat = df.copy()
        dt = pd.to_datetime(df_feat[timestamp_col])
        df_feat['hour'] = dt.dt.hour
        df_feat['day_of_week'] = dt.dt.dayofweek
        df_feat['is_weekend'] = (dt.dt.dayofweek >= 5).astype(int)
        
        # Cyclical encoding for hour
        df_feat['hour_sin'] = np.sin(2 * np.pi * df_feat['hour'] / 24.0)
        df_feat['hour_cos'] = np.cos(2 * np.pi * df_feat['hour'] / 24.0)
        return df_feat

    def build_adjacency_matrix(self, coords: np.ndarray, threshold_km: float = 2.0) -> np.ndarray:
        """
        Constructs a spatial adjacency (weight) matrix based on geographical distance threshold or Gaussian kernel.
        """
        tree = KDTree(coords)
        pairs = tree.query_pairs(r=threshold_km)
        n_nodes = len(coords)
        adj = np.zeros((n_nodes, n_nodes))
        
        for i, j in pairs:
            dist = np.linalg.norm(coords[i] - coords[j])
            # Gaussian kernel weighting
            adj[i, j] = np.exp(-(dist ** 2) / (threshold_km ** 2))
            adj[j, i] = adj[i, j]
            
        # Self-loops
        np.fill_diagonal(adj, 1.0)
        return adj

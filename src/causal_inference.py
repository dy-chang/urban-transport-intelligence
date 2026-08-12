"""
Traffic Safety Causal Inference & Policy Evaluation Module
Author: Transportation Engineering PhD Portfolio
Description: Implements Difference-in-Differences (DiD) and Interrupted Time Series (ITS) analysis to evaluate urban speed reduction policies (e.g., Safe Speed 5030).
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

class TrafficSafetyEvaluator:
    def __init__(self):
        pass

    def difference_in_differences(self, df: pd.DataFrame, outcome_col: str, treated_col: str, post_col: str) -> dict:
        """
        Estimates the causal effect of a traffic safety policy using Difference-in-Differences regression.
        Model: Y = beta_0 + beta_1 * Treated + beta_2 * Post + beta_3 * (Treated * Post) + epsilon
        """
        formula = f"{outcome_col} ~ {treated_col} + {post_col} + {treated_col}:{post_col}"
        model = smf.ols(formula, data=df).fit(cov_type='HC1') # Robust standard errors
        
        att = model.params[f"{treated_col}:{post_col}"]
        p_val = model.pvalues[f"{treated_col}:{post_col}"]
        conf_int = model.conf_int().loc[f"{treated_col}:{post_col}"]
        
        return {
            "ATT_Estimate": round(att, 4),
            "P_Value": round(p_val, 4),
            "Conf_Int_Lower": round(conf_int[0], 4),
            "Conf_Int_Upper": round(conf_int[1], 4),
            "Summary": model.summary().as_text()
        }

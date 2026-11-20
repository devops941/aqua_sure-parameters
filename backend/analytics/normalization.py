"""
AquaSure Backend - Parameter Normalization
Normalizes each water quality parameter against BIS 10500:2012 standards.
Produces columns like norm_ph, norm_tds, etc., in the range [0, ∞) where
1.0 = exactly at the acceptable limit.
"""

import numpy as np
import pandas as pd
from backend.analytics.wqi_calculator import WQI_PARAM_STANDARDS


def normalize_parameters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add normalized columns (norm_<param>) to a copy of the DataFrame.

    For pH: normalized = abs(val - 7.0) / 1.5  (ideal = 7.0, limit diff = 1.5)
    For others: normalized = val / standard_acceptable

    Values > 1.0 indicate exceedance of the acceptable limit.
    NaN where the original value is missing or out of physical bounds.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame with raw parameter columns.

    Returns
    -------
    pd.DataFrame
        Copy of df with additional norm_<param> columns.
    """
    df = df.copy()

    for param, meta in WQI_PARAM_STANDARDS.items():
        if param not in df.columns:
            continue

        col = df[param].copy()
        valid_mask = (
            col.notna()
            & (col >= meta["min_valid"])
            & (col <= meta["max_valid"])
        )

        if param == "ph":
            norm = np.where(
                valid_mask,
                np.abs(col - 7.0) / 1.5,
                np.nan,
            )
        else:
            std = meta["standard_acceptable"]
            norm = np.where(
                valid_mask,
                col / std,
                np.nan,
            )

        df[f"norm_{param}"] = np.round(norm, 4)

    return df


def exceedance_summary(df: pd.DataFrame) -> list:
    """
    For each parameter, compute the percentage of valid samples that exceed
    the BIS permissible limit.

    Returns list of dicts sorted by exceed_pct descending.
    """
    results = []
    for param, meta in WQI_PARAM_STANDARDS.items():
        if param not in df.columns:
            continue
        col = df[param].dropna()
        valid = col[(col >= meta["min_valid"]) & (col <= meta["max_valid"])]
        if len(valid) == 0:
            continue
        exceed_count = int((valid > meta["standard_permissible"]).sum())
        exceed_pct = round((exceed_count / len(valid)) * 100, 2)
        results.append(
            {
                "parameter": param,
                "name": meta["name"],
                "unit": meta["unit"],
                "standard_permissible": meta["standard_permissible"],
                "valid_samples": len(valid),
                "exceed_count": exceed_count,
                "exceed_pct": exceed_pct,
            }
        )
    results.sort(key=lambda x: x["exceed_pct"], reverse=True)
    return results

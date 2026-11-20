"""
AquaSure Backend - Sensitivity Analysis
Varies one or all parameters ±X% and measures the resulting WQI change.
"""

import numpy as np
from typing import Dict, List
from backend.analytics.wqi_calculator import calculate_wqi, WQI_PARAM_STANDARDS


def sensitivity_analysis(
    base_params: dict,
    vary_param: str,
    pct_range: float = 80.0,
    n_steps: int = 20,
) -> List[dict]:
    """
    Vary `vary_param` from (1 - pct_range/100)*base_value to
    (1 + pct_range/100)*base_value in `n_steps` equal steps, and record
    the resulting WQI.

    Parameters
    ----------
    base_params : dict
        Dictionary of water quality parameter values.
    vary_param : str
        The parameter to vary (must be a key in WQI_PARAM_STANDARDS).
    pct_range : float
        Percentage of base value to sweep in each direction (default 80%).
    n_steps : int
        Number of sweep points (default 20).

    Returns
    -------
    list of dicts: [{value, wqi, pct_change}, ...]
        value      – the parameter value at that step
        wqi        – computed WQI
        pct_change – percentage change in WQI from baseline
    """
    if vary_param not in WQI_PARAM_STANDARDS:
        raise ValueError(
            f"Parameter '{vary_param}' not in WQI standards. "
            f"Valid params: {list(WQI_PARAM_STANDARDS.keys())}"
        )

    base_val = base_params.get(vary_param)
    if base_val is None:
        raise ValueError(
            f"Parameter '{vary_param}' not found in base_params."
        )
    base_val = float(base_val)

    # Baseline WQI
    base_result = calculate_wqi(base_params)
    base_wqi = base_result["wqi"] or 0.0

    meta = WQI_PARAM_STANDARDS[vary_param]
    factor_min = 1.0 - pct_range / 100.0
    factor_max = 1.0 + pct_range / 100.0

    # Clamp min to physical lower bound
    min_val = max(base_val * factor_min, meta["min_valid"])
    max_val = min(base_val * factor_max, meta["max_valid"])

    sweep_values = np.linspace(min_val, max_val, n_steps)
    results = []

    for val in sweep_values:
        trial_params = dict(base_params)
        trial_params[vary_param] = float(val)
        result = calculate_wqi(trial_params)
        wqi = result["wqi"]
        if wqi is None:
            pct_chg = None
        else:
            pct_chg = round(((wqi - base_wqi) / base_wqi) * 100, 2) if base_wqi != 0 else None
        results.append(
            {
                "value": round(float(val), 4),
                "wqi": wqi,
                "pct_change": pct_chg,
            }
        )

    return results


def multi_sensitivity(
    base_params: dict,
    pct_range: float = 50.0,
    n_steps: int = 10,
) -> Dict[str, List[dict]]:
    """
    Run sensitivity analysis for every parameter present in base_params.

    Parameters
    ----------
    base_params : dict
        Dictionary of water quality parameter values.
    pct_range : float
        Percentage sweep range (default 50%).
    n_steps : int
        Steps per parameter (default 10).

    Returns
    -------
    dict mapping param_name -> list of {value, wqi, pct_change}
    """
    output = {}
    for param in WQI_PARAM_STANDARDS:
        if param in base_params and base_params[param] is not None:
            try:
                output[param] = sensitivity_analysis(
                    base_params, param, pct_range=pct_range, n_steps=n_steps
                )
            except (ValueError, ZeroDivisionError):
                output[param] = []
    return output

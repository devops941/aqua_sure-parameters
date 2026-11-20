"""
AquaSure Backend - WQI Calculator
Standalone WAWQI computation (copied from src/wqi_engine.py logic).
No dependency on the src/ package, safe to import in the backend.
"""

import numpy as np
from typing import Dict, List

# ---------------------------------------------------------------------------
# BIS 10500:2012 standards (copied from src/config.py)
# ---------------------------------------------------------------------------
WQI_PARAM_STANDARDS: Dict[str, dict] = {
    "ph": {
        "name": "pH (Potential of Hydrogen)",
        "unit": "pH unit",
        "standard_acceptable": 8.5,
        "standard_permissible": 8.5,
        "ideal_value": 7.0,
        "weight": 4,
        "min_valid": 4.0,
        "max_valid": 11.5,
    },
    "tds": {
        "name": "Total Dissolved Solids (TDS)",
        "unit": "mg/L",
        "standard_acceptable": 500.0,
        "standard_permissible": 2000.0,
        "ideal_value": 0.0,
        "weight": 5,
        "min_valid": 0.0,
        "max_valid": 70000.0,
    },
    "ec": {
        "name": "Electrical Conductivity (EC)",
        "unit": "µS/cm",
        "standard_acceptable": 750.0,
        "standard_permissible": 2250.0,
        "ideal_value": 0.0,
        "weight": 3,
        "min_valid": 0.0,
        "max_valid": 70000.0,
    },
    "hardness": {
        "name": "Total Hardness (as CaCO3)",
        "unit": "mg/L",
        "standard_acceptable": 200.0,
        "standard_permissible": 600.0,
        "ideal_value": 0.0,
        "weight": 3,
        "min_valid": 0.0,
        "max_valid": 20000.0,
    },
    "ca": {
        "name": "Calcium (Ca)",
        "unit": "mg/L",
        "standard_acceptable": 75.0,
        "standard_permissible": 200.0,
        "ideal_value": 0.0,
        "weight": 2,
        "min_valid": 0.0,
        "max_valid": 5000.0,
    },
    "mg": {
        "name": "Magnesium (Mg)",
        "unit": "mg/L",
        "standard_acceptable": 30.0,
        "standard_permissible": 100.0,
        "ideal_value": 0.0,
        "weight": 2,
        "min_valid": 0.0,
        "max_valid": 4000.0,
    },
    "cl": {
        "name": "Chloride (Cl)",
        "unit": "mg/L",
        "standard_acceptable": 250.0,
        "standard_permissible": 1000.0,
        "ideal_value": 0.0,
        "weight": 3,
        "min_valid": 0.0,
        "max_valid": 40000.0,
    },
    "so4": {
        "name": "Sulphate (SO4)",
        "unit": "mg/L",
        "standard_acceptable": 200.0,
        "standard_permissible": 400.0,
        "ideal_value": 0.0,
        "weight": 4,
        "min_valid": 0.0,
        "max_valid": 10000.0,
    },
    "no3": {
        "name": "Nitrate (NO3)",
        "unit": "mg/L",
        "standard_acceptable": 45.0,
        "standard_permissible": 45.0,
        "ideal_value": 0.0,
        "weight": 5,
        "min_valid": 0.0,
        "max_valid": 5000.0,
    },
    "f": {
        "name": "Fluoride (F)",
        "unit": "mg/L",
        "standard_acceptable": 1.0,
        "standard_permissible": 1.5,
        "ideal_value": 0.0,
        "weight": 5,
        "min_valid": 0.0,
        "max_valid": 15.0,
    },
}

WQI_CATEGORIES = [
    {"grade": "A", "category": "Excellent", "range": (0, 25), "potability": "Potable"},
    {"grade": "B", "category": "Good", "range": (26, 50), "potability": "Potable"},
    {"grade": "C", "category": "Poor", "range": (51, 75), "potability": "Requires Treatment"},
    {"grade": "D", "category": "Very Poor", "range": (76, 100), "potability": "Non-Potable"},
    {"grade": "E", "category": "Unsuitable for Drinking", "range": (101, float("inf")), "potability": "Hazardous / Unfit"},
]


def _categorize(wqi_score: float) -> dict:
    for cat in WQI_CATEGORIES:
        low, high = cat["range"]
        if low <= wqi_score <= high:
            return cat
    return WQI_CATEGORIES[-1]


def calculate_wqi(params: dict) -> dict:
    """
    Compute WAWQI for a single set of water quality parameters.

    Parameters
    ----------
    params : dict
        Keys are parameter names (ph, tds, ec, hardness, ca, mg, cl, so4, no3, f).
        Values are numeric measurements. Missing or None values are ignored.

    Returns
    -------
    dict with keys:
        wqi, grade, category, potability, is_potable, violations, sub_indices
    """
    active_params: Dict[str, float] = {}
    total_raw_weight = 0.0

    for param, meta in WQI_PARAM_STANDARDS.items():
        raw = params.get(param)
        if raw is None:
            continue
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue
        if np.isnan(val):
            continue
        if meta["min_valid"] <= val <= meta["max_valid"]:
            active_params[param] = val
            total_raw_weight += meta["weight"]

    if not active_params or total_raw_weight == 0:
        return {
            "wqi": None,
            "grade": "N/A",
            "category": "Unknown",
            "potability": "Unknown",
            "is_potable": False,
            "violations": ["No valid parameters provided"],
            "sub_indices": {},
        }

    wqi_sum = 0.0
    violations: List[str] = []
    sub_indices: Dict[str, float] = {}

    for param, val in active_params.items():
        meta = WQI_PARAM_STANDARDS[param]
        weight_norm = meta["weight"] / total_raw_weight

        if param == "ph":
            qi = (abs(val - 7.0) / 1.5) * 100.0
            if val < 6.5 or val > 8.5:
                violations.append(
                    f"pH out of range: {val:.2f} (Permissible: 6.5–8.5)"
                )
        else:
            std = meta["standard_acceptable"]
            qi = (val / std) * 100.0
            if val > meta["standard_permissible"]:
                violations.append(
                    f"{meta['name']} exceeded permissible limit: "
                    f"{val:.2f} {meta['unit']} (Max: {meta['standard_permissible']})"
                )

        wqi_sum += weight_norm * qi
        sub_indices[param] = {
            "qi": round(qi, 2),
            "value": round(val, 4),
            "weight": meta["weight"],
            "normalized_weight": round(weight_norm, 4),
            "standard_acceptable": meta["standard_acceptable"],
        }

    wqi_score = round(float(wqi_sum), 2)
    cat_info = _categorize(wqi_score)

    # Strict potability determination
    critical_breach = False
    if "no3" in active_params and active_params["no3"] > 45.0:
        critical_breach = True
    if "f" in active_params and active_params["f"] > 1.5:
        critical_breach = True
    if "ph" in active_params and (active_params["ph"] < 6.5 or active_params["ph"] > 8.5):
        critical_breach = True
    if "tds" in active_params and active_params["tds"] > 2000.0:
        critical_breach = True

    if wqi_score <= 50.0 and not critical_breach:
        potability = "Potable"
    elif wqi_score <= 75.0 and not critical_breach:
        potability = "Requires Basic Treatment"
    elif wqi_score <= 100.0 or critical_breach:
        potability = "Requires Advanced Treatment"
    else:
        potability = "Non-Potable / Hazardous"

    return {
        "wqi": wqi_score,
        "grade": cat_info["grade"],
        "category": cat_info["category"],
        "potability": potability,
        "is_potable": potability == "Potable",
        "violations": violations,
        "sub_indices": sub_indices,
    }


def get_parameters_metadata() -> list:
    """Return list of all parameters with BIS standards and weights."""
    result = []
    for key, meta in WQI_PARAM_STANDARDS.items():
        result.append(
            {
                "param": key,
                "name": meta["name"],
                "unit": meta["unit"],
                "weight": meta["weight"],
                "standard_acceptable": meta["standard_acceptable"],
                "standard_permissible": meta["standard_permissible"],
                "ideal_value": meta["ideal_value"],
                "min_valid": meta["min_valid"],
                "max_valid": meta["max_valid"],
            }
        )
    return result

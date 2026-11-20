"""
AquaSure WQI Engine Module
Calculates the Weighted Arithmetic Water Quality Index (WAWQI) and potability metrics
based on BIS (IS 10500:2012) and WHO standards for Tamil Nadu groundwater.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, List, Optional
from src.config import WQI_PARAM_STANDARDS, WQI_CATEGORIES, DISTRICT_SUMMARY_PATH

def compute_sample_wqi(row: pd.Series) -> Dict:
    """
    Computes WAWQI for a single water sample using dynamically normalized weights
    based on the parameters actually measured in the sample.
    """
    active_params = {}
    total_raw_weight = 0.0
    
    # 1. Gather available parameters
    for param, meta in WQI_PARAM_STANDARDS.items():
        if param in row and pd.notna(row[param]):
            val = float(row[param])
            # Check if within valid physical boundary
            if meta["min_valid"] <= val <= meta["max_valid"]:
                active_params[param] = val
                total_raw_weight += meta["weight"]
                
    if not active_params or total_raw_weight == 0:
        return {
            "wqi": np.nan,
            "category": "Unknown",
            "grade": "N/A",
            "potability": "Unknown",
            "active_param_count": 0,
            "violations": []
        }
        
    # 2. Compute sub-indices and weighted sum
    wqi_sum = 0.0
    violations = []
    
    for param, val in active_params.items():
        meta = WQI_PARAM_STANDARDS[param]
        weight_norm = meta["weight"] / total_raw_weight
        
        # Calculate sub-index qi
        if param == "ph":
            # Ideal is 7.0, permissible upper is 8.5 (diff = 1.5)
            qi = (abs(val - 7.0) / 1.5) * 100.0
            if val < 6.5 or val > 8.5:
                violations.append(f"pH out of range: {val:.2f} (Permissible: 6.5 - 8.5)")
        else:
            std = meta["standard_acceptable"]
            qi = (val / std) * 100.0
            if val > meta["standard_permissible"]:
                violations.append(f"{meta['name']} exceeded limit: {val:.1f} {meta['unit']} (Max: {meta['standard_permissible']})")
                
        wqi_sum += weight_norm * qi
        
    wqi_score = round(float(wqi_sum), 2)
    
    # 3. Categorize WQI
    category_info = WQI_CATEGORIES[-1] # Default to Grade E
    for cat in WQI_CATEGORIES:
        low, high = cat["range"]
        if low <= wqi_score <= high:
            category_info = cat
            break
            
    # 4. Potability determination
    # Strict potability requires WQI <= 50 AND no critical chemical breach (NO3 > 45, F > 1.5, pH < 6.5 or > 8.5)
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
        "category": category_info["category"],
        "grade": category_info["grade"],
        "color": category_info["color"],
        "potability": potability,
        "is_potable": potability == "Potable",
        "active_param_count": len(active_params),
        "violations": violations
    }

def calculate_wqi_vectorized(df: pd.DataFrame) -> pd.DataFrame:
    """
    High-performance vector calculation of WAWQI across the entire DataFrame.
    """
    df = df.copy()
    
    # Calculate parameter-level sub-indices (qi)
    qi_dict = {}
    wi_dict = {}
    
    for param, meta in WQI_PARAM_STANDARDS.items():
        if param in df.columns:
            s = df[param].copy()
            valid_mask = (s >= meta["min_valid"]) & (s <= meta["max_valid"]) & s.notna()
            
            # Sub-index formula
            if param == "ph":
                qi = np.where(valid_mask, (np.abs(s - 7.0) / 1.5) * 100.0, np.nan)
            else:
                qi = np.where(valid_mask, (s / meta["standard_acceptable"]) * 100.0, np.nan)
                
            qi_dict[param] = qi
            wi_dict[param] = np.where(valid_mask, meta["weight"], 0.0)
            
    # Total active weight per row
    total_weights = np.zeros(len(df))
    for param in wi_dict:
        total_weights += wi_dict[param]
        
    # Prevent division by zero
    total_weights_safe = np.where(total_weights > 0, total_weights, np.nan)
    
    # Weighted arithmetic sum
    wqi_array = np.zeros(len(df))
    for param in qi_dict:
        norm_w = wi_dict[param] / total_weights_safe
        wqi_array += np.nan_to_num(norm_w * qi_dict[param], nan=0.0)
        
    wqi_array = np.where(total_weights > 0, np.round(wqi_array, 2), np.nan)
    df["wqi"] = wqi_array
    
    # Assign category & grade
    conditions = [
        df["wqi"] <= 25.0,
        (df["wqi"] > 25.0) & (df["wqi"] <= 50.0),
        (df["wqi"] > 50.0) & (df["wqi"] <= 75.0),
        (df["wqi"] > 75.0) & (df["wqi"] <= 100.0),
        df["wqi"] > 100.0
    ]
    categories = ["Excellent", "Good", "Poor", "Very Poor", "Unsuitable for Drinking"]
    grades = ["A", "B", "C", "D", "E"]
    
    df["wqi_category"] = np.select(conditions, categories, default="Unknown")
    df["wqi_grade"] = np.select(conditions, grades, default="N/A")
    
    # Potability indicator:
    # Potable = WQI <= 50 and NO3 <= 45 and F <= 1.5 and 6.5 <= pH <= 8.5 and TDS <= 2000
    no3_safe = (df["no3"] <= 45.0) | df["no3"].isna()
    f_safe = (df["f"] <= 1.5) | df["f"].isna()
    ph_safe = ((df["ph"] >= 6.5) & (df["ph"] <= 8.5)) | df["ph"].isna()
    tds_safe = (df["tds"] <= 2000.0) | df["tds"].isna()
    
    is_potable = (df["wqi"] <= 50.0) & no3_safe & f_safe & ph_safe & tds_safe
    df["is_potable"] = is_potable
    
    pot_conditions = [
        is_potable,
        (df["wqi"] <= 75.0) & no3_safe & f_safe & ph_safe & tds_safe,
        (df["wqi"] <= 100.0) | (~no3_safe) | (~f_safe) | (~ph_safe),
        df["wqi"] > 100.0
    ]
    pot_labels = [
        "Potable",
        "Requires Basic Treatment",
        "Requires Advanced Treatment",
        "Non-Potable / Hazardous"
    ]
    df["potability_status"] = np.select(pot_conditions, pot_labels, default="Requires Advanced Treatment")
    
    return df

def generate_district_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes rigorous aggregated water quality statistics for all 38 districts of Tamil Nadu.
    """
    summary_list = []
    
    for district, grp in df.groupby("district"):
        total_samples = len(grp)
        valid_wqi = grp["wqi"].dropna()
        if len(valid_wqi) == 0:
            continue
            
        mean_wqi = round(valid_wqi.mean(), 2)
        median_wqi = round(valid_wqi.median(), 2)
        std_wqi = round(valid_wqi.std(), 2) if len(valid_wqi) > 1 else 0.0
        
        # Categorical distribution (%)
        grade_a = round(((grp["wqi_grade"] == "A").sum() / total_samples) * 100, 1)
        grade_b = round(((grp["wqi_grade"] == "B").sum() / total_samples) * 100, 1)
        grade_c = round(((grp["wqi_grade"] == "C").sum() / total_samples) * 100, 1)
        grade_d = round(((grp["wqi_grade"] == "D").sum() / total_samples) * 100, 1)
        grade_e = round(((grp["wqi_grade"] == "E").sum() / total_samples) * 100, 1)
        
        potable_pct = round(((grp["is_potable"] == True).sum() / total_samples) * 100, 1)
        
        # Determine dominant overall status
        if median_wqi <= 25:
            overall_status = "Excellent"
        elif median_wqi <= 50:
            overall_status = "Good"
        elif median_wqi <= 75:
            overall_status = "Poor"
        elif median_wqi <= 100:
            overall_status = "Very Poor"
        else:
            overall_status = "Unsuitable for Drinking"
            
        # Key parameter averages
        avg_tds = round(grp["tds"].mean(), 1) if "tds" in grp else np.nan
        avg_ph = round(grp["ph"].mean(), 2) if "ph" in grp else np.nan
        avg_no3 = round(grp["no3"].mean(), 1) if "no3" in grp else np.nan
        avg_f = round(grp["f"].mean(), 2) if "f" in grp else np.nan
        avg_ec = round(grp["ec"].mean(), 1) if "ec" in grp else np.nan
        avg_hardness = round(grp["hardness"].mean(), 1) if "hardness" in grp else np.nan
        
        # Contaminants exceeding permissible limits (%)
        tds_exceed_pct = round(((grp["tds"] > 2000.0).sum() / total_samples) * 100, 1) if "tds" in grp else 0.0
        no3_exceed_pct = round(((grp["no3"] > 45.0).sum() / total_samples) * 100, 1) if "no3" in grp else 0.0
        f_exceed_pct = round(((grp["f"] > 1.5).sum() / total_samples) * 100, 1) if "f" in grp else 0.0
        
        # Top primary concern
        concerns = []
        if no3_exceed_pct > 20.0:
            concerns.append(f"Nitrate ({no3_exceed_pct}%)")
        if tds_exceed_pct > 15.0:
            concerns.append(f"Salinity/TDS ({tds_exceed_pct}%)")
        if f_exceed_pct > 10.0:
            concerns.append(f"Fluoride ({f_exceed_pct}%)")
        primary_concern = ", ".join(concerns) if concerns else "None (Within Limits)"
        
        summary_list.append({
            "district": district,
            "total_samples": total_samples,
            "mean_wqi": mean_wqi,
            "median_wqi": median_wqi,
            "std_wqi": std_wqi,
            "overall_status": overall_status,
            "potable_pct": potable_pct,
            "grade_a_pct": grade_a,
            "grade_b_pct": grade_b,
            "grade_c_pct": grade_c,
            "grade_d_pct": grade_d,
            "grade_e_pct": grade_e,
            "avg_tds": avg_tds,
            "avg_ph": avg_ph,
            "avg_no3": avg_no3,
            "avg_f": avg_f,
            "avg_ec": avg_ec,
            "avg_hardness": avg_hardness,
            "no3_exceed_pct": no3_exceed_pct,
            "tds_exceed_pct": tds_exceed_pct,
            "f_exceed_pct": f_exceed_pct,
            "primary_concern": primary_concern
        })
        
    summary_df = pd.DataFrame(summary_list).sort_values(by="median_wqi")
    return summary_df

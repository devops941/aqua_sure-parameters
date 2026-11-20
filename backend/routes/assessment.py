"""
AquaSure Backend - Water Assessment Route
POST /api/assess-water   - Full BIS 10500:2012 assessment for a water sample
"""

from flask import Blueprint, jsonify, request
from datetime import date
from backend.analytics.wqi_calculator import calculate_wqi, WQI_PARAM_STANDARDS

assessment_bp = Blueprint("assessment", __name__)

PARAM_DISPLAY = {
    "ph":       {"name": "pH",                  "unit": "pH units"},
    "tds":      {"name": "Total Dissolved Solids (TDS)", "unit": "mg/L"},
    "ec":       {"name": "Electrical Conductivity (EC)", "unit": "µS/cm"},
    "hardness": {"name": "Total Hardness",       "unit": "mg/L"},
    "ca":       {"name": "Calcium (Ca)",         "unit": "mg/L"},
    "mg":       {"name": "Magnesium (Mg)",        "unit": "mg/L"},
    "cl":       {"name": "Chloride (Cl)",         "unit": "mg/L"},
    "so4":      {"name": "Sulphate (SO4)",        "unit": "mg/L"},
    "no3":      {"name": "Nitrate (NO3)",         "unit": "mg/L"},
    "f":        {"name": "Fluoride (F)",          "unit": "mg/L"},
}


def _param_status(key: str, value: float) -> dict:
    meta = WQI_PARAM_STANDARDS[key]
    acc  = meta["standard_acceptable"]
    perm = meta["standard_permissible"]

    if key == "ph":
        if 6.5 <= value <= 8.5:
            return {"status": "Normal", "status_code": "normal",
                    "observation": f"pH {value:.2f} is within the acceptable range (6.5–8.5)."}
        else:
            return {"status": "Above Permissible Limit", "status_code": "above_permissible",
                    "observation": f"pH {value:.2f} is outside the permissible range (6.5–8.5). Neutralization required."}

    if value <= acc:
        obs = f"{PARAM_DISPLAY[key]['name']} ({value:.2f} {meta['unit']}) is within the acceptable limit of {acc} {meta['unit']}."
        return {"status": "Normal", "status_code": "normal", "observation": obs}
    elif value <= perm:
        obs = f"{PARAM_DISPLAY[key]['name']} ({value:.2f} {meta['unit']}) exceeds the acceptable limit ({acc}) but is within the permissible limit ({perm} {meta['unit']})."
        return {"status": "Above Acceptable Limit", "status_code": "above_acceptable", "observation": obs}
    else:
        obs = f"{PARAM_DISPLAY[key]['name']} ({value:.2f} {meta['unit']}) exceeds the permissible limit of {perm} {meta['unit']}. Immediate treatment required."
        return {"status": "Above Permissible Limit", "status_code": "above_permissible", "observation": obs}


def _build_recommendations(params: dict, wqi_result: dict) -> list:
    recs = []
    exceeded = [v for v in params if v in WQI_PARAM_STANDARDS]

    for key, val in params.items():
        meta = WQI_PARAM_STANDARDS.get(key)
        if not meta:
            continue
        if key == "tds" and val > meta["standard_acceptable"]:
            recs.append("Install a Reverse Osmosis (RO) filtration system to reduce elevated dissolved solids.")
        if key == "no3" and val > meta["standard_permissible"]:
            recs.append("High nitrate detected. Avoid use for infant feeding. Identify and mitigate agricultural runoff sources near the well.")
        if key == "f" and val > meta["standard_permissible"]:
            recs.append("Fluoride exceeds safe limits. Install a defluoridation unit (activated alumina or Nalgonda technique).")
        if key == "cl" and val > meta["standard_permissible"]:
            recs.append("High chloride may indicate saltwater intrusion or industrial contamination. Seek alternative water sources.")
        if key == "hardness" and val > meta["standard_acceptable"]:
            recs.append("Water is moderately to highly hard. Consider a water softening system before domestic use.")
        if key == "ph" and (val < 6.5 or val > 8.5):
            recs.append("pH is outside the acceptable range. pH correction/neutralization treatment is recommended.")

    if not recs:
        recs = [
            "No major BIS IS 10500:2012 violations detected. Maintain regular water quality monitoring.",
            "Ensure the water source is protected from surface contamination and agricultural runoff.",
        ]
    recs.append("Consider periodic laboratory testing for parameters not covered in this assessment (e.g., microbial contamination, heavy metals).")
    return recs


def _overall_assessment(wqi: float, is_potable: bool) -> str:
    if is_potable:
        return "Good — Water appears potable. Regular monitoring recommended."
    if wqi <= 75:
        return "Moderate — Water requires basic treatment (filtration/disinfection) before use."
    if wqi <= 100:
        return "Poor — Water requires advanced treatment. Not suitable for direct drinking."
    return "Critical — Water is unsafe for drinking. Immediate remediation required."


@assessment_bp.route("/api/assess-water", methods=["POST"])
def assess_water():
    try:
        body = request.get_json(force=True, silent=True) or {}

        sample_name = str(body.get("sample_name", "Water Sample")).strip() or "Water Sample"
        district    = str(body.get("district", "")).strip()

        # Collect numeric params
        raw_params = {}
        for key in WQI_PARAM_STANDARDS:
            raw = body.get(key)
            if raw is not None:
                try:
                    raw_params[key] = float(raw)
                except (TypeError, ValueError):
                    pass

        if not raw_params:
            return jsonify({"error": "No valid water quality parameters provided."}), 400

        # WQI calculation
        wqi_result = calculate_wqi(raw_params)

        # Per-parameter assessment
        parameters = []
        params_tested     = []
        params_not_tested = []

        for key, meta in WQI_PARAM_STANDARDS.items():
            if key in raw_params:
                val    = raw_params[key]
                status = _param_status(key, val)
                sub_qi = wqi_result["sub_indices"].get(key, {})
                parameters.append({
                    "key":               key,
                    "name":              PARAM_DISPLAY[key]["name"],
                    "unit":              meta["unit"],
                    "value":             round(val, 4),
                    "acceptable_limit":  meta["standard_acceptable"],
                    "permissible_limit": meta["standard_permissible"],
                    "status":            status["status"],
                    "status_code":       status["status_code"],
                    "sub_index":         sub_qi.get("qi", None) if isinstance(sub_qi, dict) else sub_qi,
                    "weight":            meta["weight"],
                    "observation":       status["observation"],
                })
                params_tested.append(key)
            else:
                params_not_tested.append(key)

        wqi_val = wqi_result["wqi"] or 0.0
        recs    = _build_recommendations(raw_params, wqi_result)
        overall = _overall_assessment(wqi_val, wqi_result["is_potable"])

        return jsonify({
            "sample_name":        sample_name,
            "district":           district,
            "assessment_date":    date.today().isoformat(),
            "wqi":                wqi_result["wqi"],
            "grade":              wqi_result["grade"],
            "category":           wqi_result["category"],
            "potability":         wqi_result["potability"],
            "is_potable":         wqi_result["is_potable"],
            "overall_assessment": overall,
            "parameters":         parameters,
            "violations":         wqi_result["violations"],
            "recommendations":    recs,
            "params_tested":      params_tested,
            "params_not_tested":  params_not_tested,
            "disclaimer":         (
                "This is a preliminary assessment based on BIS IS 10500:2012 standards. "
                "It does not substitute for certified laboratory testing. "
                "Parameters not provided in this assessment may affect actual water quality. "
                "Consult a certified water testing laboratory for a comprehensive analysis."
            ),
        })

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

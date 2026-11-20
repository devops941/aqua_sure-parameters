"""
AquaSure Backend - Calculator Routes
POST /api/calculate-wqi     - Compute WQI for user-supplied parameters
GET  /api/sensitivity       - Sensitivity analysis for a specific parameter
GET  /api/parameters        - List all BIS parameter standards
"""

from flask import Blueprint, jsonify, request
from backend.analytics.wqi_calculator import (
    calculate_wqi,
    get_parameters_metadata,
    WQI_PARAM_STANDARDS,
)
from backend.analytics.sensitivity import sensitivity_analysis

calculator_bp = Blueprint("calculator", __name__)

_VALID_PARAMS = set(WQI_PARAM_STANDARDS.keys())


def _parse_float(val):
    """Return float or None if conversion fails."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@calculator_bp.route("/api/calculate-wqi", methods=["POST"])
def compute_wqi():
    """
    POST /api/calculate-wqi
    Body (JSON): {"ph": 7.2, "tds": 450, "hardness": 200, ...}
    Returns WQI result with sub-indices, grade, violations, and potability.
    """
    try:
        body = request.get_json(force=True, silent=True)
        if not body:
            return jsonify({"error": "Request body must be JSON with water quality parameters."}), 400

        params = {}
        unknown = []
        for key, val in body.items():
            k = key.lower().strip()
            if k in _VALID_PARAMS:
                parsed = _parse_float(val)
                if parsed is not None:
                    params[k] = parsed
            else:
                unknown.append(key)

        if not params:
            return jsonify(
                {
                    "error": "No valid parameters provided.",
                    "valid_parameters": sorted(_VALID_PARAMS),
                }
            ), 400

        result = calculate_wqi(params)

        response = {
            "wqi": result["wqi"],
            "grade": result["grade"],
            "category": result["category"],
            "potability": result["potability"],
            "is_potable": result["is_potable"],
            "violations": result["violations"],
            "sub_indices": result["sub_indices"],
            "params_used": list(params.keys()),
        }
        if unknown:
            response["unknown_params_ignored"] = unknown

        return jsonify(response)

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@calculator_bp.route("/api/sensitivity", methods=["GET"])
def get_sensitivity():
    """
    GET /api/sensitivity?param=tds&ph=7.2&tds=450&hardness=200&...
    Vary the specified parameter ±80% in 20 steps, return sensitivity data.
    """
    try:
        vary_param = request.args.get("param", "").lower().strip()
        if not vary_param:
            return jsonify({"error": "Query parameter 'param' is required."}), 400
        if vary_param not in _VALID_PARAMS:
            return jsonify(
                {
                    "error": f"Parameter '{vary_param}' not recognized.",
                    "valid_parameters": sorted(_VALID_PARAMS),
                }
            ), 400

        # Collect all other query params as base parameter values
        base_params = {}
        for key, val in request.args.items():
            if key == "param":
                continue
            k = key.lower().strip()
            if k in _VALID_PARAMS:
                parsed = _parse_float(val)
                if parsed is not None:
                    base_params[k] = parsed

        if vary_param not in base_params:
            return jsonify(
                {"error": f"Base value for '{vary_param}' must be supplied as a query parameter."}
            ), 400

        pct_range = _parse_float(request.args.get("pct_range")) or 80.0
        n_steps = int(request.args.get("n_steps") or 20)
        n_steps = max(5, min(n_steps, 100))

        data = sensitivity_analysis(
            base_params, vary_param, pct_range=pct_range, n_steps=n_steps
        )

        from backend.analytics.wqi_calculator import calculate_wqi as _cw
        baseline = _cw(base_params)

        return jsonify(
            {
                "vary_param": vary_param,
                "base_value": base_params[vary_param],
                "base_wqi": baseline["wqi"],
                "pct_range": pct_range,
                "n_steps": n_steps,
                "data": data,
            }
        )

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@calculator_bp.route("/api/parameters", methods=["GET"])
def list_parameters():
    """
    GET /api/parameters
    Returns all BIS 10500:2012 parameters with standards, weights, and units.
    """
    try:
        return jsonify(get_parameters_metadata())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

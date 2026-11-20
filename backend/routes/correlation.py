"""
AquaSure Backend - Correlation Route
GET /api/correlation
Returns the Pearson correlation matrix for key water quality parameters.
"""

from flask import Blueprint, jsonify, request
import numpy as np
from backend.analytics.data_loader import get_dataframe

correlation_bp = Blueprint("correlation", __name__)

DEFAULT_PARAMS = ["ph", "tds", "ec", "hardness", "ca", "mg", "cl", "so4", "no3", "f"]


@correlation_bp.route("/api/correlation", methods=["GET"])
def get_correlation():
    """
    GET /api/correlation[?params=ph,tds,ec,...]
    Returns the Pearson correlation matrix for the specified (or default) parameters.
    Only rows with no NaN across all requested parameters are used.
    """
    try:
        df = get_dataframe()

        # Allow caller to override the parameter list
        params_arg = request.args.get("params")
        if params_arg:
            requested = [p.strip().lower() for p in params_arg.split(",") if p.strip()]
        else:
            requested = DEFAULT_PARAMS

        # Keep only columns that exist in the dataframe
        available = [p for p in requested if p in df.columns]
        if len(available) < 2:
            return jsonify(
                {
                    "error": "At least 2 valid parameters are required for correlation.",
                    "requested": requested,
                    "available_in_data": available,
                }
            ), 400

        subset = df[available].dropna()
        if len(subset) < 2:
            return jsonify(
                {"error": "Not enough complete rows to compute correlation."}
            ), 400

        corr_matrix = subset.corr(method="pearson")
        # Round and convert to Python-native floats for JSON serialisation
        matrix_list = []
        for row_param in available:
            row = []
            for col_param in available:
                val = corr_matrix.loc[row_param, col_param]
                row.append(round(float(val), 4) if not np.isnan(val) else None)
            matrix_list.append(row)

        return jsonify(
            {
                "parameters": available,
                "matrix": matrix_list,
                "sample_size": int(len(subset)),
            }
        )

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

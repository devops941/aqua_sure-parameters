"""
AquaSure Backend - Trends Route
GET /api/trends
Returns yearly WQI trends, grade-by-year breakdown, and top contaminants.
"""

from flask import Blueprint, jsonify
import pandas as pd
from backend.analytics.data_loader import get_dataframe, cache_get, cache_set
from backend.analytics.wqi_calculator import WQI_PARAM_STANDARDS

trends_bp = Blueprint("trends", __name__)


@trends_bp.route("/api/trends", methods=["GET"])
def get_trends():
    try:
        cached = cache_get("trends")
        if cached is not None:
            return jsonify(cached)
        df = get_dataframe()

        # Ensure year column
        if "year" not in df.columns:
            if "sample_date" in df.columns:
                df = df.copy()
                df["year"] = df["sample_date"].dt.year
            else:
                return jsonify({"error": "Year information not available."}), 500

        years = sorted(df["year"].dropna().unique().tolist())

        # --- Yearly WQI & potability ---
        yearly = []
        for yr in years:
            yr_df = df[df["year"] == yr]
            wqi_v = yr_df["wqi"].dropna() if "wqi" in yr_df.columns else pd.Series([], dtype=float)
            potable_col = yr_df["is_potable"] if "is_potable" in yr_df.columns else pd.Series([], dtype=bool)
            total = len(yr_df)
            yearly.append(
                {
                    "year": int(yr),
                    "sample_count": total,
                    "avg_wqi": round(float(wqi_v.mean()), 2) if len(wqi_v) > 0 else None,
                    "median_wqi": round(float(wqi_v.median()), 2) if len(wqi_v) > 0 else None,
                    "potable_pct": round((int((potable_col == True).sum()) / total) * 100, 1) if total > 0 else 0.0,
                }
            )

        # --- Grade distribution by year ---
        grade_by_year = []
        if "wqi_grade" in df.columns:
            for yr in years:
                yr_df = df[df["year"] == yr]
                total = len(yr_df)
                entry = {"year": int(yr)}
                for g in ["A", "B", "C", "D", "E"]:
                    cnt = int((yr_df["wqi_grade"] == g).sum())
                    entry[g] = round((cnt / total) * 100, 1) if total > 0 else 0.0
                grade_by_year.append(entry)

        # --- Top contaminants (% exceeding BIS permissible limit) ---
        top_contaminants = []
        for param, meta in WQI_PARAM_STANDARDS.items():
            if param not in df.columns:
                continue
            col = df[param].dropna()
            valid = col[(col >= meta["min_valid"]) & (col <= meta["max_valid"])]
            if len(valid) == 0:
                continue
            exceed_count = int((valid > meta["standard_permissible"]).sum())
            exceed_pct = round((exceed_count / len(valid)) * 100, 2)
            top_contaminants.append(
                {
                    "parameter": param,
                    "name": meta["name"],
                    "unit": meta["unit"],
                    "standard_permissible": meta["standard_permissible"],
                    "exceed_pct": exceed_pct,
                    "exceed_count": exceed_count,
                    "valid_samples": len(valid),
                }
            )
        top_contaminants.sort(key=lambda x: x["exceed_pct"], reverse=True)

        result = {
            "yearly": yearly,
            "grade_by_year": grade_by_year,
            "top_contaminants": top_contaminants,
        }
        cache_set("trends", result)
        return jsonify(result)

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

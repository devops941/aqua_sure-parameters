"""
AquaSure Backend - Overview Route
GET /api/overview
Returns a high-level summary of the entire Tamil Nadu groundwater dataset.
"""

from flask import Blueprint, jsonify
import numpy as np
from backend.analytics.data_loader import get_dataframe, cache_get, cache_set

overview_bp = Blueprint("overview", __name__)


@overview_bp.route("/api/overview", methods=["GET"])
def get_overview():
    try:
        cached = cache_get("overview")
        if cached is not None:
            return jsonify(cached)
        df = get_dataframe()

        total_samples = int(len(df))

        potable_count = int(df["is_potable"].sum()) if "is_potable" in df.columns else 0
        potable_percent = (
            round((potable_count / total_samples) * 100, 1) if total_samples > 0 else 0.0
        )

        wqi_series = df["wqi"].dropna() if "wqi" in df.columns else None
        avg_wqi = round(float(wqi_series.mean()), 2) if wqi_series is not None and len(wqi_series) > 0 else None
        median_wqi = round(float(wqi_series.median()), 2) if wqi_series is not None and len(wqi_series) > 0 else None

        district_count = int(df["district"].nunique()) if "district" in df.columns else 0

        # Grade distribution (% of total samples)
        grade_distribution = {}
        if "wqi_grade" in df.columns:
            for grade in ["A", "B", "C", "D", "E"]:
                count = int((df["wqi_grade"] == grade).sum())
                grade_distribution[grade] = round((count / total_samples) * 100, 1)

        # Year range
        year_range = "N/A"
        if "sample_date" in df.columns:
            years = df["sample_date"].dt.year.dropna()
            if len(years) > 0:
                min_yr = int(years.min())
                max_yr = int(years.max())
                year_range = f"{min_yr}-{max_yr}"
        elif "year" in df.columns:
            years = df["year"].dropna()
            if len(years) > 0:
                min_yr = int(years.min())
                max_yr = int(years.max())
                year_range = f"{min_yr}-{max_yr}"

        result = {
            "total_samples": total_samples,
            "potable_count": potable_count,
            "potable_percent": potable_percent,
            "avg_wqi": avg_wqi,
            "median_wqi": median_wqi,
            "district_count": district_count,
            "grade_distribution": grade_distribution,
            "year_range": year_range,
        }
        cache_set("overview", result)
        return jsonify(result)

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

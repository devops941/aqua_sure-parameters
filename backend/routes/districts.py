"""
AquaSure Backend - District Routes
GET /api/districts         - List all districts sorted by mean_wqi
GET /api/district/<name>   - Detailed analytics for one district
"""

from flask import Blueprint, jsonify
import numpy as np
import pandas as pd
from backend.analytics.data_loader import get_dataframe, cache_get, cache_set
from backend.analytics.wqi_calculator import WQI_PARAM_STANDARDS

districts_bp = Blueprint("districts", __name__)

NUMERIC_PARAMS = list(WQI_PARAM_STANDARDS.keys())


def _safe_mean(series: pd.Series) -> float | None:
    v = series.dropna()
    return round(float(v.mean()), 3) if len(v) > 0 else None


def _safe_pct(mask: pd.Series, total: int) -> float:
    return round((int(mask.sum()) / total) * 100, 1) if total > 0 else 0.0


@districts_bp.route("/api/districts", methods=["GET"])
def list_districts():
    try:
        cached = cache_get("districts")
        if cached is not None:
            return jsonify(cached)
        df = get_dataframe()
        results = []

        for district, grp in df.groupby("district"):
            total = len(grp)
            wqi_valid = grp["wqi"].dropna() if "wqi" in grp.columns else pd.Series([], dtype=float)

            mean_wqi = round(float(wqi_valid.mean()), 2) if len(wqi_valid) > 0 else None
            median_wqi = round(float(wqi_valid.median()), 2) if len(wqi_valid) > 0 else None

            potable_pct = _safe_pct(grp["is_potable"] == True, total) if "is_potable" in grp.columns else 0.0

            grade_dist = {}
            if "wqi_grade" in grp.columns:
                for g in ["A", "B", "C", "D", "E"]:
                    grade_dist[g] = _safe_pct(grp["wqi_grade"] == g, total)

            # Dominant category
            overall_status = "Unknown"
            if median_wqi is not None:
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

            results.append(
                {
                    "district": district,
                    "total_samples": total,
                    "mean_wqi": mean_wqi,
                    "median_wqi": median_wqi,
                    "potable_pct": potable_pct,
                    "overall_status": overall_status,
                    "grade_distribution": grade_dist,
                }
            )

        results.sort(key=lambda x: (x["mean_wqi"] is None, x["mean_wqi"] or 0))
        cache_set("districts", results)
        return jsonify(results)

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@districts_bp.route("/api/district/<string:name>", methods=["GET"])
def district_detail(name: str):
    try:
        df = get_dataframe()

        # Case-insensitive match
        matches = df[df["district"].str.lower() == name.lower()]
        if matches.empty:
            return jsonify({"error": f"District '{name}' not found."}), 404

        grp = matches
        total = len(grp)

        wqi_valid = grp["wqi"].dropna() if "wqi" in grp.columns else pd.Series([], dtype=float)

        # Basic stats
        stats = {
            "district": grp["district"].iloc[0],
            "total_samples": total,
            "mean_wqi": round(float(wqi_valid.mean()), 2) if len(wqi_valid) > 0 else None,
            "median_wqi": round(float(wqi_valid.median()), 2) if len(wqi_valid) > 0 else None,
            "std_wqi": round(float(wqi_valid.std()), 2) if len(wqi_valid) > 1 else 0.0,
            "min_wqi": round(float(wqi_valid.min()), 2) if len(wqi_valid) > 0 else None,
            "max_wqi": round(float(wqi_valid.max()), 2) if len(wqi_valid) > 0 else None,
            "potable_pct": _safe_pct(grp["is_potable"] == True, total) if "is_potable" in grp.columns else 0.0,
        }

        # Grade distribution
        grade_dist = {}
        if "wqi_grade" in grp.columns:
            for g in ["A", "B", "C", "D", "E"]:
                grade_dist[g] = _safe_pct(grp["wqi_grade"] == g, total)
        stats["grade_distribution"] = grade_dist

        # Yearly trend
        yearly_trend = []
        if "year" in grp.columns:
            for year, yr_grp in grp.groupby("year"):
                yr_wqi = yr_grp["wqi"].dropna()
                potable_col = yr_grp["is_potable"] if "is_potable" in yr_grp.columns else pd.Series([], dtype=bool)
                yearly_trend.append(
                    {
                        "year": int(year),
                        "sample_count": len(yr_grp),
                        "avg_wqi": round(float(yr_wqi.mean()), 2) if len(yr_wqi) > 0 else None,
                        "median_wqi": round(float(yr_wqi.median()), 2) if len(yr_wqi) > 0 else None,
                        "potable_pct": _safe_pct(potable_col == True, len(yr_grp)),
                    }
                )
        stats["yearly_trend"] = sorted(yearly_trend, key=lambda x: x["year"])

        # Parameter averages
        param_avgs = {}
        for param in NUMERIC_PARAMS:
            if param in grp.columns:
                param_avgs[param] = _safe_mean(grp[param])
        stats["parameter_averages"] = param_avgs

        # BIS exceedances
        exceedances = {}
        from backend.analytics.wqi_calculator import WQI_PARAM_STANDARDS as STDS
        for param, meta in STDS.items():
            if param not in grp.columns:
                continue
            col = grp[param].dropna()
            valid = col[(col >= meta["min_valid"]) & (col <= meta["max_valid"])]
            if len(valid) == 0:
                continue
            exceed_perm = int((valid > meta["standard_permissible"]).sum())
            exceed_acc = int((valid > meta["standard_acceptable"]).sum())
            exceedances[param] = {
                "valid_samples": len(valid),
                "exceed_acceptable_count": exceed_acc,
                "exceed_acceptable_pct": round((exceed_acc / len(valid)) * 100, 1),
                "exceed_permissible_count": exceed_perm,
                "exceed_permissible_pct": round((exceed_perm / len(valid)) * 100, 1),
                "standard_acceptable": meta["standard_acceptable"],
                "standard_permissible": meta["standard_permissible"],
                "unit": meta["unit"],
            }
        stats["exceedances"] = exceedances

        return jsonify(stats)

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@districts_bp.route("/api/district-comparison", methods=["GET"])
def district_comparison():
    """GET /api/district-comparison?districts=A,B,C  — Compare up to 4 districts."""
    from flask import request
    try:
        names_raw = request.args.get("districts", "")
        names = [n.strip() for n in names_raw.split(",") if n.strip()]
        if not names:
            return jsonify({"error": "Provide ?districts=Name1,Name2"}), 400
        names = names[:4]

        df = get_dataframe()
        result = []

        for name in names:
            matches = df[df["district"].str.lower() == name.lower()]
            if matches.empty:
                continue
            grp = matches
            total = len(grp)
            wqi_valid = grp["wqi"].dropna() if "wqi" in grp.columns else pd.Series([], dtype=float)

            param_avgs = {}
            for param in NUMERIC_PARAMS:
                if param in grp.columns:
                    param_avgs[param] = _safe_mean(grp[param])

            mean_wqi = round(float(wqi_valid.mean()), 2) if len(wqi_valid) > 0 else None
            potable_pct = _safe_pct(grp["is_potable"] == True, total) if "is_potable" in grp.columns else 0.0

            overall_status = "Unknown"
            if mean_wqi is not None:
                if mean_wqi <= 25:
                    overall_status = "Excellent"
                elif mean_wqi <= 50:
                    overall_status = "Good"
                elif mean_wqi <= 75:
                    overall_status = "Poor"
                elif mean_wqi <= 100:
                    overall_status = "Very Poor"
                else:
                    overall_status = "Unsuitable for Drinking"

            result.append({
                "district": grp["district"].iloc[0],
                "total_samples": total,
                "mean_wqi": mean_wqi,
                "potable_pct": potable_pct,
                "overall_status": overall_status,
                "parameter_averages": param_avgs,
            })

        return jsonify(result)

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

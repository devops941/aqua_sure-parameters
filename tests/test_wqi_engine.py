"""
Unit tests for src/wqi_engine.py
- compute_sample_wqi: known-input / known-output for ideal and polluted water
- Category boundary mapping to correct grade labels
- Edge cases: missing params, single param, out-of-range values
"""

import sys
import os
import math
import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.wqi_engine import compute_sample_wqi, calculate_wqi_vectorized


# ---------------------------------------------------------------------------
# Helper: build a pd.Series from a dict of water quality values
# ---------------------------------------------------------------------------
def make_row(**kwargs) -> pd.Series:
    return pd.Series(kwargs)


# Realistic "ideal" water: pH exactly 7.0, all other params at BIS ideal (0 is
# the ideal for non-pH params but that's unphysical; use very low values instead).
# pH=7.0 → qi_ph = (|7-7|/1.5)*100 = 0
# tds=50  → qi_tds = (50/500)*100 = 10
# ec=75   → qi_ec = (75/750)*100 = 10
# hardness=20 → qi_hard = (20/200)*100 = 10
# ca=7.5  → qi_ca = (7.5/75)*100 = 10
# mg=3    → qi_mg = (3/30)*100 = 10
# cl=25   → qi_cl = (25/250)*100 = 10
# so4=20  → qi_so4 = (20/200)*100 = 10
# no3=4.5 → qi_no3 = (4.5/45)*100 = 10
# f=0.1   → qi_f = (0.1/1)*100 = 10
# total_weight = 36; each qi=10, weighted sum = 10 → Grade A
IDEAL_SAMPLE = dict(
    ph=7.0, tds=50.0, ec=75.0, hardness=20.0,
    ca=7.5, mg=3.0, cl=25.0, so4=20.0, no3=4.5, f=0.1
)

# Polluted water: all params well above BIS permissible limits
POLLUTED_SAMPLE = dict(
    ph=5.5,       # < 6.5 → critical breach; qi_ph = (|5.5-7|/1.5)*100 = 100
    tds=5000.0,   # >> 2000 → critical breach; qi = (5000/500)*100 = 1000
    ec=5000.0,    # qi = (5000/750)*100 ≈ 666.7
    hardness=2000.0,  # qi = (2000/200)*100 = 1000
    ca=500.0,     # qi = (500/75)*100 ≈ 666.7
    mg=200.0,     # qi = (200/30)*100 ≈ 666.7
    cl=2000.0,    # qi = (2000/250)*100 = 800
    so4=1000.0,   # qi = (1000/200)*100 = 500
    no3=100.0,    # > 45 → critical breach; qi = (100/45)*100 ≈ 222.2
    f=5.0,        # > 1.5 → critical breach; qi = (5/1)*100 = 500
)


class TestComputeSampleWQI:
    def test_ideal_water_grade_a(self):
        """Near-ideal water should produce Grade A (WQI <= 25)."""
        result = compute_sample_wqi(make_row(**IDEAL_SAMPLE))
        assert result["wqi"] is not None and not math.isnan(result["wqi"])
        assert result["wqi"] <= 25.0, (
            f"Expected ideal water WQI <= 25, got {result['wqi']}"
        )
        assert result["grade"] == "A", f"Expected Grade A, got {result['grade']}"
        assert result["category"] == "Excellent"
        assert result["potability"] == "Potable"
        assert result["is_potable"] is True

    def test_ideal_water_wqi_exact_value(self):
        """
        Verify exact WQI for the IDEAL_SAMPLE.

        pH = 7.0 → qi_ph = (|7 - 7| / 1.5) * 100 = 0.0  (ideal is 7.0)
        All other params are at 10% of their standard_acceptable → qi = 10.0

        Since pH qi = 0 (not 10), and pH has weight 4/36 of the total,
        the weighted sum is NOT 10.0 but 8.89:
          sum = (0*4 + 10*5 + 10*3 + 10*3 + 10*2 + 10*2 + 10*3 + 10*4 + 10*5 + 10*5) / 36
              = (0 + 50+30+30+20+20+30+40+50+50) / 36 = 320 / 36 ≈ 8.89
        """
        result = compute_sample_wqi(make_row(**IDEAL_SAMPLE))
        expected = 320.0 / 36.0  # ≈ 8.888...
        assert abs(result["wqi"] - expected) < 0.1, (
            f"Expected WQI ≈ {expected:.2f} for ideal sample, got {result['wqi']}"
        )

    def test_polluted_water_grade_e(self):
        """Severely polluted water should produce Grade E (WQI > 100)."""
        result = compute_sample_wqi(make_row(**POLLUTED_SAMPLE))
        assert result["wqi"] is not None and not math.isnan(result["wqi"])
        assert result["wqi"] > 100.0, (
            f"Expected polluted WQI > 100, got {result['wqi']}"
        )
        assert result["grade"] == "E", f"Expected Grade E, got {result['grade']}"
        assert result["category"] == "Unsuitable for Drinking"
        assert result["is_potable"] is False

    def test_polluted_water_has_violations(self):
        """Polluted sample should report parameter violations."""
        result = compute_sample_wqi(make_row(**POLLUTED_SAMPLE))
        assert len(result["violations"]) > 0, "Expected violations for polluted water"

    def test_ideal_water_no_violations(self):
        """Ideal water within all limits should have no violations."""
        result = compute_sample_wqi(make_row(**IDEAL_SAMPLE))
        assert result["violations"] == [], (
            f"Expected no violations, got: {result['violations']}"
        )

    def test_no_params_returns_nan(self):
        """Row with no valid WQI params should return NaN WQI."""
        result = compute_sample_wqi(make_row(station_code="X", latitude=10.0))
        assert math.isnan(result["wqi"])
        assert result["grade"] == "N/A"
        assert result["active_param_count"] == 0

    def test_single_param_ph_only(self):
        """Single valid parameter (pH) should still compute a WQI."""
        result = compute_sample_wqi(make_row(ph=7.0))
        assert not math.isnan(result["wqi"])
        assert result["active_param_count"] == 1

    def test_out_of_range_param_ignored(self):
        """Parameter value outside physical bounds should be ignored."""
        # pH of 15 is outside max_valid=11.5
        result_no_ph = compute_sample_wqi(make_row(ph=15.0, tds=50.0))
        result_with_ph = compute_sample_wqi(make_row(ph=7.0, tds=50.0))
        # Out-of-range pH should not be used; only tds should be active
        assert result_no_ph["active_param_count"] == 1  # only tds
        assert result_with_ph["active_param_count"] == 2  # ph + tds

    def test_critical_breach_ph_low(self):
        """pH < 6.5 marks a critical breach even with low WQI score."""
        result = compute_sample_wqi(make_row(ph=6.0))
        assert result["is_potable"] is False

    def test_critical_breach_nitrate(self):
        """NO3 > 45 triggers non-potable even if other params are OK."""
        sample = dict(IDEAL_SAMPLE)
        sample["no3"] = 50.0  # exceed limit
        result = compute_sample_wqi(make_row(**sample))
        assert result["is_potable"] is False

    def test_critical_breach_fluoride(self):
        """F > 1.5 triggers critical breach."""
        sample = dict(IDEAL_SAMPLE)
        sample["f"] = 2.0
        result = compute_sample_wqi(make_row(**sample))
        assert result["is_potable"] is False

    def test_critical_breach_tds(self):
        """TDS > 2000 triggers critical breach."""
        sample = dict(IDEAL_SAMPLE)
        sample["tds"] = 2500.0
        result = compute_sample_wqi(make_row(**sample))
        assert result["is_potable"] is False

    def test_return_dict_has_required_keys(self):
        """Return dict must always contain required keys."""
        result = compute_sample_wqi(make_row(**IDEAL_SAMPLE))
        required = {"wqi", "category", "grade", "potability", "is_potable",
                    "active_param_count", "violations"}
        assert required.issubset(set(result.keys()))

    def test_nan_param_value_ignored(self):
        """NaN values should be treated as missing and skipped."""
        result = compute_sample_wqi(make_row(ph=float("nan"), tds=50.0))
        assert result["active_param_count"] == 1  # only tds


class TestCategoryBoundaries:
    """Verify that WQI scores map to the correct grade labels."""

    def _wqi_for_score_via_params(self, target_wqi: float) -> dict:
        """
        Produce a row that hits approximately target_wqi using only TDS.
        qi_tds = (tds / 500) * 100 = target_wqi  → tds = target_wqi * 5
        With a single param, weight_norm = 1.0, so wqi = qi_tds.
        """
        tds_val = target_wqi * 5.0
        # Clamp to valid range (0-70000)
        tds_val = min(tds_val, 60000.0)
        return compute_sample_wqi(make_row(tds=tds_val))

    def test_grade_a_boundary(self):
        """WQI = 15 → Grade A (Excellent, 0-25)."""
        result = self._wqi_for_score_via_params(15.0)
        assert result["grade"] == "A", f"WQI={result['wqi']} → expected A, got {result['grade']}"
        assert result["category"] == "Excellent"

    def test_grade_b_boundary(self):
        """WQI = 40 → Grade B (Good, 26-50)."""
        result = self._wqi_for_score_via_params(40.0)
        assert result["grade"] == "B", f"WQI={result['wqi']} → expected B, got {result['grade']}"
        assert result["category"] == "Good"

    def test_grade_c_boundary(self):
        """WQI = 60 → Grade C (Poor, 51-75)."""
        result = self._wqi_for_score_via_params(60.0)
        assert result["grade"] == "C", f"WQI={result['wqi']} → expected C, got {result['grade']}"
        assert result["category"] == "Poor"

    def test_grade_d_boundary(self):
        """WQI = 90 → Grade D (Very Poor, 76-100)."""
        result = self._wqi_for_score_via_params(90.0)
        assert result["grade"] == "D", f"WQI={result['wqi']} → expected D, got {result['grade']}"
        assert result["category"] == "Very Poor"

    def test_grade_e_boundary(self):
        """WQI = 150 → Grade E (Unsuitable, >100)."""
        result = self._wqi_for_score_via_params(150.0)
        assert result["grade"] == "E", f"WQI={result['wqi']} → expected E, got {result['grade']}"
        assert result["category"] == "Unsuitable for Drinking"


class TestCalculateWQIVectorized:
    """Tests for the vectorized DataFrame-level WQI calculation."""

    def test_vectorized_adds_wqi_column(self):
        rows = [IDEAL_SAMPLE, POLLUTED_SAMPLE]
        df = pd.DataFrame(rows)
        result = calculate_wqi_vectorized(df)
        assert "wqi" in result.columns
        assert "wqi_grade" in result.columns
        assert "wqi_category" in result.columns
        assert "is_potable" in result.columns

    def test_vectorized_ideal_water(self):
        df = pd.DataFrame([IDEAL_SAMPLE])
        result = calculate_wqi_vectorized(df)
        assert result["wqi_grade"].iloc[0] == "A"
        assert result["is_potable"].iloc[0] is True or result["is_potable"].iloc[0] == True

    def test_vectorized_polluted_water(self):
        df = pd.DataFrame([POLLUTED_SAMPLE])
        result = calculate_wqi_vectorized(df)
        assert result["wqi_grade"].iloc[0] == "E"
        assert result["is_potable"].iloc[0] is False or result["is_potable"].iloc[0] == False

    def test_vectorized_preserves_row_count(self):
        rows = [IDEAL_SAMPLE, POLLUTED_SAMPLE, dict(ph=7.5, tds=300.0)]
        df = pd.DataFrame(rows)
        result = calculate_wqi_vectorized(df)
        assert len(result) == len(rows)

"""
Tests for src/config.py
- 38 Tamil Nadu districts present
- BIS standards keys exist for the 10 WQI parameters
- Weights are sane (positive integers summing within expected bounds)
- WQI categories cover the full scale without gaps
"""

import sys
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import TN_38_DISTRICTS, WQI_PARAM_STANDARDS, WQI_CATEGORIES

EXPECTED_PARAMS = {"ph", "tds", "ec", "hardness", "ca", "mg", "cl", "so4", "no3", "f"}
REQUIRED_PARAM_KEYS = {
    "name", "unit", "standard_acceptable", "standard_permissible",
    "ideal_value", "weight", "min_valid", "max_valid"
}


class TestDistrictList:
    def test_exactly_38_districts(self):
        """Tamil Nadu has 38 administrative districts (as of 2019 reorganisation)."""
        actual = len(TN_38_DISTRICTS)
        assert actual == 38, (
            f"TN_38_DISTRICTS has {actual} entries (expected 38)."
        )

    def test_thoothukudi_present(self):
        """Thoothukudi (Tuticorin) is the 38th district — regression guard."""
        assert "Thoothukudi" in TN_38_DISTRICTS

    def test_no_duplicate_districts(self):
        """District names must be unique."""
        assert len(TN_38_DISTRICTS) == len(set(TN_38_DISTRICTS)), (
            "Duplicate district names found"
        )

    def test_expected_districts_present(self):
        """Spot-check a selection of known Tamil Nadu districts."""
        expected = {
            "Chennai", "Coimbatore", "Madurai", "Tirunelveli",
            "Salem", "Erode", "Vellore", "Thanjavur", "Kanyakumari", "Nilgiris"
        }
        missing = expected - set(TN_38_DISTRICTS)
        assert not missing, f"These expected districts are missing: {missing}"

    def test_all_entries_are_strings(self):
        for d in TN_38_DISTRICTS:
            assert isinstance(d, str) and len(d) > 0, (
                f"Non-string or empty district entry: {d!r}"
            )


class TestWQIParamStandards:
    def test_exactly_10_wqi_parameters(self):
        """WQI uses exactly 10 BIS parameters."""
        assert set(WQI_PARAM_STANDARDS.keys()) == EXPECTED_PARAMS, (
            f"Parameter mismatch. Got: {set(WQI_PARAM_STANDARDS.keys())}"
        )

    def test_each_param_has_required_keys(self):
        for param, meta in WQI_PARAM_STANDARDS.items():
            missing = REQUIRED_PARAM_KEYS - set(meta.keys())
            assert not missing, (
                f"Parameter '{param}' is missing keys: {missing}"
            )

    def test_weights_are_positive_integers(self):
        for param, meta in WQI_PARAM_STANDARDS.items():
            w = meta["weight"]
            assert isinstance(w, int) and w > 0, (
                f"Parameter '{param}' has invalid weight: {w}"
            )

    def test_total_weight_sum_is_36(self):
        """Sum of raw weights should be 36 (4+5+3+3+2+2+3+4+5+5)."""
        total = sum(meta["weight"] for meta in WQI_PARAM_STANDARDS.values())
        assert total == 36, f"Expected weight sum 36, got {total}"

    def test_valid_range_is_sensible(self):
        """min_valid must be less than max_valid for every parameter."""
        for param, meta in WQI_PARAM_STANDARDS.items():
            assert meta["min_valid"] < meta["max_valid"], (
                f"Parameter '{param}': min_valid >= max_valid"
            )

    def test_acceptable_limit_within_valid_range(self):
        """standard_acceptable must be within [min_valid, max_valid]."""
        for param, meta in WQI_PARAM_STANDARDS.items():
            assert meta["min_valid"] <= meta["standard_acceptable"] <= meta["max_valid"], (
                f"Parameter '{param}': standard_acceptable out of valid range"
            )

    def test_ph_ideal_value_is_7(self):
        assert WQI_PARAM_STANDARDS["ph"]["ideal_value"] == 7.0

    def test_nitrate_permissible_equals_acceptable(self):
        """NO3 BIS permissible and acceptable limits are both 45 mg/L."""
        no3 = WQI_PARAM_STANDARDS["no3"]
        assert no3["standard_acceptable"] == no3["standard_permissible"] == 45.0


class TestWQICategories:
    def test_five_categories(self):
        assert len(WQI_CATEGORIES) == 5

    def test_grades_are_a_through_e(self):
        grades = [cat["grade"] for cat in WQI_CATEGORIES]
        assert grades == ["A", "B", "C", "D", "E"]

    def test_grade_a_starts_at_zero(self):
        assert WQI_CATEGORIES[0]["range"][0] == 0

    def test_grade_e_has_infinite_upper(self):
        import math
        assert math.isinf(WQI_CATEGORIES[-1]["range"][1])

    def test_categories_have_required_fields(self):
        for cat in WQI_CATEGORIES:
            for key in ("grade", "category", "range", "potability"):
                assert key in cat, f"Category '{cat.get('grade')}' missing key '{key}'"

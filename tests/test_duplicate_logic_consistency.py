"""
Consistency test: src/wqi_engine.compute_sample_wqi vs
backend/analytics/wqi_calculator.calculate_wqi

Both are independent copies of the same WAWQI formula. This test feeds
identical samples to both implementations and asserts their numerical
outputs agree within a tolerance of 0.5 WQI points.

A failure here means the two codebases have drifted and that is a
real finding — do NOT silence the assertion.
"""

import sys
import os
import math
import pytest
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.wqi_engine import compute_sample_wqi
from backend.analytics.wqi_calculator import calculate_wqi

# Tolerance for numeric agreement (WQI points)
TOLERANCE = 0.5


def _make_row(**kwargs) -> pd.Series:
    return pd.Series(kwargs)


def _src_wqi(params: dict) -> float:
    """Call src/wqi_engine and return the WQI float."""
    result = compute_sample_wqi(_make_row(**params))
    return result["wqi"]


def _backend_wqi(params: dict) -> float:
    """Call backend/analytics/wqi_calculator and return the WQI float."""
    result = calculate_wqi(params)
    return result["wqi"]


# ---------------------------------------------------------------------------
# Test samples covering different quality tiers
# ---------------------------------------------------------------------------
TEST_SAMPLES = {
    "ideal_water": dict(
        ph=7.0, tds=50.0, ec=75.0, hardness=20.0,
        ca=7.5, mg=3.0, cl=25.0, so4=20.0, no3=4.5, f=0.1
    ),
    "borderline_grade_a_b": dict(
        ph=7.5, tds=200.0, ec=250.0, hardness=100.0,
        ca=30.0, mg=12.0, cl=100.0, so4=80.0, no3=18.0, f=0.4
    ),
    "moderate_quality": dict(
        ph=7.8, tds=400.0, ec=600.0, hardness=180.0,
        ca=60.0, mg=25.0, cl=200.0, so4=160.0, no3=30.0, f=0.8
    ),
    "poor_quality": dict(
        ph=8.3, tds=800.0, ec=1200.0, hardness=350.0,
        ca=100.0, mg=50.0, cl=500.0, so4=250.0, no3=40.0, f=1.2
    ),
    "very_poor_quality": dict(
        ph=6.3, tds=1500.0, ec=2000.0, hardness=500.0,
        ca=150.0, mg=80.0, cl=800.0, so4=350.0, no3=44.0, f=1.4
    ),
    "polluted_water": dict(
        ph=5.5, tds=5000.0, ec=5000.0, hardness=2000.0,
        ca=500.0, mg=200.0, cl=2000.0, so4=1000.0, no3=100.0, f=5.0
    ),
    "partial_params_no3_f_only": dict(
        no3=20.0, f=0.5
    ),
    "partial_params_ph_tds_only": dict(
        ph=7.2, tds=300.0
    ),
    "critical_fluoride": dict(
        ph=7.0, tds=200.0, f=2.5
    ),
    "critical_nitrate": dict(
        ph=7.0, tds=200.0, no3=60.0
    ),
}


@pytest.mark.parametrize("label,params", TEST_SAMPLES.items())
def test_wqi_implementations_agree(label: str, params: dict):
    """
    Both implementations must produce the same WQI (within TOLERANCE).
    """
    src_result = _src_wqi(params)
    backend_result = _backend_wqi(params)

    # Both should be NaN/None or both should be numeric
    src_is_nan = src_result is None or (isinstance(src_result, float) and math.isnan(src_result))
    backend_is_nan = backend_result is None

    if src_is_nan and backend_is_nan:
        return  # Both agree: no valid params

    assert not src_is_nan, (
        f"[{label}] src returned NaN but backend returned {backend_result}"
    )
    assert not backend_is_nan, (
        f"[{label}] backend returned None but src returned {src_result}"
    )

    diff = abs(float(src_result) - float(backend_result))
    assert diff <= TOLERANCE, (
        f"[{label}] WQI DISAGREEMENT: src={src_result}, backend={backend_result}, "
        f"diff={diff:.4f} (tolerance={TOLERANCE})\n"
        f"  Input params: {params}"
    )


@pytest.mark.parametrize("label,params", TEST_SAMPLES.items())
def test_grade_implementations_agree(label: str, params: dict):
    """
    Both implementations must assign the same grade letter.
    """
    src_res = compute_sample_wqi(_make_row(**params))
    backend_res = calculate_wqi(params)

    src_grade = src_res["grade"]
    backend_grade = backend_res["grade"]

    if src_grade == "N/A" and backend_grade == "N/A":
        return  # Both agree: no valid params

    assert src_grade == backend_grade, (
        f"[{label}] GRADE DISAGREEMENT: src={src_grade}, backend={backend_grade}\n"
        f"  src_wqi={src_res['wqi']}, backend_wqi={backend_res['wqi']}\n"
        f"  Input params: {params}"
    )


@pytest.mark.parametrize("label,params", TEST_SAMPLES.items())
def test_potability_implementations_agree(label: str, params: dict):
    """
    Both implementations must agree on is_potable flag.
    """
    src_res = compute_sample_wqi(_make_row(**params))
    backend_res = calculate_wqi(params)

    # Skip if no valid params in either
    src_wqi = src_res["wqi"]
    backend_wqi = backend_res["wqi"]
    if (src_wqi is None or (isinstance(src_wqi, float) and math.isnan(src_wqi))) \
            and backend_wqi is None:
        return

    assert src_res["is_potable"] == backend_res["is_potable"], (
        f"[{label}] IS_POTABLE DISAGREEMENT: src={src_res['is_potable']}, "
        f"backend={backend_res['is_potable']}\n"
        f"  src_wqi={src_res['wqi']}, backend_wqi={backend_res['wqi']}\n"
        f"  Input params: {params}"
    )

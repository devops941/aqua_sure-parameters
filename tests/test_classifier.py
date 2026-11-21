"""
Tests for src/potability_classifier.py
Tests load_or_train_model() and predict_single_sample() using the pre-trained
Random Forest model at data/models/potability_rf_model.joblib.

All tests are skipped gracefully if the model file is not present.
"""

import sys
import os
import math
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

MODEL_PATH = os.path.join(PROJECT_ROOT, "data", "models", "potability_rf_model.joblib")
MODEL_AVAILABLE = os.path.exists(MODEL_PATH)

SKIP_REASON = f"Model file not found at {MODEL_PATH}. Run train_potability_model() first."


# A realistic potable-quality sample
POTABLE_SAMPLE = {
    "ph": 7.2,
    "tds": 250.0,
    "ec": 400.0,
    "hardness": 120.0,
    "ca": 40.0,
    "mg": 15.0,
    "cl": 100.0,
    "so4": 80.0,
    "no3": 10.0,
    "f": 0.4
}

# A clearly non-potable sample
NON_POTABLE_SAMPLE = {
    "ph": 5.5,
    "tds": 4000.0,
    "ec": 5000.0,
    "hardness": 1500.0,
    "ca": 300.0,
    "mg": 150.0,
    "cl": 1500.0,
    "so4": 800.0,
    "no3": 90.0,
    "f": 4.0
}


@pytest.mark.skipif(not MODEL_AVAILABLE, reason=SKIP_REASON)
class TestLoadModel:
    def test_load_model_returns_dict(self):
        from src.potability_classifier import load_or_train_model
        artifact = load_or_train_model()
        assert isinstance(artifact, dict), (
            f"Expected dict artifact, got {type(artifact)}"
        )

    def test_artifact_has_pipeline(self):
        from src.potability_classifier import load_or_train_model
        artifact = load_or_train_model()
        assert "pipeline" in artifact, f"'pipeline' missing from artifact: {artifact.keys()}"

    def test_artifact_has_features(self):
        from src.potability_classifier import load_or_train_model
        artifact = load_or_train_model()
        assert "features" in artifact
        features = artifact["features"]
        assert isinstance(features, list) and len(features) > 0

    def test_artifact_has_expected_metrics(self):
        from src.potability_classifier import load_or_train_model
        artifact = load_or_train_model()
        for key in ("accuracy", "roc_auc"):
            if key in artifact:
                val = artifact[key]
                assert 0.0 <= val <= 1.0, f"{key}={val} out of [0,1]"


@pytest.mark.skipif(not MODEL_AVAILABLE, reason=SKIP_REASON)
class TestPredictSingleSample:
    def test_returns_dict(self):
        from src.potability_classifier import predict_single_sample
        result = predict_single_sample(POTABLE_SAMPLE)
        assert isinstance(result, dict)

    def test_result_has_required_keys(self):
        from src.potability_classifier import predict_single_sample
        result = predict_single_sample(POTABLE_SAMPLE)
        required = {"is_potable", "potability_confidence", "potability_probability", "verdict"}
        missing = required - set(result.keys())
        assert not missing, f"Result missing keys: {missing}"

    def test_probability_in_range(self):
        from src.potability_classifier import predict_single_sample
        result = predict_single_sample(POTABLE_SAMPLE)
        prob = result["potability_probability"]
        assert 0.0 <= prob <= 1.0, f"probability out of range: {prob}"

    def test_confidence_in_range(self):
        from src.potability_classifier import predict_single_sample
        result = predict_single_sample(POTABLE_SAMPLE)
        conf = result["potability_confidence"]
        assert 0.0 <= conf <= 1.0, f"confidence out of range: {conf}"

    def test_is_potable_is_bool(self):
        from src.potability_classifier import predict_single_sample
        result = predict_single_sample(POTABLE_SAMPLE)
        assert isinstance(result["is_potable"], bool)

    def test_verdict_is_string(self):
        from src.potability_classifier import predict_single_sample
        result = predict_single_sample(POTABLE_SAMPLE)
        assert isinstance(result["verdict"], str) and len(result["verdict"]) > 0

    def test_non_potable_sample_prediction(self):
        """Non-potable sample should return a valid prediction without crashing."""
        from src.potability_classifier import predict_single_sample
        result = predict_single_sample(NON_POTABLE_SAMPLE)
        assert isinstance(result, dict)
        assert "is_potable" in result
        assert "potability_probability" in result

    def test_missing_params_handled_gracefully(self):
        """Sample with only some params (imputer fills rest) should not crash."""
        from src.potability_classifier import predict_single_sample
        partial = {"ph": 7.0, "tds": 300.0}
        result = predict_single_sample(partial)
        assert isinstance(result, dict)
        assert "is_potable" in result

    def test_empty_sample_handled_gracefully(self):
        """Fully empty sample (all imputed) should not crash."""
        from src.potability_classifier import predict_single_sample
        result = predict_single_sample({})
        assert isinstance(result, dict)
        assert "is_potable" in result

    def test_confidence_consistency_with_is_potable(self):
        """
        confidence = prob if potable else (1 - prob).
        When is_potable=True, confidence == prob.
        When is_potable=False, confidence == 1 - prob.
        """
        from src.potability_classifier import predict_single_sample
        for sample in (POTABLE_SAMPLE, NON_POTABLE_SAMPLE):
            result = predict_single_sample(sample)
            prob = result["potability_probability"]
            conf = result["potability_confidence"]
            is_potable = result["is_potable"]
            if is_potable:
                expected_conf = round(prob, 4)
            else:
                expected_conf = round(1.0 - prob, 4)
            assert abs(conf - expected_conf) < 1e-3, (
                f"confidence mismatch: conf={conf}, prob={prob}, "
                f"is_potable={is_potable}, expected_conf={expected_conf}"
            )

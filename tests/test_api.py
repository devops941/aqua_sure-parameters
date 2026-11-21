"""
Flask API endpoint tests via test_client.
Tests health, overview, districts, trends, and calculate-wqi endpoints.
"""

import sys
import os
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.data}"
        )

    def test_health_returns_json(self, client):
        response = client.get("/api/health")
        data = response.get_json()
        assert data is not None, "Response is not valid JSON"

    def test_health_status_field(self, client):
        response = client.get("/api/health")
        data = response.get_json()
        # Either "ok" (data loaded) or "error" (data not found) — both are valid
        assert "status" in data, f"'status' key missing from health response: {data}"
        assert data["status"] in ("ok", "error"), (
            f"Unexpected status value: {data['status']}"
        )

    def test_health_ok_has_rows_loaded(self, client):
        response = client.get("/api/health")
        data = response.get_json()
        if data.get("status") == "ok":
            assert "rows_loaded" in data, "'rows_loaded' missing from healthy response"
            assert isinstance(data["rows_loaded"], int) and data["rows_loaded"] > 0


class TestOverviewEndpoint:
    def test_overview_returns_200(self, client):
        response = client.get("/api/overview")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.data}"
        )

    def test_overview_returns_json(self, client):
        response = client.get("/api/overview")
        data = response.get_json()
        assert data is not None

    def test_overview_has_expected_fields(self, client):
        response = client.get("/api/overview")
        data = response.get_json()
        if "error" in data:
            pytest.skip(f"Data not available: {data['error']}")
        expected_fields = {
            "total_samples", "potable_count", "potable_percent",
            "avg_wqi", "district_count"
        }
        missing = expected_fields - set(data.keys())
        assert not missing, f"Overview response missing fields: {missing}"

    def test_overview_total_samples_positive(self, client):
        response = client.get("/api/overview")
        data = response.get_json()
        if "error" in data:
            pytest.skip(f"Data not available: {data['error']}")
        assert data["total_samples"] > 0

    def test_overview_potable_percent_in_range(self, client):
        response = client.get("/api/overview")
        data = response.get_json()
        if "error" in data:
            pytest.skip(f"Data not available: {data['error']}")
        pct = data["potable_percent"]
        assert 0.0 <= pct <= 100.0, f"potable_percent out of range: {pct}"


class TestDistrictsEndpoint:
    def test_districts_returns_200(self, client):
        response = client.get("/api/districts")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.data}"
        )

    def test_districts_returns_json_list(self, client):
        response = client.get("/api/districts")
        data = response.get_json()
        assert data is not None
        # Either a list of districts or an error dict
        if isinstance(data, dict) and "error" in data:
            pytest.skip(f"Data not available: {data['error']}")
        assert isinstance(data, list), f"Expected list, got {type(data)}"

    def test_districts_list_not_empty(self, client):
        response = client.get("/api/districts")
        data = response.get_json()
        if isinstance(data, dict) and "error" in data:
            pytest.skip(f"Data not available: {data['error']}")
        assert len(data) > 0

    def test_districts_each_entry_has_district_key(self, client):
        response = client.get("/api/districts")
        data = response.get_json()
        if isinstance(data, dict) and "error" in data:
            pytest.skip(f"Data not available: {data['error']}")
        for entry in data[:5]:  # check first 5 to keep test fast
            assert "district" in entry, f"Entry missing 'district': {entry}"
            assert "mean_wqi" in entry or "median_wqi" in entry, (
                f"Entry missing WQI fields: {entry}"
            )


class TestTrendsEndpoint:
    def test_trends_returns_200(self, client):
        response = client.get("/api/trends")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.data}"
        )

    def test_trends_returns_json(self, client):
        response = client.get("/api/trends")
        data = response.get_json()
        assert data is not None

    def test_trends_has_yearly_field(self, client):
        response = client.get("/api/trends")
        data = response.get_json()
        if isinstance(data, dict) and "error" in data:
            pytest.skip(f"Data not available: {data['error']}")
        assert "yearly" in data, f"'yearly' missing from trends: {data.keys()}"
        assert isinstance(data["yearly"], list)


class TestCalculateWQIEndpoint:
    """POST /api/calculate-wqi tests."""

    SAMPLE_PAYLOAD = {
        "ph": 7.2,
        "tds": 450.0,
        "ec": 650.0,
        "hardness": 180.0,
        "ca": 55.0,
        "mg": 20.0,
        "cl": 180.0,
        "so4": 150.0,
        "no3": 25.0,
        "f": 0.6
    }

    def test_calculate_wqi_returns_200(self, client):
        response = client.post(
            "/api/calculate-wqi",
            data=json.dumps(self.SAMPLE_PAYLOAD),
            content_type="application/json"
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.data}"
        )

    def test_calculate_wqi_returns_wqi_value(self, client):
        response = client.post(
            "/api/calculate-wqi",
            data=json.dumps(self.SAMPLE_PAYLOAD),
            content_type="application/json"
        )
        data = response.get_json()
        assert "wqi" in data, f"'wqi' missing from response: {data}"
        assert data["wqi"] is not None
        assert isinstance(data["wqi"], (int, float))

    def test_calculate_wqi_returns_grade(self, client):
        response = client.post(
            "/api/calculate-wqi",
            data=json.dumps(self.SAMPLE_PAYLOAD),
            content_type="application/json"
        )
        data = response.get_json()
        assert "grade" in data
        assert data["grade"] in ("A", "B", "C", "D", "E")

    def test_calculate_wqi_returns_potability(self, client):
        response = client.post(
            "/api/calculate-wqi",
            data=json.dumps(self.SAMPLE_PAYLOAD),
            content_type="application/json"
        )
        data = response.get_json()
        assert "potability" in data
        assert isinstance(data["potability"], str) and len(data["potability"]) > 0

    def test_calculate_wqi_returns_violations_list(self, client):
        response = client.post(
            "/api/calculate-wqi",
            data=json.dumps(self.SAMPLE_PAYLOAD),
            content_type="application/json"
        )
        data = response.get_json()
        assert "violations" in data
        assert isinstance(data["violations"], list)

    def test_calculate_wqi_returns_sub_indices(self, client):
        response = client.post(
            "/api/calculate-wqi",
            data=json.dumps(self.SAMPLE_PAYLOAD),
            content_type="application/json"
        )
        data = response.get_json()
        assert "sub_indices" in data
        assert isinstance(data["sub_indices"], dict)

    def test_calculate_wqi_wqi_in_range(self, client):
        """WQI for a moderate-quality sample should be a positive finite number."""
        response = client.post(
            "/api/calculate-wqi",
            data=json.dumps(self.SAMPLE_PAYLOAD),
            content_type="application/json"
        )
        data = response.get_json()
        wqi = data["wqi"]
        assert wqi > 0, f"Expected positive WQI, got {wqi}"

    def test_calculate_wqi_empty_body_returns_400(self, client):
        response = client.post(
            "/api/calculate-wqi",
            data=json.dumps({}),
            content_type="application/json"
        )
        assert response.status_code == 400, (
            f"Expected 400 for empty body, got {response.status_code}"
        )

    def test_calculate_wqi_invalid_params_returns_400(self, client):
        """Unknown-only params should return 400."""
        response = client.post(
            "/api/calculate-wqi",
            data=json.dumps({"invalid_param": 123}),
            content_type="application/json"
        )
        assert response.status_code == 400

    def test_calculate_wqi_partial_params_ok(self, client):
        """Only a subset of params should still return a valid WQI."""
        payload = {"ph": 7.0, "tds": 300.0}
        response = client.post(
            "/api/calculate-wqi",
            data=json.dumps(payload),
            content_type="application/json"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "wqi" in data and data["wqi"] is not None

    def test_404_for_unknown_endpoint(self, client):
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_parameters_endpoint(self, client):
        """GET /api/parameters should return 200 with list of BIS standards."""
        response = client.get("/api/parameters")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 10, f"Expected 10 parameters, got {len(data)}"

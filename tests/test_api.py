from decimal import Decimal

from fastapi.testclient import TestClient

from regional_medical_risk.api import _json_row, app, get_repository


class FakeAccessibilityRepository:
    def latest_summary(self):
        return {
            "run_id": "run-1",
            "method": "2SFCA",
            "demand_point_count": 3_559,
            "senior_coverage_pct": 96.43,
        }

    def list_regions(self):
        return "run-1", [{"region_code": "11110", "region_name": "종로구"}]

    def get_region(self, region_code):
        if region_code != "11110":
            return None
        return {
            "run_id": "run-1",
            "region_code": region_code,
            "region_name": "종로구",
            "demand_points": [{"demand_id": "1101053", "within_threshold": True}],
        }


def _fake_repository():
    return FakeAccessibilityRepository()


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_accessibility_endpoints_return_latest_run():
    app.dependency_overrides[get_repository] = _fake_repository
    try:
        with TestClient(app) as client:
            latest = client.get("/api/v1/accessibility/latest")
            regions = client.get("/api/v1/accessibility/regions")
            detail = client.get("/api/v1/accessibility/regions/11110")
    finally:
        app.dependency_overrides.clear()

    assert latest.status_code == 200
    assert latest.json()["senior_coverage_pct"] == 96.43
    assert regions.json()["count"] == 1
    assert detail.json()["demand_points"][0]["within_threshold"]


def test_unknown_region_returns_404():
    app.dependency_overrides[get_repository] = _fake_repository
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/accessibility/regions/00000")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_database_numeric_values_are_json_numbers():
    assert _json_row({"coverage_pct": Decimal("96.43")}) == {
        "coverage_pct": 96.43
    }

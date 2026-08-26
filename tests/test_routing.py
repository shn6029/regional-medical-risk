import pandas as pd

from regional_medical_risk.routing import (
    KakaoDailyQuotaExceeded,
    build_candidate_pairs,
    collect_route_matrix,
    summarize_route_access,
)


def test_candidate_pairs_and_weighted_route_access():
    demand = pd.DataFrame(
        [
            {
                "demand_id": "P1",
                "region_code": 1,
                "population": 75,
                "latitude": 36.0,
                "longitude": 128.0,
            },
            {
                "demand_id": "P2",
                "region_code": 1,
                "population": 25,
                "latitude": 36.1,
                "longitude": 128.0,
            },
        ]
    )
    hospitals = pd.DataFrame(
        [
            {
                "hospital_id": "A",
                "latitude": 36.0,
                "longitude": 128.0,
                "closure_candidate": True,
            },
            {
                "hospital_id": "B",
                "latitude": 37.0,
                "longitude": 129.0,
                "closure_candidate": True,
            },
        ]
    )

    pairs = build_candidate_pairs(demand, hospitals, candidate_count=1)
    assert pairs["hospital_id"].tolist() == ["A", "A"]

    routes = pd.DataFrame(
        [
            {
                "demand_id": "P1",
                "hospital_id": "A",
                "route_distance_km": 4,
                "route_duration_min": 8,
                "route_status": "ok",
            },
            {
                "demand_id": "P2",
                "hospital_id": "A",
                "route_distance_km": 8,
                "route_duration_min": 16,
                "route_status": "ok",
            },
        ]
    )
    access = summarize_route_access(routes, demand).iloc[0]
    assert access["access_distance_km"] == 5
    assert access["access_duration_min"] == 10


def test_daily_multi_destination_collection_resumes(tmp_path):
    demand = pd.DataFrame(
        [
            {
                "demand_id": f"P{number}",
                "region_code": 1,
                "population": 10,
                "latitude": 36.0 + number / 100,
                "longitude": 128.0,
            }
            for number in range(3)
        ]
    )
    hospitals = pd.DataFrame(
        [
            {
                "hospital_id": hospital_id,
                "latitude": 36.0,
                "longitude": longitude,
                "closure_candidate": True,
            }
            for hospital_id, longitude in [("A", 128.0), ("B", 128.1)]
        ]
    )

    class FakeClient:
        def __init__(self):
            self.calls = 0

        def routes(self, origin_lon, origin_lat, destinations):
            self.calls += 1
            return {
                destination["key"]: {
                    "route_distance_km": 2,
                    "route_duration_min": 4,
                    "route_status": "ok",
                }
                for destination in destinations
            }

    cache_path = tmp_path / "kakao_routes.csv"
    first_client = FakeClient()
    first = collect_route_matrix(
        demand, hospitals, first_client, cache_path, candidate_count=2, daily_origin_limit=2
    )
    assert first_client.calls == 2
    assert len(first) == 4
    assert first.attrs["collection_complete"] is False

    second_client = FakeClient()
    second = collect_route_matrix(
        demand, hospitals, second_client, cache_path, candidate_count=2, daily_origin_limit=2
    )
    assert second_client.calls == 1
    assert len(second) == 6
    assert second.attrs["collection_complete"] is True


def test_daily_quota_stops_cleanly_and_keeps_cache(tmp_path):
    demand = pd.DataFrame(
        [
            {
                "demand_id": f"P{number}",
                "region_code": 1,
                "population": 10,
                "latitude": 36.0 + number / 100,
                "longitude": 128.0,
            }
            for number in range(2)
        ]
    )
    hospitals = pd.DataFrame(
        [
            {
                "hospital_id": "A",
                "latitude": 36.0,
                "longitude": 128.0,
                "closure_candidate": True,
            }
        ]
    )

    class QuotaClient:
        def __init__(self):
            self.calls = 0

        def routes(self, origin_lon, origin_lat, destinations):
            self.calls += 1
            if self.calls == 2:
                raise KakaoDailyQuotaExceeded
            return {
                "A": {
                    "route_distance_km": 2,
                    "route_duration_min": 4,
                    "route_status": "ok",
                }
            }

    routes = collect_route_matrix(
        demand,
        hospitals,
        QuotaClient(),
        tmp_path / "kakao_routes.csv",
        candidate_count=1,
        daily_origin_limit=2,
    )
    assert len(routes) == 1
    assert routes.attrs["collection_complete"] is False

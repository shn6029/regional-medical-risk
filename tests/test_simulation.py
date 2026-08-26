import pandas as pd

from regional_medical_risk.simulation import simulate_hospital_closure


def test_closing_nearest_hospital_increases_distance_and_risk():
    region = pd.Series(
        {
            "region_code": 1,
            "population": 1000,
            "senior_population": 200,
            "hospital_count": 2,
            "hospital_beds": 100,
            "aging_rate": 20,
            "population_change_5y_pct": -5,
            "facilities_per_1000": 2,
            "access_distance_km": 1,
        }
    )
    hospitals = pd.DataFrame(
        [
            {
                "hospital_id": "A",
                "hospital_name": "가병원",
                "region_code": 1,
                "beds": 60,
                "latitude": 36.0,
                "longitude": 128.0,
            },
            {
                "hospital_id": "B",
                "hospital_name": "나병원",
                "region_code": 1,
                "beds": 40,
                "latitude": 36.0,
                "longitude": 129.0,
            },
        ]
    )
    demand = pd.DataFrame(
        [
            {
                "region_code": 1,
                "population": 600,
                "senior_population": 120,
                "latitude": 36.0,
                "longitude": 128.0,
            },
            {
                "region_code": 1,
                "population": 400,
                "senior_population": 80,
                "latitude": 36.0,
                "longitude": 128.1,
            },
        ]
    )

    result = simulate_hospital_closure(region, hospitals, "A", demand)

    assert result["hospital_count_after"] == result["hospital_count_before"] - 1
    assert result["access_distance_after"] > result["access_distance_before"]
    assert result["risk_after"] > result["risk_before"]
    assert result["affected_population"] == 1000
    assert result["affected_senior_population"] == 200


def test_route_matrix_adds_driving_time_to_closure_result():
    region = pd.Series(
        {
            "region_code": 1,
            "population": 1000,
            "senior_population": 200,
            "hospital_count": 2,
            "hospital_beds": 100,
            "aging_rate": 20,
            "population_change_5y_pct": -5,
            "facilities_per_1000": 2,
            "access_distance_km": 1,
        }
    )
    hospitals = pd.DataFrame(
        [
            {"hospital_id": "A", "hospital_name": "가병원", "region_code": 1, "beds": 60},
            {"hospital_id": "B", "hospital_name": "나병원", "region_code": 1, "beds": 40},
        ]
    )
    demand = pd.DataFrame(
        [
            {
                "demand_id": "P1",
                "region_code": 1,
                "population": 1000,
                "senior_population": 200,
            }
        ]
    )
    routes = pd.DataFrame(
        [
            {"demand_id": "P1", "hospital_id": "A", "route_distance_km": 3, "route_duration_min": 7},
            {"demand_id": "P1", "hospital_id": "B", "route_distance_km": 9, "route_duration_min": 18},
        ]
    )

    result = simulate_hospital_closure(region, hospitals, "A", demand, routes)

    assert result["access_duration_before"] == 7
    assert result["access_duration_after"] == 18
    assert result["access_distance_after"] == 9
    assert result["affected_population"] == 1000

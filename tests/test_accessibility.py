import pandas as pd

from regional_medical_risk.accessibility import calculate_2sfca


def test_30_minute_coverage_and_two_step_floating_catchment():
    demand = pd.DataFrame(
        [
            {
                "demand_id": "P1",
                "region_code": 1,
                "population": 1_000,
                "senior_population": 100,
            },
            {
                "demand_id": "P2",
                "region_code": 1,
                "population": 1_000,
                "senior_population": 100,
            },
        ]
    )
    hospitals = pd.DataFrame(
        [
            {"hospital_id": "A", "beds": 20, "closure_candidate": True},
            {"hospital_id": "B", "beds": 10, "closure_candidate": True},
        ]
    )
    routes = pd.DataFrame(
        [
            {"demand_id": "P1", "hospital_id": "A", "route_duration_min": 10},
            {"demand_id": "P2", "hospital_id": "A", "route_duration_min": 20},
            {"demand_id": "P1", "hospital_id": "B", "route_duration_min": 25},
            {"demand_id": "P2", "hospital_id": "B", "route_duration_min": 40},
        ]
    )

    points, regions = calculate_2sfca(demand, hospitals, routes)

    point_scores = points.set_index("demand_id")["two_sfca_score"]
    assert point_scores["P1"] == 200
    assert point_scores["P2"] == 100
    assert regions.iloc[0]["population_within_30min_pct"] == 100
    assert regions.iloc[0]["senior_population_within_30min_pct"] == 100
    assert regions.iloc[0]["two_sfca_score"] == 150


def test_point_without_a_route_inside_30_minutes_is_uncovered():
    demand = pd.DataFrame(
        [
            {
                "demand_id": "P1",
                "region_code": 1,
                "population": 1_000,
                "senior_population": 100,
            }
        ]
    )
    hospitals = pd.DataFrame(
        [{"hospital_id": "A", "beds": 20, "closure_candidate": True}]
    )
    routes = pd.DataFrame(
        [{"demand_id": "P1", "hospital_id": "A", "route_duration_min": 31}]
    )

    points, regions = calculate_2sfca(demand, hospitals, routes)

    assert not points.iloc[0]["within_30min"]
    assert regions.iloc[0]["population_within_30min_pct"] == 0
    assert regions.iloc[0]["two_sfca_score"] == 0

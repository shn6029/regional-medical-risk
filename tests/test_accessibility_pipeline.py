from uuid import UUID

import pandas as pd
import pytest

from regional_medical_risk.accessibility import calculate_2sfca
from regional_medical_risk.accessibility_pipeline import (
    build_result_rows,
    validate_accessibility_inputs,
)


def _sample_inputs():
    demand = pd.DataFrame(
        [
            {
                "demand_id": "P1",
                "region_code": "R1",
                "population": 1_000,
                "senior_population": 100,
            },
            {
                "demand_id": "P2",
                "region_code": "R1",
                "population": 2_000,
                "senior_population": 200,
            },
        ]
    )
    facilities = pd.DataFrame(
        [
            {"hospital_id": "H1", "beds": 30, "closure_candidate": True},
            {"hospital_id": "H2", "beds": 20, "closure_candidate": True},
        ]
    )
    routes = pd.DataFrame(
        [
            {
                "demand_id": "P1",
                "hospital_id": "H1",
                "route_duration_min": 10,
                "route_status": "ok",
            },
            {
                "demand_id": "P1",
                "hospital_id": "H2",
                "route_duration_min": 40,
                "route_status": "estimated_no_road_origin",
            },
            {
                "demand_id": "P2",
                "hospital_id": "H1",
                "route_duration_min": 20,
                "route_status": "ok",
            },
            {
                "demand_id": "P2",
                "hospital_id": "H2",
                "route_duration_min": 25,
                "route_status": "ok",
            },
        ]
    )
    return demand, facilities, routes


def test_validate_accessibility_inputs_reports_route_quality():
    demand, facilities, routes = _sample_inputs()

    metadata = validate_accessibility_inputs(
        demand, facilities, routes, expected_routes_per_demand=2
    )

    assert metadata["demand_point_count"] == 2
    assert metadata["facility_count"] == 2
    assert metadata["exact_route_count"] == 3
    assert metadata["estimated_route_count"] == 1
    assert metadata["estimated_route_share_pct"] == 25.0


def test_validate_accessibility_inputs_rejects_incomplete_route_matrix():
    demand, facilities, routes = _sample_inputs()

    with pytest.raises(ValueError, match="수요점별 경로 수"):
        validate_accessibility_inputs(
            demand, facilities, routes.iloc[:-1], expected_routes_per_demand=2
        )


def test_build_result_rows_matches_supabase_result_schema():
    demand, facilities, routes = _sample_inputs()
    points, regions = calculate_2sfca(demand, facilities, routes)
    run_id = UUID("00000000-0000-0000-0000-000000000001")

    point_rows, region_rows = build_result_rows(run_id, points, regions)

    assert len(point_rows) == 2
    assert point_rows[0][:5] == (run_id, "P1", 1, 30, True)
    assert len(region_rows) == 1
    assert region_rows[0][:3] == (run_id, "R1", 3_000)
    assert region_rows[0][5:8] == (300, 300, 100.0)

from datetime import date

import pandas as pd
import pytest

from regional_medical_risk.supabase_loader import (
    PreparedDataset,
    _as_bool,
    _parse_selected,
    prepare_facilities,
    prepare_route_matrix,
    validate_dataset_rows,
)


def test_facility_mapping_preserves_string_ids_and_snapshot(tmp_path):
    pd.DataFrame(
        [
            {
                "hospital_id": "H001",
                "region_code": "01110",
                "hospital_name": "가병원",
                "hospital_type": "병원",
                "address": "테스트로 1",
                "opened_on": "2020-01-02",
                "beds": 20,
                "latitude": 36.5,
                "longitude": 128.1,
                "closure_candidate": True,
            }
        ]
    ).to_csv(tmp_path / "hospitals.csv", index=False)

    dataset = prepare_facilities(tmp_path, date(2026, 6, 30))
    row = next(dataset.rows())

    assert dataset.row_count == 1
    assert row[0] == "H001"
    assert row[1] == "01110"
    assert row[5] == date(2020, 1, 2)
    assert row[10] is True
    assert row[11] == date(2026, 6, 30)


def test_route_mapping_deduplicates_for_upsert(tmp_path):
    pd.DataFrame(
        [
            {
                "demand_id": "01110001",
                "hospital_id": "H001",
                "straight_distance_km": 1.0,
                "route_distance_km": 1.2,
                "route_duration_min": 10,
                "route_status": "ok",
                "collected_at": "2026-08-18T00:00:00+00:00",
            },
            {
                "demand_id": "01110001",
                "hospital_id": "H001",
                "straight_distance_km": 1.0,
                "route_distance_km": 1.3,
                "route_duration_min": 11,
                "route_status": "ok",
                "collected_at": "2026-08-18T01:00:00+00:00",
            },
        ]
    ).to_csv(tmp_path / "kakao_routes.csv", index=False)

    dataset = prepare_route_matrix(tmp_path)
    row = next(dataset.rows())

    assert dataset.row_count == 1
    assert row[0:2] == ("01110001", "H001")
    assert row[3] == 1.3
    assert row[4] == 11


@pytest.mark.parametrize("value", [True, "true", "1", "예"])
def test_boolean_true_values(value):
    assert _as_bool(value) is True


def test_selected_tables_follow_foreign_key_order():
    assert _parse_selected("route_matrix,regions,facilities") == (
        "regions",
        "facilities",
        "route_matrix",
    )


def test_dry_run_validation_detects_row_count_mismatch():
    dataset = PreparedDataset(
        name="sample",
        target_table="sample",
        source_paths=(),
        row_count=2,
        create_stage_sql="",
        copy_sql="",
        upsert_sql="",
        rows=lambda: iter([("one",)]),
    )

    with pytest.raises(RuntimeError, match="변환 행 수 불일치"):
        validate_dataset_rows(dataset)

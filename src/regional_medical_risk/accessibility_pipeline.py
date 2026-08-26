from __future__ import annotations

import argparse
import json
import os
from typing import Any

import pandas as pd

from regional_medical_risk.accessibility import calculate_2sfca
from regional_medical_risk.supabase_loader import (
    connect_database,
    load_env_file,
    verify_schema,
)


CATCHMENT_MINUTES = 30.0
EXPECTED_ROUTES_PER_DEMAND = 30
METHOD_VERSION = "2sfca-v1"
RESULT_TABLES = {
    "accessibility_runs",
    "demand_accessibility_scores",
    "regional_accessibility_scores",
}


def load_accessibility_inputs(
    connection,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    demand = _query_frame(
        connection,
        """
        select demand_id, region_code, population, senior_population
        from public.demand_points
        """,
    )
    facilities = _query_frame(
        connection,
        """
        with latest_snapshot as (
          select max(snapshot_date) as snapshot_date
          from public.facility_snapshots
        )
        select f.facility_id as hospital_id,
               fs.beds,
               f.is_analysis_target as closure_candidate,
               fs.snapshot_date
        from public.facilities f
        join public.facility_snapshots fs using (facility_id)
        join latest_snapshot latest using (snapshot_date)
        where f.is_analysis_target and fs.is_open
        """,
    )
    routes = _query_frame(
        connection,
        """
        select demand_id,
               facility_id as hospital_id,
               route_duration_min,
               route_status
        from public.route_matrix
        """,
    )
    if facilities.empty:
        raise ValueError("Supabase에 분석 대상 의료기관 스냅샷이 없습니다.")
    snapshot_dates = facilities["snapshot_date"].dropna().astype(str).unique()
    if len(snapshot_dates) != 1:
        raise ValueError(f"의료기관 스냅샷 날짜가 하나가 아닙니다: {snapshot_dates.tolist()}")
    return demand, facilities.drop(columns="snapshot_date"), routes, snapshot_dates[0]


def validate_accessibility_inputs(
    demand: pd.DataFrame,
    facilities: pd.DataFrame,
    routes: pd.DataFrame,
    expected_routes_per_demand: int = EXPECTED_ROUTES_PER_DEMAND,
) -> dict[str, Any]:
    if expected_routes_per_demand < 1:
        raise ValueError("expected_routes_per_demand는 1 이상이어야 합니다.")
    _require_columns(
        demand,
        {"demand_id", "region_code", "population", "senior_population"},
        "demand_points",
    )
    _require_columns(
        facilities,
        {"hospital_id", "beds", "closure_candidate"},
        "facilities",
    )
    _require_columns(
        routes,
        {"demand_id", "hospital_id", "route_duration_min", "route_status"},
        "route_matrix",
    )
    if demand["demand_id"].astype(str).duplicated().any():
        raise ValueError("demand_points에 중복 demand_id가 있습니다.")
    if facilities["hospital_id"].astype(str).duplicated().any():
        raise ValueError("facilities에 중복 hospital_id가 있습니다.")
    route_keys = routes[["demand_id", "hospital_id"]].astype(str)
    if route_keys.duplicated().any():
        raise ValueError("route_matrix에 중복 수요점-병원 경로가 있습니다.")

    durations = pd.to_numeric(routes["route_duration_min"], errors="coerce")
    if durations.isna().any() or durations.lt(0).any():
        raise ValueError("route_matrix에 비어 있거나 음수인 이동시간이 있습니다.")

    demand_ids = set(demand["demand_id"].astype(str))
    facility_ids = set(facilities["hospital_id"].astype(str))
    route_demand_ids = set(route_keys["demand_id"])
    route_facility_ids = set(route_keys["hospital_id"])
    missing_demands = demand_ids.difference(route_demand_ids)
    unknown_demands = route_demand_ids.difference(demand_ids)
    unknown_facilities = route_facility_ids.difference(facility_ids)
    if missing_demands or unknown_demands or unknown_facilities:
        raise ValueError(
            "경로 참조가 완전하지 않습니다: "
            f"경로 없는 수요점={len(missing_demands)}, "
            f"알 수 없는 수요점={len(unknown_demands)}, "
            f"알 수 없는 병원={len(unknown_facilities)}"
        )

    route_counts = route_keys.groupby("demand_id").size()
    if not route_counts.eq(expected_routes_per_demand).all():
        raise ValueError(
            "수요점별 경로 수가 완전하지 않습니다: "
            f"최소={int(route_counts.min())}, 최대={int(route_counts.max())}, "
            f"기대={expected_routes_per_demand}"
        )

    status_counts = {
        str(status): int(count)
        for status, count in routes["route_status"].value_counts(dropna=False).items()
    }
    exact_count = status_counts.get("ok", 0)
    estimated_count = len(routes) - exact_count
    return {
        "demand_point_count": len(demand),
        "facility_count": len(facilities),
        "expected_routes_per_demand": expected_routes_per_demand,
        "route_status_counts": status_counts,
        "exact_route_count": exact_count,
        "estimated_route_count": estimated_count,
        "estimated_route_share_pct": round(estimated_count / len(routes) * 100, 2),
    }


def build_result_rows(
    run_id,
    points: pd.DataFrame,
    regions: pd.DataFrame,
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    point_rows = [
        (
            run_id,
            str(row.demand_id),
            int(row.accessible_hospital_count),
            int(round(row.accessible_beds)),
            bool(row.within_30min),
            float(row.two_sfca_score),
        )
        for row in points.itertuples(index=False)
    ]
    region_rows = [
        (
            run_id,
            str(row.region_code),
            int(round(row.population)),
            int(round(row.population_within_30min)),
            float(row.population_within_30min_pct),
            int(round(row.senior_population)),
            int(round(row.senior_population_within_30min)),
            float(row.senior_population_within_30min_pct),
            float(row.two_sfca_score),
        )
        for row in regions.itertuples(index=False)
    ]
    return point_rows, region_rows


def run_pipeline(connection, dry_run: bool = False) -> dict[str, Any]:
    verify_schema(connection)
    _verify_result_tables(connection)
    demand, facilities, routes, snapshot_date = load_accessibility_inputs(connection)
    parameters = validate_accessibility_inputs(demand, facilities, routes)
    parameters["facility_snapshot_date"] = snapshot_date

    points, regions = calculate_2sfca(
        demand,
        facilities,
        routes,
        catchment_minutes=CATCHMENT_MINUTES,
        demand_column="senior_population",
        supply_column="beds",
    )
    if len(points) != len(demand) or len(regions) != demand["region_code"].nunique():
        raise RuntimeError(
            "2SFCA 결과 행 수가 입력과 다릅니다: "
            f"수요점={len(points)}/{len(demand)}, "
            f"지역={len(regions)}/{demand['region_code'].nunique()}"
        )

    summary = {
        **parameters,
        "route_count": len(routes),
        "demand_result_count": len(points),
        "regional_result_count": len(regions),
        "covered_demand_count": int(points["within_30min"].sum()),
        "national_senior_coverage_pct": _national_senior_coverage(points),
    }
    if dry_run:
        return summary

    run_id = _create_run(connection, len(routes), parameters)
    try:
        point_rows, region_rows = build_result_rows(run_id, points, regions)
        _save_results(connection, run_id, point_rows, region_rows)
    except Exception as error:
        _mark_run_failed(connection, run_id, str(error))
        raise
    summary["run_id"] = str(run_id)
    return summary


def _create_run(connection, route_count: int, parameters: dict[str, Any]):
    from psycopg.types.json import Jsonb

    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into public.accessibility_runs (
              method, method_version, catchment_minutes, demand_column,
              supply_column, route_count, parameters, status
            ) values ('2SFCA', %s, %s, 'senior_population', 'beds', %s, %s, 'running')
            returning run_id
            """,
            (METHOD_VERSION, CATCHMENT_MINUTES, route_count, Jsonb(parameters)),
        )
        return cursor.fetchone()[0]


def _save_results(
    connection,
    run_id,
    point_rows: list[tuple[Any, ...]],
    region_rows: list[tuple[Any, ...]],
) -> None:
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute("set local statement_timeout = '5min'")
            cursor.execute("set local lock_timeout = '30s'")
            with cursor.copy(
                """
                copy public.demand_accessibility_scores (
                  run_id, demand_id, accessible_hospital_count, accessible_beds,
                  within_threshold, two_sfca_score
                ) from stdin
                """
            ) as copy:
                for row in point_rows:
                    copy.write_row(row)
            with cursor.copy(
                """
                copy public.regional_accessibility_scores (
                  run_id, region_code, population, population_within_threshold,
                  population_within_threshold_pct, senior_population,
                  senior_within_threshold, senior_within_threshold_pct,
                  two_sfca_score
                ) from stdin
                """
            ) as copy:
                for row in region_rows:
                    copy.write_row(row)
            cursor.execute(
                """
                update public.accessibility_runs
                set status = 'completed', completed_at = now(), error_message = null
                where run_id = %s
                """,
                (run_id,),
            )


def _mark_run_failed(connection, run_id, error_message: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            update public.accessibility_runs
            set status = 'failed', completed_at = now(), error_message = %s
            where run_id = %s
            """,
            (error_message[:2000], run_id),
        )


def _verify_result_tables(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'public' and table_type = 'BASE TABLE'
            """
        )
        actual = {row[0] for row in cursor.fetchall()}
    missing = RESULT_TABLES.difference(actual)
    if missing:
        raise RuntimeError(f"Supabase 결과 테이블이 없습니다: {sorted(missing)}")


def _query_frame(connection, query: str) -> pd.DataFrame:
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [column.name for column in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=columns)


def _national_senior_coverage(points: pd.DataFrame) -> float:
    total = float(points["senior_population"].sum())
    if total <= 0:
        return 0.0
    covered = float(points.loc[points["within_30min"], "senior_population"].sum())
    return round(covered / total * 100, 2)


def _require_columns(
    frame: pd.DataFrame,
    required: set[str],
    name: str,
) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{name}에 필수 열이 없습니다: {sorted(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Supabase 전국 경로로 30분 고령인구·병상 2SFCA를 계산합니다."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env_file()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        parser.error(".env에 Supabase Session pooler DATABASE_URL을 입력하세요.")

    with connect_database(database_url) as connection:
        summary = run_pipeline(connection, dry_run=args.dry_run)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

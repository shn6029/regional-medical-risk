from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd


DEFAULT_DATA_DIR = Path("data/processed/national")
DEFAULT_FACILITY_SNAPSHOT_DATE = date(2026, 6, 30)
DEFAULT_CLOSURE_SNAPSHOT_DATE = date(2025, 12, 31)
LOAD_ORDER = (
    "regions",
    "population_history",
    "demand_points",
    "facilities",
    "facility_closures",
    "route_matrix",
)
REQUIRED_TABLES = {
    "regions",
    "population_history",
    "demand_points",
    "facilities",
    "facility_snapshots",
    "facility_closures",
    "route_matrix",
    "data_imports",
}


@dataclass
class PreparedDataset:
    name: str
    target_table: str
    source_paths: tuple[Path, ...]
    row_count: int
    create_stage_sql: str
    copy_sql: str
    upsert_sql: str
    rows: Callable[[], Iterator[tuple[Any, ...]]]


def load_env_file(path: Path = Path(".env")) -> None:
    """Load simple KEY=VALUE entries without overwriting exported variables."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


def prepare_regions(data_dir: Path) -> PreparedDataset:
    lookup_path = data_dir / "region_lookup.csv"
    supply_path = data_dir / "medical_supply.csv"
    geojson_path = data_dir / "regions.geojson"
    lookup = pd.read_csv(lookup_path, dtype={"region_code": str})
    supply = pd.read_csv(supply_path, dtype={"region_code": str})
    _require_columns(lookup, {"region_code", "province_name", "region_name"}, lookup_path)
    _require_columns(supply, {"region_code", "latitude", "longitude"}, supply_path)
    _require_unique(lookup, ["region_code"], lookup_path)
    _require_unique(supply, ["region_code"], supply_path)

    boundaries = json.loads(geojson_path.read_text(encoding="utf-8"))
    geometry_by_code = {
        str(feature["properties"]["region_code"]): json.dumps(
            feature["geometry"], ensure_ascii=False, separators=(",", ":")
        )
        for feature in boundaries.get("features", [])
    }
    centers = supply.set_index("region_code")[["latitude", "longitude"]]
    expected = set(lookup["region_code"])
    missing_centers = expected.difference(centers.index)
    missing_boundaries = expected.difference(geometry_by_code)
    if missing_centers or missing_boundaries:
        raise ValueError(
            f"regions 적재 자료가 불완전합니다. 중심점 누락={sorted(missing_centers)[:5]}, "
            f"경계 누락={sorted(missing_boundaries)[:5]}"
        )

    def rows() -> Iterator[tuple[Any, ...]]:
        for row in lookup.itertuples(index=False):
            center = centers.loc[str(row.region_code)]
            yield (
                str(row.region_code),
                str(row.province_name),
                str(row.region_name),
                _as_float(center["latitude"]),
                _as_float(center["longitude"]),
                geometry_by_code[str(row.region_code)],
            )

    return PreparedDataset(
        name="regions",
        target_table="regions",
        source_paths=(lookup_path, supply_path, geojson_path),
        row_count=len(lookup),
        create_stage_sql="""
            create temp table stage_regions (
              region_code text, province_name text, region_name text,
              center_latitude double precision, center_longitude double precision,
              boundary_geojson text
            ) on commit drop
        """,
        copy_sql="""
            copy stage_regions (
              region_code, province_name, region_name, center_latitude,
              center_longitude, boundary_geojson
            ) from stdin
        """,
        upsert_sql="""
            insert into public.regions (
              region_code, province_name, region_name, center_latitude,
              center_longitude, boundary
            )
            select
              region_code, province_name, region_name, center_latitude,
              center_longitude,
              extensions.st_multi(
                extensions.st_setsrid(
                  extensions.st_geomfromgeojson(boundary_geojson), 4326
                )
              )::extensions.geometry(MultiPolygon, 4326)
            from stage_regions
            on conflict (region_code) do update set
              province_name = excluded.province_name,
              region_name = excluded.region_name,
              center_latitude = excluded.center_latitude,
              center_longitude = excluded.center_longitude,
              boundary = excluded.boundary
        """,
        rows=rows,
    )


def prepare_population_history(data_dir: Path) -> PreparedDataset:
    path = data_dir / "historical_population.csv"
    frame = pd.read_csv(path, dtype={"region_code": str})
    columns = {
        "region_code",
        "year",
        "population",
        "senior_population",
        "youth_population",
    }
    _require_columns(frame, columns, path)
    _require_unique(frame, ["region_code", "year"], path)

    def rows() -> Iterator[tuple[Any, ...]]:
        for row in frame.itertuples(index=False):
            yield (
                str(row.region_code),
                _as_int(row.year),
                _as_int(row.population),
                _as_int(row.senior_population),
                _as_int(row.youth_population),
            )

    return PreparedDataset(
        "population_history",
        "population_history",
        (path,),
        len(frame),
        """create temp table stage_population_history (
          region_code text, year smallint, population integer,
          senior_population integer, youth_population integer
        ) on commit drop""",
        """copy stage_population_history (
          region_code, year, population, senior_population, youth_population
        ) from stdin""",
        """insert into public.population_history (
          region_code, year, population, senior_population, youth_population
        ) select region_code, year, population, senior_population, youth_population
        from stage_population_history
        on conflict (region_code, year) do update set
          population = excluded.population,
          senior_population = excluded.senior_population,
          youth_population = excluded.youth_population""",
        rows,
    )


def prepare_demand_points(data_dir: Path) -> PreparedDataset:
    path = data_dir / "demand_points.csv"
    frame = pd.read_csv(path, dtype={"region_code": str, "demand_id": str})
    columns = {
        "demand_id",
        "region_code",
        "demand_name",
        "population",
        "senior_population",
        "latitude",
        "longitude",
    }
    _require_columns(frame, columns, path)
    _require_unique(frame, ["demand_id"], path)

    def rows() -> Iterator[tuple[Any, ...]]:
        for row in frame.itertuples(index=False):
            yield (
                str(row.demand_id),
                str(row.region_code),
                str(row.demand_name),
                _as_int(row.population),
                _as_int(row.senior_population),
                _as_float(row.latitude),
                _as_float(row.longitude),
            )

    return PreparedDataset(
        "demand_points",
        "demand_points",
        (path,),
        len(frame),
        """create temp table stage_demand_points (
          demand_id text, region_code text, demand_name text, population integer,
          senior_population integer, latitude double precision, longitude double precision
        ) on commit drop""",
        """copy stage_demand_points (
          demand_id, region_code, demand_name, population, senior_population,
          latitude, longitude
        ) from stdin""",
        """insert into public.demand_points (
          demand_id, region_code, demand_name, population, senior_population,
          latitude, longitude
        ) select demand_id, region_code, demand_name, population, senior_population,
          latitude, longitude from stage_demand_points
        on conflict (demand_id) do update set
          region_code = excluded.region_code,
          demand_name = excluded.demand_name,
          population = excluded.population,
          senior_population = excluded.senior_population,
          latitude = excluded.latitude,
          longitude = excluded.longitude""",
        rows,
    )


def prepare_facilities(data_dir: Path, snapshot_date: date) -> PreparedDataset:
    path = data_dir / "hospitals.csv"
    frame = pd.read_csv(path, dtype={"hospital_id": str, "region_code": str})
    columns = {
        "hospital_id",
        "region_code",
        "hospital_name",
        "hospital_type",
        "address",
        "opened_on",
        "beds",
        "latitude",
        "longitude",
        "closure_candidate",
    }
    _require_columns(frame, columns, path)
    _require_unique(frame, ["hospital_id"], path)

    def rows() -> Iterator[tuple[Any, ...]]:
        for row in frame.itertuples(index=False):
            yield (
                str(row.hospital_id),
                str(row.region_code),
                str(row.hospital_name),
                str(row.hospital_type),
                _as_optional_text(row.address),
                _as_date(row.opened_on),
                None,
                _as_int(row.beds),
                _as_float(row.latitude),
                _as_float(row.longitude),
                _as_bool(row.closure_candidate),
                snapshot_date,
            )

    return PreparedDataset(
        "facilities",
        "facilities",
        (path,),
        len(frame),
        """create temp table stage_facilities (
          facility_id text, region_code text, facility_name text, facility_type text,
          address text, opened_on date, closed_on date, beds integer,
          latitude double precision, longitude double precision,
          is_analysis_target boolean, source_snapshot_date date
        ) on commit drop""",
        """copy stage_facilities (
          facility_id, region_code, facility_name, facility_type, address, opened_on,
          closed_on, beds, latitude, longitude, is_analysis_target, source_snapshot_date
        ) from stdin""",
        """insert into public.facilities (
          facility_id, region_code, facility_name, facility_type, address, opened_on,
          closed_on, beds, latitude, longitude, is_analysis_target, source_snapshot_date
        ) select facility_id, region_code, facility_name, facility_type, address, opened_on,
          closed_on, beds, latitude, longitude, is_analysis_target, source_snapshot_date
        from stage_facilities
        on conflict (facility_id) do update set
          region_code = excluded.region_code,
          facility_name = excluded.facility_name,
          facility_type = excluded.facility_type,
          address = excluded.address,
          opened_on = excluded.opened_on,
          closed_on = excluded.closed_on,
          beds = excluded.beds,
          latitude = excluded.latitude,
          longitude = excluded.longitude,
          is_analysis_target = excluded.is_analysis_target,
          source_snapshot_date = excluded.source_snapshot_date;

        insert into public.facility_snapshots (
          facility_id, snapshot_date, region_code, facility_type, beds, is_open
        ) select facility_id, source_snapshot_date, region_code, facility_type, beds,
          closed_on is null
        from stage_facilities
        on conflict (facility_id, snapshot_date) do update set
          region_code = excluded.region_code,
          facility_type = excluded.facility_type,
          beds = excluded.beds,
          is_open = excluded.is_open
        """,
        rows,
    )


def prepare_facility_closures(data_dir: Path, snapshot_date: date) -> PreparedDataset:
    path = data_dir / "closure_validation.csv"
    frame = pd.read_csv(path, dtype={"hospital_id": str, "region_code": str})
    columns = {
        "hospital_id",
        "hospital_name",
        "hospital_type",
        "region_code",
        "closed_on",
        "baseline_date",
        "comparison_date",
        "predicted_distance_delta_km",
        "observed_distance_delta_km",
        "predicted_direction",
        "observed_direction",
        "direction_agreement",
        "predicted_risk_delta",
        "observed_risk_delta",
        "affected_population",
        "affected_senior_population",
        "hospital_count_before",
        "hospital_count_observed",
    }
    _require_columns(frame, columns, path)
    _require_unique(frame, ["hospital_id", "closed_on"], path)

    def rows() -> Iterator[tuple[Any, ...]]:
        for row in frame.itertuples(index=False):
            yield (
                str(row.hospital_id),
                str(row.hospital_name),
                str(row.hospital_type),
                str(row.region_code),
                _as_date(row.closed_on),
                _as_date(row.baseline_date),
                _as_date(row.comparison_date),
                _as_optional_float(row.predicted_distance_delta_km),
                _as_optional_float(row.observed_distance_delta_km),
                _as_optional_float(row.predicted_risk_delta),
                _as_optional_float(row.observed_risk_delta),
                _as_optional_text(row.predicted_direction),
                _as_optional_text(row.observed_direction),
                _as_bool(row.direction_agreement),
                _as_optional_int(row.affected_population),
                _as_optional_int(row.affected_senior_population),
                _as_optional_int(row.hospital_count_before),
                _as_optional_int(row.hospital_count_observed),
                snapshot_date,
            )

    return PreparedDataset(
        "facility_closures",
        "facility_closures",
        (path,),
        len(frame),
        """create temp table stage_facility_closures (
          facility_id text, facility_name text, facility_type text, region_code text,
          closed_on date, baseline_date date, comparison_date date,
          predicted_distance_delta_km numeric, observed_distance_delta_km numeric,
          predicted_risk_delta numeric, observed_risk_delta numeric,
          predicted_direction text, observed_direction text, direction_agreement boolean,
          affected_population integer, affected_senior_population integer,
          hospital_count_before integer, hospital_count_observed integer,
          source_snapshot_date date
        ) on commit drop""",
        """copy stage_facility_closures (
          facility_id, facility_name, facility_type, region_code, closed_on,
          baseline_date, comparison_date, predicted_distance_delta_km,
          observed_distance_delta_km, predicted_risk_delta, observed_risk_delta,
          predicted_direction, observed_direction, direction_agreement,
          affected_population, affected_senior_population, hospital_count_before,
          hospital_count_observed, source_snapshot_date
        ) from stdin""",
        """insert into public.facility_closures (
          facility_id, facility_name, facility_type, region_code, closed_on,
          baseline_date, comparison_date, predicted_distance_delta_km,
          observed_distance_delta_km, predicted_risk_delta, observed_risk_delta,
          predicted_direction, observed_direction, direction_agreement,
          affected_population, affected_senior_population, hospital_count_before,
          hospital_count_observed, source_snapshot_date
        ) select facility_id, facility_name, facility_type, region_code, closed_on,
          baseline_date, comparison_date, predicted_distance_delta_km,
          observed_distance_delta_km, predicted_risk_delta, observed_risk_delta,
          predicted_direction, observed_direction, direction_agreement,
          affected_population, affected_senior_population, hospital_count_before,
          hospital_count_observed, source_snapshot_date
        from stage_facility_closures
        on conflict (facility_id, closed_on) do update set
          facility_name = excluded.facility_name,
          facility_type = excluded.facility_type,
          region_code = excluded.region_code,
          baseline_date = excluded.baseline_date,
          comparison_date = excluded.comparison_date,
          predicted_distance_delta_km = excluded.predicted_distance_delta_km,
          observed_distance_delta_km = excluded.observed_distance_delta_km,
          predicted_risk_delta = excluded.predicted_risk_delta,
          observed_risk_delta = excluded.observed_risk_delta,
          predicted_direction = excluded.predicted_direction,
          observed_direction = excluded.observed_direction,
          direction_agreement = excluded.direction_agreement,
          affected_population = excluded.affected_population,
          affected_senior_population = excluded.affected_senior_population,
          hospital_count_before = excluded.hospital_count_before,
          hospital_count_observed = excluded.hospital_count_observed,
          source_snapshot_date = excluded.source_snapshot_date
        """,
        rows,
    )


def prepare_route_matrix(data_dir: Path) -> PreparedDataset:
    path = data_dir / "kakao_routes.csv"
    frame = pd.read_csv(path, dtype={"demand_id": str, "hospital_id": str})
    columns = {
        "demand_id",
        "hospital_id",
        "straight_distance_km",
        "route_distance_km",
        "route_duration_min",
        "route_status",
        "collected_at",
    }
    _require_columns(frame, columns, path)
    frame = frame.drop_duplicates(["demand_id", "hospital_id"], keep="last")
    _require_unique(frame, ["demand_id", "hospital_id"], path)

    def rows() -> Iterator[tuple[Any, ...]]:
        for row in frame.itertuples(index=False):
            yield (
                str(row.demand_id),
                str(row.hospital_id),
                _as_float(row.straight_distance_km),
                _as_optional_float(row.route_distance_km),
                _as_optional_float(row.route_duration_min),
                str(row.route_status),
                _as_datetime(row.collected_at),
            )

    return PreparedDataset(
        "route_matrix",
        "route_matrix",
        (path,),
        len(frame),
        """create temp table stage_route_matrix (
          demand_id text, facility_id text, straight_distance_km numeric,
          route_distance_km numeric, route_duration_min numeric,
          route_status text, collected_at timestamptz
        ) on commit drop""",
        """copy stage_route_matrix (
          demand_id, facility_id, straight_distance_km, route_distance_km,
          route_duration_min, route_status, collected_at
        ) from stdin""",
        """insert into public.route_matrix (
          demand_id, facility_id, straight_distance_km, route_distance_km,
          route_duration_min, route_status, collected_at
        ) select demand_id, facility_id, straight_distance_km, route_distance_km,
          route_duration_min, route_status, collected_at from stage_route_matrix
        on conflict (demand_id, facility_id) do update set
          straight_distance_km = excluded.straight_distance_km,
          route_distance_km = excluded.route_distance_km,
          route_duration_min = excluded.route_duration_min,
          route_status = excluded.route_status,
          collected_at = excluded.collected_at
        """,
        rows,
    )


def prepare_dataset(
    name: str,
    data_dir: Path,
    facility_snapshot_date: date = DEFAULT_FACILITY_SNAPSHOT_DATE,
    closure_snapshot_date: date = DEFAULT_CLOSURE_SNAPSHOT_DATE,
) -> PreparedDataset:
    if name == "regions":
        return prepare_regions(data_dir)
    if name == "population_history":
        return prepare_population_history(data_dir)
    if name == "demand_points":
        return prepare_demand_points(data_dir)
    if name == "facilities":
        return prepare_facilities(data_dir, facility_snapshot_date)
    if name == "facility_closures":
        return prepare_facility_closures(data_dir, closure_snapshot_date)
    if name == "route_matrix":
        return prepare_route_matrix(data_dir)
    raise ValueError(f"지원하지 않는 데이터셋입니다: {name}")


def connect_database(database_url: str):
    try:
        import psycopg
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "psycopg가 없습니다. `python -m pip install -e .`를 먼저 실행하세요."
        ) from error

    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise ValueError("DATABASE_URL은 PostgreSQL 연결 문자열이어야 합니다.")
    if parsed.port == 6543:
        print(
            "주의: transaction pooler(6543) 대신 Connect의 Session pooler(5432)를 권장합니다.",
            file=sys.stderr,
        )
    return psycopg.connect(
        database_url,
        autocommit=True,
        prepare_threshold=None,
        sslmode="require",
        application_name="regional-medical-risk-loader",
    )


def verify_schema(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """select table_name from information_schema.tables
               where table_schema = 'public' and table_type = 'BASE TABLE'"""
        )
        actual = {row[0] for row in cursor.fetchall()}
        missing = REQUIRED_TABLES.difference(actual)
        if missing:
            raise RuntimeError(f"Supabase migration이 필요합니다. 누락 테이블: {sorted(missing)}")
        cursor.execute("select extversion from pg_extension where extname = 'postgis'")
        if cursor.fetchone() is None:
            raise RuntimeError("PostGIS 확장이 설치되어 있지 않습니다.")


def load_dataset(connection, dataset: PreparedDataset) -> tuple[int, int]:
    checksum = combined_sha256(dataset.source_paths)
    source_file = ",".join(path.name for path in dataset.source_paths)
    import_id = _start_import(
        connection, dataset.name, source_file, checksum, dataset.row_count
    )
    try:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("set local statement_timeout = '15min'")
                cursor.execute("set local lock_timeout = '30s'")
                cursor.execute(dataset.create_stage_sql)
                copied = _copy_rows(cursor, dataset.copy_sql, dataset.rows())
                if copied != dataset.row_count:
                    raise RuntimeError(
                        f"{dataset.name} COPY 행 수 불일치: {copied}/{dataset.row_count}"
                    )
                cursor.execute(dataset.upsert_sql)
                cursor.execute(f"select count(*) from public.{dataset.target_table}")
                target_count = int(cursor.fetchone()[0])
        _finish_import(connection, import_id, "completed")
        return copied, target_count
    except Exception as error:
        _finish_import(connection, import_id, "failed", str(error)[:2000])
        raise


def combined_sha256(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def _copy_rows(cursor, statement: str, rows: Iterable[tuple[Any, ...]]) -> int:
    count = 0
    with cursor.copy(statement) as copy:
        for row in rows:
            copy.write_row(row)
            count += 1
            if count % 25_000 == 0:
                print(f"  COPY {count:,}행")
    return count


def validate_dataset_rows(dataset: PreparedDataset) -> None:
    converted = sum(1 for _ in dataset.rows())
    if converted != dataset.row_count:
        raise RuntimeError(
            f"{dataset.name} 변환 행 수 불일치: {converted}/{dataset.row_count}"
        )


def _start_import(
    connection,
    dataset_name: str,
    source_file: str,
    checksum: str,
    row_count: int,
):
    with connection.cursor() as cursor:
        cursor.execute(
            """insert into public.data_imports (
                 dataset_name, source_file, file_sha256, row_count, status
               ) values (%s, %s, %s, %s, 'running') returning import_id""",
            (dataset_name, source_file, checksum, row_count),
        )
        return cursor.fetchone()[0]


def _finish_import(connection, import_id, status: str, error_message: str | None = None):
    with connection.cursor() as cursor:
        cursor.execute(
            """update public.data_imports
               set status = %s, error_message = %s, completed_at = now()
               where import_id = %s""",
            (status, error_message, import_id),
        )


def _require_columns(frame: pd.DataFrame, required: set[str], path: Path) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{path.name} 필수 열 누락: {sorted(missing)}")


def _require_unique(frame: pd.DataFrame, columns: list[str], path: Path) -> None:
    duplicated = frame.duplicated(columns, keep=False)
    if duplicated.any():
        samples = frame.loc[duplicated, columns].head(5).to_dict("records")
        raise ValueError(f"{path.name} 중복 키 {columns}: {samples}")
    if frame[columns].isna().any(axis=None):
        raise ValueError(f"{path.name} 키 열에 결측값이 있습니다: {columns}")


def _is_missing(value: Any) -> bool:
    return value is None or bool(pd.isna(value))


def _as_optional_text(value: Any) -> str | None:
    if _is_missing(value):
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: Any) -> int:
    if _is_missing(value):
        raise ValueError("필수 정수값이 비어 있습니다.")
    return int(float(value))


def _as_optional_int(value: Any) -> int | None:
    return None if _is_missing(value) else int(float(value))


def _as_float(value: Any) -> float:
    if _is_missing(value):
        raise ValueError("필수 실수값이 비어 있습니다.")
    return float(value)


def _as_optional_float(value: Any) -> float | None:
    return None if _is_missing(value) else float(value)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if _is_missing(value):
        return False
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y", "예"}:
        return True
    if normalized in {"false", "0", "no", "n", "아니오"}:
        return False
    raise ValueError(f"불리언으로 변환할 수 없습니다: {value}")


def _as_date(value: Any) -> date | None:
    if _is_missing(value):
        return None
    return pd.Timestamp(value).date()


def _as_datetime(value: Any) -> datetime:
    if _is_missing(value):
        raise ValueError("수집 시각이 비어 있습니다.")
    return pd.Timestamp(value).to_pydatetime()


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_selected(value: str) -> tuple[str, ...]:
    selected = tuple(part.strip() for part in value.split(",") if part.strip())
    unknown = set(selected).difference(LOAD_ORDER)
    if unknown:
        raise ValueError(f"지원하지 않는 --only 값: {sorted(unknown)}")
    return tuple(name for name in LOAD_ORDER if name in selected)


def main() -> None:
    parser = argparse.ArgumentParser(description="전국 의료 CSV를 Supabase에 COPY/UPSERT합니다.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--only",
        default=",".join(LOAD_ORDER),
        help=f"쉼표로 구분: {','.join(LOAD_ORDER)}",
    )
    parser.add_argument(
        "--facility-snapshot-date",
        type=_parse_date,
        default=DEFAULT_FACILITY_SNAPSHOT_DATE,
    )
    parser.add_argument(
        "--closure-snapshot-date",
        type=_parse_date,
        default=DEFAULT_CLOSURE_SNAPSHOT_DATE,
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    selected = _parse_selected(args.only)
    if not selected:
        parser.error("적재할 데이터셋이 없습니다.")

    if args.dry_run:
        print("Supabase 적재 사전 검증")
        for name in selected:
            dataset = prepare_dataset(
                name,
                args.data_dir,
                args.facility_snapshot_date,
                args.closure_snapshot_date,
            )
            validate_dataset_rows(dataset)
            checksum = combined_sha256(dataset.source_paths)
            print(f"- {name}: {dataset.row_count:,}행, sha256={checksum[:12]}...")
        return

    load_env_file()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        parser.error(".env에 Supabase Session pooler DATABASE_URL을 입력하세요.")

    with connect_database(database_url) as connection:
        verify_schema(connection)
        for name in selected:
            print(f"[{name}] 준비")
            dataset = prepare_dataset(
                name,
                args.data_dir,
                args.facility_snapshot_date,
                args.closure_snapshot_date,
            )
            copied, total = load_dataset(connection, dataset)
            print(f"[{name}] 완료: 입력 {copied:,}행, DB 누적 {total:,}행")


if __name__ == "__main__":
    main()

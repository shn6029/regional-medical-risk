from __future__ import annotations

import os
from contextlib import asynccontextmanager
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

from fastapi import Depends, FastAPI, HTTPException
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

LATEST_RUN_SQL = """
    select run_id, method, method_version, catchment_minutes, route_count,
           parameters, started_at, completed_at
    from public.accessibility_runs
    where status = 'completed'
    order by completed_at desc, started_at desc
    limit 1
"""


class AccessibilityRepository:
    def __init__(self, connection):
        self.connection = connection

    def latest_summary(self) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                with latest as ({LATEST_RUN_SQL})
                select latest.*,
                       count(scores.demand_id) as demand_point_count,
                       count(scores.demand_id) filter (
                         where scores.within_threshold
                       ) as covered_demand_count,
                       coalesce(sum(points.senior_population), 0) as senior_population,
                       coalesce(sum(points.senior_population) filter (
                         where scores.within_threshold
                       ), 0) as covered_senior_population,
                       coalesce(
                         round(
                           sum(points.senior_population) filter (
                             where scores.within_threshold
                           )::numeric
                           / nullif(sum(points.senior_population), 0) * 100,
                           2
                         ),
                         0
                       ) as senior_coverage_pct
                from latest
                join public.demand_accessibility_scores scores using (run_id)
                join public.demand_points points using (demand_id)
                group by latest.run_id, latest.method, latest.method_version,
                         latest.catchment_minutes, latest.route_count,
                         latest.parameters, latest.started_at, latest.completed_at
                """
            )
            row = cursor.fetchone()
        return _json_row(row) if row else None

    def list_regions(self) -> tuple[str, list[dict[str, Any]]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                with latest as ({LATEST_RUN_SQL})
                select latest.run_id, regions.region_code, regions.province_name,
                       regions.region_name, regions.center_latitude,
                       regions.center_longitude, scores.population,
                       scores.population_within_threshold,
                       scores.population_within_threshold_pct,
                       scores.senior_population, scores.senior_within_threshold,
                       scores.senior_within_threshold_pct, scores.two_sfca_score
                from latest
                join public.regional_accessibility_scores scores using (run_id)
                join public.regions regions using (region_code)
                order by regions.province_name, regions.region_name
                """
            )
            rows = [_json_row(row) for row in cursor.fetchall()]
        run_id = str(rows[0]["run_id"]) if rows else ""
        for row in rows:
            row.pop("run_id", None)
        return run_id, rows

    def get_region(self, region_code: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                with latest as ({LATEST_RUN_SQL})
                select latest.run_id, regions.region_code, regions.province_name,
                       regions.region_name, regions.center_latitude,
                       regions.center_longitude, scores.population,
                       scores.population_within_threshold,
                       scores.population_within_threshold_pct,
                       scores.senior_population, scores.senior_within_threshold,
                       scores.senior_within_threshold_pct, scores.two_sfca_score
                from latest
                join public.regional_accessibility_scores scores using (run_id)
                join public.regions regions using (region_code)
                where regions.region_code = %s
                """,
                (region_code,),
            )
            region = cursor.fetchone()
            if region is None:
                return None
            cursor.execute(
                """
                select points.demand_id, points.demand_name, points.population,
                       points.senior_population, points.latitude, points.longitude,
                       scores.accessible_hospital_count, scores.accessible_beds,
                       scores.within_threshold, scores.two_sfca_score
                from public.demand_accessibility_scores scores
                join public.demand_points points using (demand_id)
                where scores.run_id = %s and points.region_code = %s
                order by points.demand_name
                """,
                (region["run_id"], region_code),
            )
            demand_points = [_json_row(row) for row in cursor.fetchall()]
        result = _json_row(region)
        result["run_id"] = str(result["run_id"])
        result["demand_points"] = demand_points
        return result


def _json_row(row) -> dict[str, Any]:
    return {
        key: float(value) if isinstance(value, Decimal) else value
        for key, value in dict(row).items()
    }


def _load_local_env(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


@lru_cache(maxsize=1)
def database_pool() -> ConnectionPool:
    _load_local_env()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL 환경변수가 필요합니다.")
    max_size = max(1, min(int(os.getenv("DB_POOL_MAX_SIZE", "5")), 10))
    return ConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=max_size,
        kwargs={
            "autocommit": True,
            "prepare_threshold": None,
            "sslmode": "require",
            "application_name": "medireach-api",
            "row_factory": dict_row,
        },
        check=ConnectionPool.check_connection,
        open=True,
    )


def get_repository() -> Iterator[AccessibilityRepository]:
    with database_pool().connection() as connection:
        yield AccessibilityRepository(connection)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    if database_pool.cache_info().currsize:
        database_pool().close()
        database_pool.cache_clear()


app = FastAPI(
    title="MediReach API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/accessibility/latest")
def latest_accessibility(
    repository: AccessibilityRepository = Depends(get_repository),
) -> dict[str, Any]:
    result = repository.latest_summary()
    if result is None:
        raise HTTPException(status_code=404, detail="완료된 2SFCA 실행이 없습니다.")
    result["run_id"] = str(result["run_id"])
    return result


@app.get("/api/v1/accessibility/regions")
def accessibility_regions(
    repository: AccessibilityRepository = Depends(get_repository),
) -> dict[str, Any]:
    run_id, items = repository.list_regions()
    if not items:
        raise HTTPException(status_code=404, detail="완료된 지역별 2SFCA 결과가 없습니다.")
    return {"run_id": run_id, "count": len(items), "items": items}


@app.get("/api/v1/accessibility/regions/{region_code}")
def accessibility_region(
    region_code: str,
    repository: AccessibilityRepository = Depends(get_repository),
) -> dict[str, Any]:
    result = repository.get_region(region_code)
    if result is None:
        raise HTTPException(status_code=404, detail="해당 지역의 2SFCA 결과가 없습니다.")
    return result

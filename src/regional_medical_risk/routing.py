from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


KAKAO_DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"
KAKAO_MULTI_DESTINATIONS_URL = (
    "https://apis-navi.kakaomobility.com/v1/destinations/directions"
)
ROUTE_COLUMNS = [
    "demand_id",
    "hospital_id",
    "straight_distance_km",
    "route_distance_km",
    "route_duration_min",
    "route_status",
    "collected_at",
]


class KakaoDailyQuotaExceeded(RuntimeError):
    """Raised when Kakao reports that the app's daily routing quota is exhausted."""


def load_kakao_api_key(env_path: str | Path = ".env") -> str:
    """Load the Kakao REST key without adding a dotenv dependency."""
    key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    if key:
        return key

    path = Path(env_path)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() == "KAKAO_REST_API_KEY":
                key = value.strip().strip("'\"")
                break
    if not key:
        raise ValueError(".env에 KAKAO_REST_API_KEY를 입력해 주세요.")
    return key


class KakaoDirectionsClient:
    def __init__(self, api_key: str, timeout: int = 20) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def route(self, origin_lon: float, origin_lat: float, dest_lon: float, dest_lat: float) -> dict:
        query = urlencode(
            {
                "origin": f"{origin_lon},{origin_lat}",
                "destination": f"{dest_lon},{dest_lat}",
                "priority": "TIME",
                "summary": "true",
            }
        )
        request = Request(
            f"{KAKAO_DIRECTIONS_URL}?{query}",
            headers={"Authorization": f"KakaoAK {self.api_key}"},
        )
        for attempt in range(3):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    payload = json.load(response)
                route = payload["routes"][0]
                if route.get("result_code") != 0:
                    return {
                        "route_distance_km": np.nan,
                        "route_duration_min": np.nan,
                        "route_status": route.get("result_msg", "no_route"),
                    }
                summary = route["summary"]
                return {
                    "route_distance_km": round(summary["distance"] / 1000, 3),
                    "route_duration_min": round(summary["duration"] / 60, 2),
                    "route_status": "ok",
                }
            except (HTTPError, URLError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("카카오 길찾기 요청에 실패했습니다.")

    def routes(self, origin_lon: float, origin_lat: float, destinations: list[dict]) -> dict:
        """Return summaries from one origin to at most 30 destinations."""
        if not 1 <= len(destinations) <= 30:
            raise ValueError("다중 목적지는 1개 이상 30개 이하로 지정해야 합니다.")
        body = {
            "origin": {"x": origin_lon, "y": origin_lat},
            "destinations": [
                {
                    "key": str(destination["key"]),
                    "x": destination["longitude"],
                    "y": destination["latitude"],
                }
                for destination in destinations
            ],
            "radius": 10_000,
            "priority": "TIME",
        }
        request = Request(
            KAKAO_MULTI_DESTINATIONS_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"KakaoAK {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        for attempt in range(3):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    payload = json.load(response)
                results = {}
                for route in payload.get("routes", []):
                    key = str(route["key"])
                    if route.get("result_code") != 0:
                        results[key] = {
                            "route_distance_km": np.nan,
                            "route_duration_min": np.nan,
                            "route_status": route.get("result_msg", "no_route"),
                        }
                        continue
                    summary = route["summary"]
                    results[key] = {
                        "route_distance_km": round(summary["distance"] / 1000, 3),
                        "route_duration_min": round(summary["duration"] / 60, 2),
                        "route_status": "ok",
                    }
                return results
            except HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")
                try:
                    error_payload = json.loads(detail)
                except json.JSONDecodeError:
                    error_payload = {}
                if error_payload.get("code") == -10:
                    raise KakaoDailyQuotaExceeded(
                        "카카오 다중 목적지 길찾기 일일 쿼터를 모두 사용했습니다."
                    ) from error
                if 400 <= error.code < 500 and error.code != 429:
                    raise RuntimeError(
                        f"카카오 다중 목적지 요청 오류({error.code}): {detail}"
                    ) from error
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("카카오 다중 목적지 길찾기 요청에 실패했습니다.")


def _haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    value = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(
        (lon2 - lon1) / 2
    ) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(value))


def build_candidate_pairs(
    demand_points: pd.DataFrame, hospitals: pd.DataFrame, candidate_count: int = 5
) -> pd.DataFrame:
    """Select nearby hospitals cheaply before requesting road routes."""
    facilities = hospitals.copy()
    if "closure_candidate" in facilities:
        facilities = facilities[facilities["closure_candidate"]].copy()
    if facilities.empty:
        raise ValueError("길찾기 대상 병원급 의료기관이 없습니다.")

    distances = _haversine(
        demand_points["latitude"].to_numpy()[:, None],
        demand_points["longitude"].to_numpy()[:, None],
        facilities["latitude"].to_numpy()[None, :],
        facilities["longitude"].to_numpy()[None, :],
    )
    count = min(candidate_count, len(facilities))
    nearest = np.argpartition(distances, count - 1, axis=1)[:, :count]
    rows = []
    facilities = facilities.reset_index(drop=True)
    for point_index, facility_indexes in enumerate(nearest):
        point = demand_points.iloc[point_index]
        ordered = facility_indexes[np.argsort(distances[point_index, facility_indexes])]
        for facility_index in ordered:
            hospital = facilities.iloc[facility_index]
            rows.append(
                {
                    "demand_id": str(point["demand_id"]),
                    "hospital_id": str(hospital["hospital_id"]),
                    "origin_latitude": float(point["latitude"]),
                    "origin_longitude": float(point["longitude"]),
                    "destination_latitude": float(hospital["latitude"]),
                    "destination_longitude": float(hospital["longitude"]),
                    "straight_distance_km": round(float(distances[point_index, facility_index]), 3),
                }
            )
    return pd.DataFrame(rows)


def collect_route_matrix(
    demand_points: pd.DataFrame,
    hospitals: pd.DataFrame,
    client: KakaoDirectionsClient,
    cache_path: str | Path,
    candidate_count: int = 30,
    daily_origin_limit: int = 1_000,
) -> pd.DataFrame:
    """Collect one resumable daily batch with Kakao multi-destination routing."""
    if daily_origin_limit < 1:
        raise ValueError("daily_origin_limit은 1 이상이어야 합니다.")
    if not 1 <= candidate_count <= 30:
        raise ValueError("candidate_count는 카카오 다중 목적지 제한에 따라 1~30이어야 합니다.")
    cache_path = Path(cache_path)
    pairs = build_candidate_pairs(demand_points, hospitals, candidate_count)
    if cache_path.exists():
        cached = pd.read_csv(cache_path, dtype={"demand_id": str, "hospital_id": str})
    else:
        cached = pd.DataFrame(columns=ROUTE_COLUMNS)
    completed = set(zip(cached["demand_id"].astype(str), cached["hospital_id"].astype(str)))
    new_rows = []
    processed_origins = 0

    try:
        for demand_id, group in pairs.groupby("demand_id", sort=False):
            group_keys = {
                (str(pair.demand_id), str(pair.hospital_id))
                for pair in group.itertuples(index=False)
            }
            if group_keys.issubset(completed):
                continue
            if processed_origins >= daily_origin_limit:
                break

            pending = group[
                [
                    (str(pair.demand_id), str(pair.hospital_id)) not in completed
                    for pair in group.itertuples(index=False)
                ]
            ]
            origin = pending.iloc[0]
            destinations = [
                {
                    "key": str(pair.hospital_id),
                    "longitude": pair.destination_longitude,
                    "latitude": pair.destination_latitude,
                }
                for pair in pending.itertuples(index=False)
            ]
            try:
                results = client.routes(
                    float(origin["origin_longitude"]),
                    float(origin["origin_latitude"]),
                    destinations,
                )
            except KakaoDailyQuotaExceeded:
                print("카카오 일일 쿼터에 도달해 오늘 수집을 종료합니다.")
                break
            collected_at = datetime.now(timezone.utc).isoformat()
            for pair in pending.itertuples(index=False):
                hospital_id = str(pair.hospital_id)
                result = results.get(
                    hospital_id,
                    {
                        "route_distance_km": np.nan,
                        "route_duration_min": np.nan,
                        "route_status": "missing_response",
                    },
                )
                new_rows.append(
                    {
                        "demand_id": str(demand_id),
                        "hospital_id": hospital_id,
                        "straight_distance_km": pair.straight_distance_km,
                        **result,
                        "collected_at": collected_at,
                    }
                )
            completed.update(
                (str(pair.demand_id), str(pair.hospital_id))
                for pair in pending.itertuples(index=False)
            )
            processed_origins += 1
            if processed_origins % 25 == 0:
                cached = _save_cache(cache_path, cached, new_rows)
                new_rows = []
                print(
                    f"카카오 경로: 오늘 {processed_origins:,}개, "
                    f"누적 경로 {len(cached):,}/{len(pairs):,}건"
                )
    finally:
        if new_rows:
            cached = _save_cache(cache_path, cached, new_rows)

    cached = cached.drop_duplicates(["demand_id", "hospital_id"], keep="last")
    expected = set(zip(pairs["demand_id"].astype(str), pairs["hospital_id"].astype(str)))
    actual = set(zip(cached["demand_id"].astype(str), cached["hospital_id"].astype(str)))
    collection_complete = expected.issubset(actual)
    completed_origins = sum(
        {
            (str(pair.demand_id), str(pair.hospital_id))
            for pair in group.itertuples(index=False)
        }.issubset(actual)
        for _, group in pairs.groupby("demand_id", sort=False)
    )
    if collection_complete:
        cached = impute_unroutable_origins(cached, pairs, demand_points)
    cached.to_csv(cache_path, index=False, encoding="utf-8")
    cached.attrs["collection_complete"] = collection_complete
    cached.attrs["processed_origins"] = processed_origins
    cached.attrs["completed_origins"] = completed_origins
    cached.attrs["total_origins"] = pairs["demand_id"].nunique()
    return cached


def _save_cache(cache_path: Path, cached: pd.DataFrame, rows: list[dict]) -> pd.DataFrame:
    new = pd.DataFrame(rows)
    combined = new if cached.empty else pd.concat([cached, new], ignore_index=True)
    combined = combined.drop_duplicates(["demand_id", "hospital_id"], keep="last")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(cache_path, index=False, encoding="utf-8")
    return combined


def impute_unroutable_origins(
    route_matrix: pd.DataFrame, pairs: pd.DataFrame, demand_points: pd.DataFrame
) -> pd.DataFrame:
    """Estimate routes only when a polygon centroid has no nearby road."""
    routes = route_matrix.drop(columns=["straight_distance_km"], errors="ignore").merge(
        pairs[["demand_id", "hospital_id", "straight_distance_km"]],
        on=["demand_id", "hospital_id"],
        how="left",
        validate="one_to_one",
    )
    point_regions = demand_points[["demand_id", "region_code"]].copy()
    point_regions["demand_id"] = point_regions["demand_id"].astype(str)
    routes = routes.merge(point_regions, on="demand_id", how="left", validate="many_to_one")
    exact = routes[
        routes["route_status"].eq("ok")
        & routes["route_distance_km"].gt(0)
        & routes["straight_distance_km"].gt(0)
    ].copy()
    exact["distance_factor"] = exact["route_distance_km"] / exact["straight_distance_km"]
    exact["minutes_per_km"] = exact["route_duration_min"] / exact["route_distance_km"]
    regional = exact.groupby("region_code")[["distance_factor", "minutes_per_km"]].median()
    statewide = exact[["distance_factor", "minutes_per_km"]].median()

    missing = routes["route_distance_km"].isna()
    factors = routes["region_code"].map(regional["distance_factor"]).fillna(
        statewide["distance_factor"]
    )
    minutes = routes["region_code"].map(regional["minutes_per_km"]).fillna(
        statewide["minutes_per_km"]
    )
    routes.loc[missing, "route_distance_km"] = (
        routes.loc[missing, "straight_distance_km"] * factors[missing]
    ).round(3)
    routes.loc[missing, "route_duration_min"] = (
        routes.loc[missing, "route_distance_km"] * minutes[missing]
    ).round(2)
    routes.loc[missing, "route_status"] = "estimated_no_road_origin"
    return routes.drop(columns="region_code")


def summarize_route_access(route_matrix: pd.DataFrame, demand_points: pd.DataFrame) -> pd.DataFrame:
    valid = route_matrix[route_matrix["route_duration_min"].notna()].copy()
    valid = valid.sort_values("route_duration_min").groupby("demand_id", as_index=False).first()
    points = demand_points.copy()
    points["demand_id"] = points["demand_id"].astype(str)
    joined = points.merge(valid, on="demand_id", how="left", validate="one_to_one")
    missing = joined.loc[joined["route_duration_min"].isna(), "demand_id"].tolist()
    if missing:
        raise ValueError(f"유효한 자동차 경로가 없는 수요 지점이 있습니다: {missing[:5]}")

    rows = []
    for region_code, region in joined.groupby("region_code"):
        weights = region["population"].to_numpy()
        rows.append(
            {
                "region_code": int(region_code),
                "access_distance_km": round(
                    float(np.average(region["route_distance_km"], weights=weights)), 2
                ),
                "access_duration_min": round(
                    float(np.average(region["route_duration_min"], weights=weights)), 2
                ),
                "access_method": "kakao_car",
                "route_exact_share_pct": round(
                    float(np.average(region["route_status"].eq("ok") * 100, weights=weights)), 1
                ),
            }
        )
    return pd.DataFrame(rows)


def update_supply_with_routes(
    supply: pd.DataFrame, route_matrix: pd.DataFrame, demand_points: pd.DataFrame
) -> pd.DataFrame:
    access = summarize_route_access(route_matrix, demand_points)
    result = supply.drop(
        columns=[
            "access_distance_km",
            "access_duration_min",
            "access_method",
            "route_exact_share_pct",
        ],
        errors="ignore",
    ).merge(access, on="region_code", how="left", validate="one_to_one")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="카카오 자동차 이동거리·시간 수집")
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--candidate-count", type=int, default=30)
    parser.add_argument(
        "--daily-origin-limit",
        type=int,
        default=1_000,
        help="한 번 실행할 때 요청할 출발지 수(카카오 무료 일일 쿼터 기본값: 1,000)",
    )
    args = parser.parse_args()

    demand = pd.read_csv(args.data_dir / "demand_points.csv", dtype={"demand_id": str})
    hospitals = pd.read_csv(args.data_dir / "hospitals.csv", dtype={"hospital_id": str})
    cache_path = args.data_dir / "kakao_routes.csv"
    client = KakaoDirectionsClient(load_kakao_api_key(args.env))
    routes = collect_route_matrix(
        demand,
        hospitals,
        client,
        cache_path,
        args.candidate_count,
        args.daily_origin_limit,
    )
    if not routes.attrs["collection_complete"]:
        print(
            f"오늘 수집 완료: {routes.attrs['processed_origins']:,}개 출발지, "
            f"완전 수집 {routes.attrs['completed_origins']:,}/"
            f"{routes.attrs['total_origins']:,}개. "
            "다음 날 같은 명령을 다시 실행하면 이어서 수집합니다."
        )
        return
    supply_path = args.data_dir / "medical_supply.csv"
    supply = update_supply_with_routes(pd.read_csv(supply_path), routes, demand)
    supply.to_csv(supply_path, index=False, encoding="utf-8")
    print(f"전국 자동차 경로 {len(routes):,}건, 지역 접근성 {len(supply):,}개 갱신 완료")


if __name__ == "__main__":
    main()

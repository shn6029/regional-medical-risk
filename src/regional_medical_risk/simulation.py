import numpy as np
import pandas as pd

from .risk import score_regions


def simulate_hospital_closure(
    region: pd.Series | dict,
    hospitals: pd.DataFrame,
    hospital_id: str,
    demand_points: pd.DataFrame | None = None,
    route_matrix: pd.DataFrame | None = None,
) -> dict:
    """Remove one hospital and recompute access, supply, and risk."""
    region = pd.Series(region, dtype=object).copy()
    access_hospitals = hospitals.copy()
    if "closure_candidate" in access_hospitals:
        access_hospitals = access_hospitals[access_hospitals["closure_candidate"]].copy()
    region_hospitals = access_hospitals[
        access_hospitals["region_code"] == region["region_code"]
    ].copy()
    selected = region_hospitals[region_hospitals["hospital_id"] == hospital_id]
    if selected.empty:
        raise ValueError("선택한 의료기관이 해당 지역에 없습니다.")
    if len(region_hospitals) < 2:
        raise ValueError("마지막 의료기관은 폐업 시뮬레이션할 수 없습니다.")

    closed = selected.iloc[0]
    remaining = region_hospitals[region_hospitals["hospital_id"] != hospital_id]
    affected_population = None
    affected_senior_population = None
    baseline_duration = None
    scenario_duration = None
    if route_matrix is not None and demand_points is not None and not route_matrix.empty:
        points = demand_points[demand_points["region_code"] == region["region_code"]].copy()
        points["demand_id"] = points["demand_id"].astype(str)
        routes = route_matrix.copy()
        routes["demand_id"] = routes["demand_id"].astype(str)
        routes["hospital_id"] = routes["hospital_id"].astype(str)
        routes = routes[
            routes["demand_id"].isin(points["demand_id"])
            & routes["route_duration_min"].notna()
        ]
        best = routes.sort_values("route_duration_min").groupby("demand_id", as_index=False).first()
        after = routes[routes["hospital_id"] != str(hospital_id)]
        best_after = after.sort_values("route_duration_min").groupby("demand_id", as_index=False).first()
        access = points.merge(best, on="demand_id", how="left", validate="one_to_one")
        access_after = points.merge(
            best_after, on="demand_id", how="left", validate="one_to_one"
        )
        if access["route_duration_min"].isna().any() or access_after["route_duration_min"].isna().any():
            raise ValueError("폐업 전후 자동차 경로가 없는 수요 지점이 있습니다.")
        weights = points["population"].to_numpy()
        baseline_distance = float(np.average(access["route_distance_km"], weights=weights))
        scenario_distance = float(np.average(access_after["route_distance_km"], weights=weights))
        baseline_duration = float(np.average(access["route_duration_min"], weights=weights))
        scenario_duration = float(np.average(access_after["route_duration_min"], weights=weights))
        affected_ids = access.loc[
            access["hospital_id"].eq(str(hospital_id)), "demand_id"
        ]
        affected = points["demand_id"].isin(affected_ids)
        affected_population = round(float(points.loc[affected, "population"].sum()))
        affected_senior_population = round(
            float(points.loc[affected, "senior_population"].sum())
        )
    elif demand_points is not None and {"latitude", "longitude"}.issubset(access_hospitals):
        points = demand_points[demand_points["region_code"] == region["region_code"]]
        distances = _haversine(
            points["latitude"].to_numpy()[:, None],
            points["longitude"].to_numpy()[:, None],
            access_hospitals["latitude"].to_numpy()[None, :],
            access_hospitals["longitude"].to_numpy()[None, :],
        )
        closed_index = access_hospitals.index.get_loc(selected.index[0])
        nearest = distances.argmin(axis=1)
        weights = points["population"].to_numpy()
        baseline_distance = float(np.average(distances.min(axis=1), weights=weights))
        scenario_distance = float(
            np.average(np.delete(distances, closed_index, axis=1).min(axis=1), weights=weights)
        )
        affected = nearest == closed_index
        affected_population = round(float(points.loc[affected, "population"].sum()))
        affected_senior_population = round(
            float(points.loc[affected, "senior_population"].sum())
        )
    else:
        baseline_distance = float(region_hospitals["distance_km"].min())
        scenario_distance = float(remaining["distance_km"].min())

    baseline = region.copy()
    baseline["access_distance_km"] = baseline_distance
    scenario = region.copy()
    scenario["hospital_count"] = int(region["hospital_count"]) - 1
    scenario["hospital_beds"] = max(0, int(region["hospital_beds"]) - int(closed["beds"]))
    scenario["access_distance_km"] = scenario_distance
    scenario["facilities_per_1000"] = scenario["hospital_count"] / scenario["population"] * 1000

    before_score = float(score_regions(pd.DataFrame([baseline])).iloc[0]["risk_score"])
    after_score = float(score_regions(pd.DataFrame([scenario])).iloc[0]["risk_score"])
    if affected_population is None:
        total_beds = float(region["hospital_beds"])
        bed_share = float(closed["beds"] / total_beds) if total_beds > 0 else 0.0
        affected_population = round(float(region["population"]) * bed_share)
        affected_senior_population = round(float(region["senior_population"]) * bed_share)

    return {
        "hospital_name": closed["hospital_name"],
        "hospital_count_before": int(region["hospital_count"]),
        "hospital_count_after": int(scenario["hospital_count"]),
        "access_distance_before": round(baseline_distance, 1),
        "access_distance_after": round(scenario_distance, 1),
        "access_duration_before": round(baseline_duration, 1) if baseline_duration is not None else None,
        "access_duration_after": round(scenario_duration, 1) if scenario_duration is not None else None,
        "risk_before": before_score,
        "risk_after": after_score,
        "affected_population": affected_population,
        "affected_senior_population": affected_senior_population,
    }


def _haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    value = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(
        (lon2 - lon1) / 2
    ) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(value))

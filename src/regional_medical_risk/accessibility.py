from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_2sfca(
    demand_points: pd.DataFrame,
    hospitals: pd.DataFrame,
    route_matrix: pd.DataFrame,
    catchment_minutes: float = 30,
    demand_column: str = "senior_population",
    supply_column: str = "beds",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate demand-point and regional 2SFCA accessibility within a time threshold."""
    if catchment_minutes <= 0:
        raise ValueError("catchment_minutes는 0보다 커야 합니다.")
    _require_columns(
        demand_points,
        {"demand_id", "region_code", "population", demand_column},
        "demand_points",
    )
    _require_columns(hospitals, {"hospital_id", supply_column}, "hospitals")
    _require_columns(
        route_matrix,
        {"demand_id", "hospital_id", "route_duration_min"},
        "route_matrix",
    )

    demand = demand_points.copy()
    demand["demand_id"] = demand["demand_id"].astype(str)
    facilities = hospitals.copy()
    facilities["hospital_id"] = facilities["hospital_id"].astype(str)
    if "closure_candidate" in facilities:
        facilities = facilities[facilities["closure_candidate"]].copy()
    facilities[supply_column] = pd.to_numeric(
        facilities[supply_column], errors="coerce"
    ).fillna(0)

    routes = route_matrix.copy()
    routes["demand_id"] = routes["demand_id"].astype(str)
    routes["hospital_id"] = routes["hospital_id"].astype(str)
    routes = routes.dropna(subset=["route_duration_min"])
    routes = routes.sort_values("route_duration_min").drop_duplicates(
        ["demand_id", "hospital_id"], keep="first"
    )
    routes = routes[routes["route_duration_min"].le(catchment_minutes)].copy()
    routes = routes.merge(
        demand[["demand_id", demand_column]],
        on="demand_id",
        how="inner",
        validate="many_to_one",
    )
    routes = routes.merge(
        facilities[["hospital_id", supply_column]],
        on="hospital_id",
        how="inner",
        validate="many_to_one",
    )
    routes[supply_column] = pd.to_numeric(routes[supply_column], errors="coerce").fillna(0)

    catchment_demand = routes.groupby("hospital_id")[demand_column].sum()
    capacity = facilities.set_index("hospital_id")[supply_column].reindex(catchment_demand.index)
    supply_ratio = (capacity / catchment_demand.replace(0, np.nan) * 1_000).fillna(0)
    routes["hospital_supply_ratio"] = routes["hospital_id"].map(supply_ratio)

    point_access = routes.groupby("demand_id").agg(
        accessible_hospital_count=("hospital_id", "nunique"),
        accessible_beds=(supply_column, "sum"),
        two_sfca_score=("hospital_supply_ratio", "sum"),
    )
    points = demand.merge(point_access, on="demand_id", how="left", validate="one_to_one")
    points[["accessible_hospital_count", "accessible_beds", "two_sfca_score"]] = points[
        ["accessible_hospital_count", "accessible_beds", "two_sfca_score"]
    ].fillna(0)
    points["within_30min"] = points["accessible_hospital_count"].gt(0)
    points["accessible_hospital_count"] = points["accessible_hospital_count"].astype(int)

    regional_rows = []
    for region_code, region in points.groupby("region_code"):
        population = region["population"].sum()
        target_population = region[demand_column].sum()
        covered = region["within_30min"]
        regional_rows.append(
            {
                "region_code": region_code,
                "population": population,
                "population_within_30min": region.loc[covered, "population"].sum(),
                "population_within_30min_pct": _percentage(
                    region.loc[covered, "population"].sum(), population
                ),
                demand_column: target_population,
                f"{demand_column}_within_30min": region.loc[covered, demand_column].sum(),
                f"{demand_column}_within_30min_pct": _percentage(
                    region.loc[covered, demand_column].sum(), target_population
                ),
                "two_sfca_score": _weighted_average(
                    region["two_sfca_score"], region[demand_column]
                ),
            }
        )
    return points, pd.DataFrame(regional_rows)


def _weighted_average(values: pd.Series, weights: pd.Series) -> float:
    if weights.sum() <= 0:
        return 0.0
    return round(float(np.average(values, weights=weights)), 2)


def _percentage(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator / denominator * 100), 1)


def _require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{name}에 필수 열이 없습니다: {sorted(missing)}")

from pathlib import Path

import pandas as pd


REQUIRED_POPULATION_COLUMNS = {
    "region_code",
    "region_name",
    "year",
    "population",
    "senior_population",
    "youth_population",
}
REQUIRED_SUPPLY_COLUMNS = {
    "region_code",
    "latitude",
    "longitude",
    "hospital_count",
    "hospital_beds",
    "access_distance_km",
}
REQUIRED_HOSPITAL_COLUMNS = {
    "hospital_id",
    "hospital_name",
    "region_code",
    "beds",
    "latitude",
    "longitude",
}
REQUIRED_DEMAND_COLUMNS = {
    "region_code",
    "demand_id",
    "population",
    "senior_population",
    "latitude",
    "longitude",
}


def load_demo_data(data_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the bundled portfolio dataset."""
    data_dir = Path(data_dir)
    population = pd.read_csv(data_dir / "historical_population.csv")
    supply = pd.read_csv(data_dir / "medical_supply.csv")
    hospitals = pd.read_csv(data_dir / "hospitals.csv")
    _require_columns(population, REQUIRED_POPULATION_COLUMNS, "historical_population.csv")
    _require_columns(supply, REQUIRED_SUPPLY_COLUMNS, "medical_supply.csv")
    _require_columns(hospitals, REQUIRED_HOSPITAL_COLUMNS, "hospitals.csv")
    return population, supply, hospitals


def load_demand_points(data_dir: str | Path) -> pd.DataFrame:
    demand = pd.read_csv(Path(data_dir) / "demand_points.csv")
    _require_columns(demand, REQUIRED_DEMAND_COLUMNS, "demand_points.csv")
    return demand


def load_route_matrix(data_dir: str | Path) -> pd.DataFrame | None:
    path = Path(data_dir) / "kakao_routes.csv"
    if not path.exists():
        return None
    routes = pd.read_csv(path, dtype={"demand_id": str, "hospital_id": str})
    _require_columns(
        routes,
        {"demand_id", "hospital_id", "route_distance_km", "route_duration_min"},
        "kakao_routes.csv",
    )
    return routes


def build_latest_snapshot(population: pd.DataFrame, supply: pd.DataFrame) -> pd.DataFrame:
    """Join the latest population year with medical supply by region code."""
    ordered = population.sort_values(["region_code", "year"]).copy()
    latest = ordered.groupby("region_code", as_index=False).tail(1).copy()
    prior = ordered[["region_code", "year", "population"]].copy()
    prior["year"] += 5
    prior = prior.rename(columns={"population": "population_5y_prior"})
    latest = latest.merge(prior, on=["region_code", "year"], how="left", validate="one_to_one")
    if latest["population_5y_prior"].isna().any():
        raise ValueError("최신 연도의 정확히 5년 전 인구가 없습니다.")
    latest["population_change_5y_pct"] = (
        (latest["population"] / latest["population_5y_prior"] - 1) * 100
    )
    latest["aging_rate"] = latest["senior_population"] / latest["population"] * 100

    snapshot = latest.merge(supply, on="region_code", how="inner", validate="one_to_one")
    snapshot["facilities_per_1000"] = snapshot["hospital_count"] / snapshot["population"] * 1000
    return snapshot.drop(columns=["population_5y_prior"])


def _require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{name}에 필수 열이 없습니다: {sorted(missing)}")

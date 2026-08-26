from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .data import build_latest_snapshot, load_demo_data
from .etl import HOSPITAL_TYPES, _map_hira_regions, prepare_hospitals
from .risk import score_regions
from .simulation import simulate_hospital_closure


def _read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError(f"CSV 인코딩을 확인할 수 없습니다: {path}")


def _name_key(value: object) -> str:
    return "".join(character.lower() for character in str(value) if character.isalnum())


def load_closures(path: str | Path, regions: pd.DataFrame) -> pd.DataFrame:
    frame = _read_csv(Path(path)).rename(
        columns={
            "요양기관명": "hospital_name",
            "요양종별": "hospital_type",
            "시도명": "province_name",
            "시군구명": "district_name",
            "폐업일자": "closed_on",
        }
    )
    required = {"hospital_name", "hospital_type", "province_name", "district_name", "closed_on"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"폐업 CSV 필수 열이 없습니다: {sorted(missing)}")
    frame["closed_on"] = pd.to_datetime(frame["closed_on"], errors="coerce")
    mapping_source = frame.rename(
        columns={"province_name": "시도코드명", "district_name": "시군구코드명"}
    )
    frame["region_code"] = _map_hira_regions(mapping_source, regions)
    names = regions[["region_code", "region_name"]].drop_duplicates()
    frame = frame.merge(names, on="region_code", how="left", validate="many_to_one")
    frame["name_key"] = frame["hospital_name"].map(_name_key)
    return frame.dropna(subset=["closed_on", "region_code"])


def match_actual_closures(
    baseline: pd.DataFrame,
    comparison: pd.DataFrame,
    closures: pd.DataFrame,
    baseline_date: str,
    comparison_date: str,
) -> pd.DataFrame:
    actual = closures[
        closures["closed_on"].gt(pd.Timestamp(baseline_date))
        & closures["closed_on"].le(pd.Timestamp(comparison_date))
        & closures["hospital_type"].isin(HOSPITAL_TYPES)
    ].copy()
    actual = actual.sort_values("closed_on").drop_duplicates(
        ["name_key", "hospital_type", "region_code"], keep="last"
    )
    before = baseline[baseline["closure_candidate"]].copy()
    after = comparison[comparison["closure_candidate"]].copy()
    before["name_key"] = before["hospital_name"].map(_name_key)
    after["name_key"] = after["hospital_name"].map(_name_key)

    matches = before.merge(
        actual[["name_key", "hospital_type", "region_code", "closed_on"]],
        on=["name_key", "hospital_type", "region_code"],
        how="inner",
        validate="many_to_one",
    )
    still_open = set(
        zip(after["name_key"], after["hospital_type"], after["region_code"].astype(int))
    )
    matches = matches[
        ~matches.apply(
            lambda row: (row["name_key"], row["hospital_type"], int(row["region_code"]))
            in still_open,
            axis=1,
        )
    ]
    return matches.drop_duplicates("hospital_id")


def _weighted_access(hospitals: pd.DataFrame, points: pd.DataFrame) -> float:
    lat1 = np.radians(points["latitude"].to_numpy()[:, None])
    lon1 = np.radians(points["longitude"].to_numpy()[:, None])
    lat2 = np.radians(hospitals["latitude"].to_numpy()[None, :])
    lon2 = np.radians(hospitals["longitude"].to_numpy()[None, :])
    value = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(
        (lon2 - lon1) / 2
    ) ** 2
    distances = 6371.0 * 2 * np.arcsin(np.sqrt(value))
    return float(np.average(distances.min(axis=1), weights=points["population"]))


def _direction(delta: float, tolerance_km: float = 0.1) -> str:
    if delta > tolerance_km:
        return "increase"
    if delta < -tolerance_km:
        return "decrease"
    return "stable"


def validate_actual_closures(
    baseline: pd.DataFrame,
    comparison: pd.DataFrame,
    closures: pd.DataFrame,
    demand_points: pd.DataFrame,
    snapshot: pd.DataFrame,
    baseline_date: str,
    comparison_date: str,
) -> pd.DataFrame:
    matches = match_actual_closures(
        baseline, comparison, closures, baseline_date, comparison_date
    )
    baseline_candidates = baseline[baseline["closure_candidate"]].copy()
    comparison_candidates = comparison[comparison["closure_candidate"]].copy()
    rows = []
    for closed in matches.itertuples(index=False):
        region_code = int(closed.region_code)
        before = baseline_candidates[baseline_candidates["region_code"].eq(region_code)]
        after = comparison_candidates[comparison_candidates["region_code"].eq(region_code)]
        points = demand_points[demand_points["region_code"].eq(region_code)]
        if len(before) < 2 or after.empty or points.empty:
            continue

        region = snapshot[snapshot["region_code"].eq(region_code)].iloc[0].copy()
        region["hospital_count"] = len(before)
        region["hospital_beds"] = int(before["beds"].sum())
        region["facilities_per_1000"] = len(before) / region["population"] * 1000
        result = simulate_hospital_closure(
            region, baseline_candidates, str(closed.hospital_id), demand_points
        )
        baseline_access = _weighted_access(baseline_candidates, points)
        simulated_access = _weighted_access(
            baseline_candidates[
                baseline_candidates["hospital_id"].astype(str).ne(str(closed.hospital_id))
            ],
            points,
        )
        observed_access = _weighted_access(comparison_candidates, points)
        actual_region = region.copy()
        actual_region["hospital_count"] = len(after)
        actual_region["hospital_beds"] = int(after["beds"].sum())
        actual_region["facilities_per_1000"] = len(after) / region["population"] * 1000
        actual_region["access_distance_km"] = observed_access
        observed_risk = float(score_regions(pd.DataFrame([actual_region])).iloc[0]["risk_score"])
        predicted_delta = simulated_access - baseline_access
        observed_delta = observed_access - baseline_access
        predicted_direction = _direction(predicted_delta)
        observed_direction = _direction(observed_delta)
        rows.append(
            {
                "hospital_id": str(closed.hospital_id),
                "hospital_name": closed.hospital_name,
                "hospital_type": closed.hospital_type,
                "region_code": region_code,
                "closed_on": pd.Timestamp(closed.closed_on).date().isoformat(),
                "baseline_date": baseline_date,
                "comparison_date": comparison_date,
                "predicted_distance_delta_km": round(predicted_delta, 2),
                "observed_distance_delta_km": round(observed_delta, 2),
                "predicted_direction": predicted_direction,
                "observed_direction": observed_direction,
                "direction_agreement": predicted_direction == observed_direction,
                "predicted_risk_delta": round(result["risk_after"] - result["risk_before"], 1),
                "observed_risk_delta": round(observed_risk - result["risk_before"], 1),
                "affected_population": result["affected_population"],
                "affected_senior_population": result["affected_senior_population"],
                "hospital_count_before": len(before),
                "hospital_count_observed": len(after),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="실제 병원 폐업 사례로 What-if 결과 검증")
    parser.add_argument("--closures", type=Path, required=True)
    parser.add_argument("--baseline-zip", type=Path, required=True)
    parser.add_argument("--comparison-zip", type=Path, required=True)
    parser.add_argument("--baseline-date", default="2023-12-31")
    parser.add_argument("--comparison-date", default="2024-12-31")
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/closure_validation.csv"))
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()

    population, supply, _ = load_demo_data(args.data_dir)
    regions = (
        population.sort_values("year")
        .groupby("region_code", as_index=False)
        .tail(1)[["region_code", "region_name", "province_name"]]
    )
    baseline = prepare_hospitals(args.baseline_zip, regions)
    comparison = prepare_hospitals(args.comparison_zip, regions)
    closures = load_closures(args.closures, regions)
    snapshot = score_regions(build_latest_snapshot(population, supply))
    demand = pd.read_csv(args.data_dir / "demand_points.csv")
    result = validate_actual_closures(
        baseline,
        comparison,
        closures,
        demand,
        snapshot,
        args.baseline_date,
        args.comparison_date,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.append and args.output.exists():
        previous = pd.read_csv(args.output, dtype={"hospital_id": str})
        result = pd.concat([previous, result], ignore_index=True).drop_duplicates(
            ["hospital_id", "closed_on"], keep="last"
        )
    result.to_csv(args.output, index=False, encoding="utf-8")
    agreement = result["direction_agreement"].mean() * 100 if not result.empty else 0
    print(f"실제 폐업 검증 {len(result)}건, 접근성 변화 방향 일치율 {agreement:.1f}%")


if __name__ == "__main__":
    main()

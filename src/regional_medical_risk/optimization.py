from __future__ import annotations

import numpy as np
import pandas as pd


def optimize_facility_locations(
    demand_points: pd.DataFrame,
    baseline_times: pd.DataFrame,
    candidate_times: pd.DataFrame,
    k: int,
    threshold_minutes: float = 30,
    weight_column: str = "senior_population",
) -> tuple[pd.DataFrame, dict]:
    """Greedily choose up to K sites that maximize population-weighted time savings."""
    if k < 1:
        raise ValueError("k는 1 이상이어야 합니다.")
    demand, baseline, matrix, candidate_ids = _prepare_inputs(
        demand_points, baseline_times, candidate_times, weight_column
    )
    if k > len(candidate_ids):
        raise ValueError("k는 후보 입지 수보다 클 수 없습니다.")

    weights = demand[weight_column].to_numpy(dtype=float)
    current = baseline.copy()
    selected_indexes: list[int] = []
    rows = []
    cumulative_weighted_minutes = 0.0

    for rank in range(1, k + 1):
        improvements = np.maximum(0, current[:, None] - matrix)
        benefits = (improvements * weights[:, None]).sum(axis=0)
        if selected_indexes:
            benefits[selected_indexes] = -np.inf
        best_index = int(np.argmax(benefits))
        best_benefit = float(benefits[best_index])
        if not np.isfinite(best_benefit) or best_benefit <= 0:
            break

        selected_indexes.append(best_index)
        current = np.minimum(current, matrix[:, best_index])
        cumulative_weighted_minutes += best_benefit
        metrics = _plan_metrics(demand, baseline, current, threshold_minutes, weight_column)
        rows.append(
            {
                "rank": rank,
                "candidate_id": candidate_ids[best_index],
                "incremental_weighted_minutes_saved": round(best_benefit),
                "cumulative_weighted_minutes_saved": round(cumulative_weighted_minutes),
                **metrics,
            }
        )

    selected = pd.DataFrame(rows)
    final_metrics = _plan_metrics(demand, baseline, current, threshold_minutes, weight_column)
    final_metrics["selected_count"] = len(selected_indexes)
    final_metrics["selected_candidate_ids"] = [candidate_ids[index] for index in selected_indexes]
    return selected, final_metrics


def evaluate_location_plan(
    demand_points: pd.DataFrame,
    baseline_times: pd.DataFrame,
    candidate_times: pd.DataFrame,
    selected_candidate_ids: list[str],
    threshold_minutes: float = 30,
    weight_column: str = "senior_population",
) -> dict:
    """Evaluate a fixed candidate set for random and population-priority baselines."""
    demand, baseline, matrix, candidate_ids = _prepare_inputs(
        demand_points, baseline_times, candidate_times, weight_column
    )
    index_by_id = {candidate_id: index for index, candidate_id in enumerate(candidate_ids)}
    missing = set(map(str, selected_candidate_ids)).difference(index_by_id)
    if missing:
        raise ValueError(f"후보 이동시간이 없는 입지입니다: {sorted(missing)}")
    selected_indexes = [index_by_id[str(candidate_id)] for candidate_id in selected_candidate_ids]
    current = baseline.copy()
    if selected_indexes:
        current = np.minimum(current, matrix[:, selected_indexes].min(axis=1))
    metrics = _plan_metrics(demand, baseline, current, threshold_minutes, weight_column)
    metrics["selected_count"] = len(selected_indexes)
    metrics["selected_candidate_ids"] = [candidate_ids[index] for index in selected_indexes]
    return metrics


def baseline_candidate_sets(
    candidate_sites: pd.DataFrame,
    k: int,
    population_column: str = "senior_population",
    random_state: int = 42,
) -> dict[str, list[str]]:
    """Create deterministic random and population-priority comparison sets."""
    _require_columns(candidate_sites, {"candidate_id", population_column}, "candidate_sites")
    if not 1 <= k <= len(candidate_sites):
        raise ValueError("k는 1 이상이고 후보 입지 수 이하여야 합니다.")
    sites = candidate_sites.copy()
    sites["candidate_id"] = sites["candidate_id"].astype(str)
    population_priority = sites.nlargest(k, population_column)["candidate_id"].tolist()
    random_selection = sites.sample(n=k, random_state=random_state)["candidate_id"].tolist()
    return {
        "population_priority": population_priority,
        "random": random_selection,
    }


def _prepare_inputs(
    demand_points: pd.DataFrame,
    baseline_times: pd.DataFrame,
    candidate_times: pd.DataFrame,
    weight_column: str,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, list[str]]:
    _require_columns(
        demand_points,
        {"demand_id", "population", weight_column},
        "demand_points",
    )
    _require_columns(
        baseline_times,
        {"demand_id", "baseline_duration_min"},
        "baseline_times",
    )
    _require_columns(
        candidate_times,
        {"demand_id", "candidate_id", "duration_min"},
        "candidate_times",
    )
    demand = demand_points.copy()
    demand["demand_id"] = demand["demand_id"].astype(str)
    baseline_frame = baseline_times.copy()
    baseline_frame["demand_id"] = baseline_frame["demand_id"].astype(str)
    joined = demand.merge(
        baseline_frame[["demand_id", "baseline_duration_min"]],
        on="demand_id",
        how="left",
        validate="one_to_one",
    )
    if joined["baseline_duration_min"].isna().any():
        raise ValueError("모든 수요 지점에 현재 병원 접근시간이 필요합니다.")

    times = candidate_times.copy()
    times["demand_id"] = times["demand_id"].astype(str)
    times["candidate_id"] = times["candidate_id"].astype(str)
    pivot = times.pivot_table(
        index="demand_id", columns="candidate_id", values="duration_min", aggfunc="min"
    ).reindex(joined["demand_id"])
    candidate_ids = [str(candidate_id) for candidate_id in pivot.columns]
    if not candidate_ids:
        raise ValueError("신규 의료시설 후보 이동시간이 없습니다.")
    return (
        joined,
        joined["baseline_duration_min"].to_numpy(dtype=float),
        pivot.to_numpy(dtype=float, na_value=np.inf),
        candidate_ids,
    )


def _plan_metrics(
    demand: pd.DataFrame,
    baseline: np.ndarray,
    current: np.ndarray,
    threshold_minutes: float,
    weight_column: str,
) -> dict:
    weights = demand[weight_column].to_numpy(dtype=float)
    population = demand["population"].to_numpy(dtype=float)
    improved = current < baseline
    before_over = baseline > threshold_minutes
    after_over = current > threshold_minutes
    return {
        "weighted_mean_duration_before": _weighted_mean(baseline, weights),
        "weighted_mean_duration_after": _weighted_mean(current, weights),
        "weighted_mean_duration_reduction": round(
            _weighted_mean(baseline, weights) - _weighted_mean(current, weights), 2
        ),
        "improved_population": round(float(population[improved].sum())),
        "improved_senior_population": round(float(weights[improved].sum())),
        "population_over_30min_before": round(float(population[before_over].sum())),
        "population_over_30min_after": round(float(population[after_over].sum())),
        "senior_population_over_30min_before": round(float(weights[before_over].sum())),
        "senior_population_over_30min_after": round(float(weights[after_over].sum())),
    }


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    if weights.sum() <= 0:
        return 0.0
    return round(float(np.average(values, weights=weights)), 2)


def _require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{name}에 필수 열이 없습니다: {sorted(missing)}")

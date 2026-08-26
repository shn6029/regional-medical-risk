import pandas as pd

from regional_medical_risk.optimization import (
    baseline_candidate_sets,
    evaluate_location_plan,
    optimize_facility_locations,
)


def _fixtures():
    demand = pd.DataFrame(
        [
            {"demand_id": "D1", "population": 1_000, "senior_population": 100},
            {"demand_id": "D2", "population": 1_000, "senior_population": 100},
            {"demand_id": "D3", "population": 1_000, "senior_population": 100},
        ]
    )
    baseline = pd.DataFrame(
        [
            {"demand_id": "D1", "baseline_duration_min": 50},
            {"demand_id": "D2", "baseline_duration_min": 45},
            {"demand_id": "D3", "baseline_duration_min": 10},
        ]
    )
    candidate_times = pd.DataFrame(
        [
            {"demand_id": "D1", "candidate_id": "A", "duration_min": 10},
            {"demand_id": "D2", "candidate_id": "A", "duration_min": 40},
            {"demand_id": "D3", "candidate_id": "A", "duration_min": 15},
            {"demand_id": "D1", "candidate_id": "B", "duration_min": 45},
            {"demand_id": "D2", "candidate_id": "B", "duration_min": 10},
            {"demand_id": "D3", "candidate_id": "B", "duration_min": 15},
        ]
    )
    return demand, baseline, candidate_times


def test_greedy_optimizer_selects_sites_by_incremental_time_savings():
    demand, baseline, candidate_times = _fixtures()

    selected, metrics = optimize_facility_locations(
        demand, baseline, candidate_times, k=2
    )

    assert selected["candidate_id"].tolist() == ["A", "B"]
    assert selected["incremental_weighted_minutes_saved"].tolist() == [4_500, 3_000]
    assert metrics["weighted_mean_duration_before"] == 35
    assert metrics["weighted_mean_duration_after"] == 10
    assert metrics["population_over_30min_before"] == 2_000
    assert metrics["population_over_30min_after"] == 0


def test_fixed_plan_and_comparison_sets_are_reproducible():
    demand, baseline, candidate_times = _fixtures()
    metrics = evaluate_location_plan(demand, baseline, candidate_times, ["B"])
    candidates = pd.DataFrame(
        [
            {"candidate_id": "A", "senior_population": 50},
            {"candidate_id": "B", "senior_population": 100},
        ]
    )
    first = baseline_candidate_sets(candidates, k=1, random_state=7)
    second = baseline_candidate_sets(candidates, k=1, random_state=7)

    assert metrics["weighted_mean_duration_after"] == 21.67
    assert metrics["population_over_30min_after"] == 1_000
    assert first == second
    assert first["population_priority"] == ["B"]

import pandas as pd

from regional_medical_risk.risk import score_regions


def test_worse_inputs_produce_higher_risk_score():
    frame = pd.DataFrame(
        [
            {
                "region": "stable",
                "aging_rate": 24,
                "population_change_5y_pct": 1,
                "facilities_per_1000": 0.7,
                "access_distance_km": 2,
            },
            {
                "region": "vulnerable",
                "aging_rate": 42,
                "population_change_5y_pct": -18,
                "facilities_per_1000": 0.1,
                "access_distance_km": 9,
            },
        ]
    )

    result = score_regions(frame).set_index("region")

    assert result.loc["vulnerable", "risk_score"] > result.loc["stable", "risk_score"]
    assert result["risk_score"].between(0, 100).all()


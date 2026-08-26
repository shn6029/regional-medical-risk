from pathlib import Path

import pandas as pd

from regional_medical_risk.data import load_demo_data
from regional_medical_risk.forecast import (
    LAST_VALUE_BASELINE,
    LINEAR_TREND_BASELINE,
    _supervised,
    benchmark_models,
    forecast_population,
)


DATA_DIR = Path(__file__).parents[1] / "data" / "processed"


def test_benchmark_and_four_year_forecast_cover_every_region():
    population, _, _ = load_demo_data(DATA_DIR)

    benchmark = benchmark_models(population)
    forecast = forecast_population(population, years=4, model_name="Linear Regression")

    assert {LAST_VALUE_BASELINE, LINEAR_TREND_BASELINE, "Linear Regression", "Random Forest"}.issubset(
        set(benchmark["model"])
    )
    supervised = _supervised(population, "senior_population")
    holdout = supervised[supervised["year"].eq(supervised["year"].max())]
    expected_last_value_mae = (holdout["senior_population"] - holdout["lag_1"]).abs().mean()
    expected_trend_mae = (
        holdout["senior_population"] - (2 * holdout["lag_1"] - holdout["lag_2"]).clip(lower=0)
    ).abs().mean()
    by_model = benchmark.set_index("model")
    assert by_model.loc[LAST_VALUE_BASELINE, "mae"] == round(expected_last_value_mae)
    assert by_model.loc[LINEAR_TREND_BASELINE, "mae"] == round(expected_trend_mae)
    assert {"category", "vs_best_baseline_pct", "test_year"}.issubset(benchmark.columns)
    assert len(forecast) == population["region_code"].nunique() * 4
    assert forecast["year"].min() == population["year"].max() + 1
    assert (forecast["senior_population"] >= 0).all()


def test_supervised_lags_require_exact_prior_years():
    panel = pd.DataFrame(
        {
            "region_code": [1, 1, 1, 1],
            "region_name": ["A"] * 4,
            "year": [2020, 2021, 2023, 2024],
            "senior_population": [100, 110, 130, 140],
        }
    )

    result = _supervised(panel, "senior_population")

    assert result.empty


def test_linear_trend_baseline_extrapolates_recent_change():
    panel = pd.DataFrame(
        {
            "region_code": [1, 1, 1],
            "region_name": ["A"] * 3,
            "year": [2022, 2023, 2024],
            "senior_population": [100, 110, 125],
        }
    )

    forecast = forecast_population(
        panel, years=2, model_name=LINEAR_TREND_BASELINE
    )

    assert forecast["senior_population"].tolist() == [140, 155]

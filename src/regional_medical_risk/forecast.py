from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


FEATURE_COLUMNS = ["region_code", "year", "lag_1", "lag_2", "recent_change"]
LAST_VALUE_BASELINE = "Naive Baseline (Last Value)"
LINEAR_TREND_BASELINE = "Linear Trend Baseline"


def _supervised(panel: pd.DataFrame, target: str) -> pd.DataFrame:
    frame = panel.sort_values(["region_code", "year"]).copy()
    lag_1 = frame[["region_code", "year", target]].rename(columns={target: "lag_1"})
    lag_1["year"] += 1
    lag_2 = frame[["region_code", "year", target]].rename(columns={target: "lag_2"})
    lag_2["year"] += 2
    frame = frame.merge(lag_1, on=["region_code", "year"], how="left", validate="one_to_one")
    frame = frame.merge(lag_2, on=["region_code", "year"], how="left", validate="one_to_one")
    frame["recent_change"] = (frame["lag_1"] / frame["lag_2"] - 1).fillna(0)
    return frame.dropna(subset=["lag_1", "lag_2", target])


def _pipeline(regressor) -> Pipeline:
    preprocessing = ColumnTransformer(
        [("region", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["region_code"])],
        remainder="passthrough",
    )
    return Pipeline([("preprocess", preprocessing), ("model", regressor)])


def _models() -> dict[str, Pipeline]:
    models = {
        "Linear Regression": _pipeline(LinearRegression()),
        "Random Forest": _pipeline(
            RandomForestRegressor(n_estimators=160, min_samples_leaf=2, random_state=42)
        ),
    }
    try:
        from xgboost import XGBRegressor

        models["XGBoost"] = _pipeline(
            XGBRegressor(
                n_estimators=160,
                max_depth=3,
                learning_rate=0.04,
                objective="reg:squarederror",
                random_state=42,
                n_jobs=1,
            )
        )
    except ImportError:
        pass
    return models


def benchmark_models(panel: pd.DataFrame, target: str = "senior_population") -> pd.DataFrame:
    """Evaluate models on the latest year as a temporal holdout."""
    supervised = _supervised(panel, target)
    test_year = int(supervised["year"].max())
    train = supervised[supervised["year"] < test_year]
    test = supervised[supervised["year"] == test_year]
    if train.empty or test.empty:
        raise ValueError("시계열 홀드아웃 평가에 필요한 연도가 부족합니다.")

    linear_trend_prediction = np.maximum(0, 2 * test["lag_1"] - test["lag_2"])
    rows = [
        {
            "model": LAST_VALUE_BASELINE,
            "mae": mean_absolute_error(test[target], test["lag_1"]),
            "category": "Baseline",
        },
        {
            "model": LINEAR_TREND_BASELINE,
            "mae": mean_absolute_error(test[target], linear_trend_prediction),
            "category": "Baseline",
        }
    ]
    for name, model in _models().items():
        model.fit(train[FEATURE_COLUMNS], train[target])
        prediction = np.maximum(0, model.predict(test[FEATURE_COLUMNS]))
        rows.append(
            {
                "model": name,
                "mae": mean_absolute_error(test[target], prediction),
                "category": "ML",
            }
        )
    result = pd.DataFrame(rows)
    best_baseline_mae = result.loc[result["category"].eq("Baseline"), "mae"].min()
    result["vs_best_baseline_pct"] = (
        (best_baseline_mae - result["mae"]) / best_baseline_mae * 100
    ).round(1)
    result["test_year"] = test_year
    result["mae"] = result["mae"].round(0)
    return result.sort_values("mae").reset_index(drop=True)


def forecast_population(
    panel: pd.DataFrame,
    target: str = "senior_population",
    years: int = 4,
    model_name: str = "Random Forest",
) -> pd.DataFrame:
    """Fit on all history and recursively forecast each region."""
    if years < 1:
        raise ValueError("예측 기간은 1년 이상이어야 합니다.")
    supervised = _supervised(panel, target)
    models = _models()
    baseline_names = {LAST_VALUE_BASELINE, LINEAR_TREND_BASELINE, "Naive Baseline"}
    if model_name not in baseline_names and model_name not in models:
        raise ValueError(f"지원하지 않는 모델입니다: {model_name}")

    model = None
    if model_name not in baseline_names:
        model = models[model_name]
        model.fit(supervised[FEATURE_COLUMNS], supervised[target])

    predictions = []
    for region_code, history in panel.sort_values("year").groupby("region_code"):
        history = history.sort_values("year")
        values = history[target].astype(float).tolist()
        last_year = int(history["year"].max())
        region_name = history["region_name"].iloc[-1]
        for step in range(1, years + 1):
            forecast_year = last_year + step
            recent_change = values[-1] / values[-2] - 1 if values[-2] else 0
            features = pd.DataFrame(
                [{
                    "region_code": region_code,
                    "year": forecast_year,
                    "lag_1": values[-1],
                    "lag_2": values[-2],
                    "recent_change": recent_change,
                }]
            )
            if model_name == LINEAR_TREND_BASELINE:
                prediction = values[-1] + (values[-1] - values[-2])
            elif model is None:
                prediction = values[-1]
            else:
                prediction = float(model.predict(features)[0])
            prediction = max(0, round(prediction))
            values.append(prediction)
            predictions.append(
                {
                    "region_code": region_code,
                    "region_name": region_name,
                    "year": forecast_year,
                    target: prediction,
                    "kind": "예측",
                    "model": model_name,
                }
            )
    return pd.DataFrame(predictions)

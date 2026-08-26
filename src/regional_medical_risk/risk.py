import pandas as pd


REQUIRED_COLUMNS = {
    "aging_rate",
    "population_change_5y_pct",
    "facilities_per_1000",
    "access_distance_km",
}


def _scale(series: pd.Series, low: float, high: float, inverse: bool = False) -> pd.Series:
    scaled = ((series.astype(float) - low) / (high - low)).clip(0, 1)
    return 1 - scaled if inverse else scaled


def score_regions(frame: pd.DataFrame) -> pd.DataFrame:
    """Calculate a transparent 0-100 medical vulnerability index.

    Fixed policy bounds keep a region's score comparable before and after a
    what-if scenario. They are assumptions for the demo, not clinical cutoffs.
    """
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"취약도 산출에 필요한 열이 없습니다: {sorted(missing)}")

    scored = frame.copy()
    scored["aging_component"] = _scale(scored["aging_rate"], 20, 45)
    scored["decline_component"] = _scale(
        scored["population_change_5y_pct"], -20, 5, inverse=True
    )
    scored["supply_component"] = _scale(
        scored["facilities_per_1000"], 0.04, 0.20, inverse=True
    )
    scored["access_component"] = _scale(scored["access_distance_km"], 1, 10)

    scored["risk_score"] = (
        scored["aging_component"] * 0.25
        + scored["decline_component"] * 0.20
        + scored["supply_component"] * 0.25
        + scored["access_component"] * 0.30
    ).mul(100).round(1)
    scored["risk_level"] = pd.cut(
        scored["risk_score"],
        bins=[-1, 40, 60, 75, 101],
        labels=["안정", "관심", "주의", "위험"],
        right=False,
    ).astype(str)
    return scored

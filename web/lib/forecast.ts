/**
 * 고령인구 예측 모델 검증 결과 (데이터 서비스 계층).
 * ⚠️ MAE·시계열은 프로토타입용 샘플값이다.
 *
 * 핵심 결론: 복잡한 머신러닝 모델이 단순 선형추세 기준선보다 낫지 않았다.
 * 따라서 모델별 MAE는 기준선과 사실상 동등하거나 약간 나쁘게 구성했다.
 */

export interface ForecastModel {
  id: string
  /** 영문/기술 명칭. */
  name: string
  /** 한글 설명. */
  label: string
  /** 평균절대오차 (명). 낮을수록 좋음. */
  mae: number
  isBaseline: boolean
}

export const EVAL_YEAR = 2024

export const FORECAST_MODELS: ForecastModel[] = [
  { id: 'persistence', name: 'Persistence', label: '작년 값 유지', mae: 1180, isBaseline: true },
  { id: 'linear-trend', name: 'Linear Trend', label: '선형 추세 기준선', mae: 742, isBaseline: true },
  { id: 'linreg', name: 'Linear Regression', label: '선형회귀', mae: 758, isBaseline: false },
  { id: 'rf', name: 'Random Forest', label: 'Random Forest', mae: 811, isBaseline: false },
  { id: 'xgb', name: 'XGBoost', label: 'XGBoost', mae: 796, isBaseline: false },
]

/** 기본 선택 모델(대표). */
export const SELECTED_MODEL_ID = 'linreg'

export function bestBaseline(): ForecastModel {
  return FORECAST_MODELS.filter((m) => m.isBaseline).reduce((a, b) =>
    a.mae <= b.mae ? a : b,
  )
}

export function getModel(id: string): ForecastModel {
  return FORECAST_MODELS.find((m) => m.id === id) ?? FORECAST_MODELS[2]
}

/** 선택 모델의 기준선 대비 성능(%). 양수면 기준선보다 우수. */
export function improvementOverBaseline(modelId: string): number {
  const model = getModel(modelId)
  const baseline = bestBaseline()
  return Number((((baseline.mae - model.mae) / baseline.mae) * 100).toFixed(1))
}

export interface ForecastPoint {
  year: number
  actual: number | null
  predicted: number | null
}

/**
 * 전국 65세 이상 인구 실측(2016~2024) 및 예측(2024~2028) 시계열 — 샘플.
 * 예측 구간에는 불확실성 안내를 함께 표기한다(UI).
 */
export const FORECAST_SERIES: ForecastPoint[] = [
  { year: 2016, actual: 6_780_000, predicted: null },
  { year: 2017, actual: 7_120_000, predicted: null },
  { year: 2018, actual: 7_490_000, predicted: null },
  { year: 2019, actual: 7_850_000, predicted: null },
  { year: 2020, actual: 8_150_000, predicted: null },
  { year: 2021, actual: 8_570_000, predicted: null },
  { year: 2022, actual: 9_020_000, predicted: null },
  { year: 2023, actual: 9_510_000, predicted: null },
  { year: 2024, actual: 10_030_000, predicted: 10_010_000 },
  { year: 2025, actual: null, predicted: 10_520_000 },
  { year: 2026, actual: null, predicted: 11_010_000 },
  { year: 2027, actual: null, predicted: 11_480_000 },
  { year: 2028, actual: null, predicted: 11_930_000 },
]

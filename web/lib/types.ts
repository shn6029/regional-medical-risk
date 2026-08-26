/**
 * 기존 FastAPI 서버(`src/regional_medical_risk/api.py`)의 응답 스키마.
 * 백엔드는 새로 만들지 않으며, 아래 타입은 기존 API 응답을 그대로 반영한다.
 */

/** GET /api/v1/accessibility/latest */
export interface AccessibilitySummary {
  run_id: string
  method: string
  method_version: string
  catchment_minutes: number
  route_count: number
  parameters: Record<string, unknown>
  started_at: string | null
  completed_at: string | null
  demand_point_count: number
  covered_demand_count: number
  senior_population: number
  covered_senior_population: number
  senior_coverage_pct: number
}

/** GET /api/v1/accessibility/regions -> items[] */
export interface RegionScore {
  region_code: string
  province_name: string
  region_name: string
  center_latitude: number | null
  center_longitude: number | null
  population: number
  population_within_threshold: number
  population_within_threshold_pct: number
  senior_population: number
  senior_within_threshold: number
  senior_within_threshold_pct: number
  two_sfca_score: number
}

export interface RegionsResponse {
  run_id: string
  count: number
  items: RegionScore[]
}

/** GET /api/v1/accessibility/regions/{region_code} -> demand_points[] */
export interface DemandPoint {
  demand_id: string
  demand_name: string
  population: number
  senior_population: number
  latitude: number
  longitude: number
  accessible_hospital_count: number
  accessible_beds: number
  within_threshold: boolean
  two_sfca_score: number
}

export interface RegionDetail extends RegionScore {
  run_id: string
  demand_points: DemandPoint[]
}

export type RiskLevel = 'low' | 'mid' | 'high' | 'critical'

export interface RiskInfo {
  level: RiskLevel
  label: string
  /** CSS 변수 (UI 토큰). */
  color: string
  /** Leaflet SVG 등 CSS 변수를 못 쓰는 곳을 위한 구체 색상. */
  hex: string
}

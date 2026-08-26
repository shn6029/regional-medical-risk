/**
 * ── 데이터 서비스(어댑터) 계층 ──────────────────────────────────────────────
 * 이 파일은 화면이 사용하는 모든 지역 단위 데이터를 제공하는 단일 소스다.
 * 현재는 제공된 샘플 데이터를 반환하지만, 각 selector 함수를 FastAPI 호출로
 * 교체하면 UI 수정 없이 실제 백엔드와 연결할 수 있다.
 *
 * ⚠️ 지역 좌표는 공개된 지리 정보이며, 그 외 수치는 프로토타입용 "샘플"이다.
 *    전국 집계 KPI(NATIONAL / ACCESSIBILITY_KPI)만 명세에서 제공된 확정값이다.
 */

import { getRiskGrade } from './risk'
import type { RiskInfo } from './types'

/** 취약도 구성요인별 기여 점수(각 항목 ≤ 최대 배점, 합계 = total). */
export interface VulnerabilityBreakdown {
  aging: number
  decline: number
  supply: number
  access: number
  total: number
}

export interface Region {
  code: string
  province: string
  name: string
  lat: number
  lng: number
  population: number
  /** 최근 5년 인구 변화율(%). 음수는 감소. */
  populationChange5yr: number
  /** 65세 이상 비율(%). */
  agingRate: number
  /** 병원급 의료기관 수. */
  hospitalCount: number
  /** 평균 직선 접근거리(km). */
  avgAccessDistanceKm: number
  /** 평균 자동차 이동시간(분). */
  avgDriveMinutes: number
  /** 고령인구 30분 접근률(%). */
  seniorCoverage30min: number
  /** 2SFCA 접근성 점수. */
  twoSfcaScore: number
  vulnerability: VulnerabilityBreakdown
}

const v = (
  aging: number,
  decline: number,
  supply: number,
  access: number,
): VulnerabilityBreakdown => ({
  aging,
  decline,
  supply,
  access,
  total: Number((aging + decline + supply + access).toFixed(1)),
})

/**
 * 전국 집계 지표 — 서비스 명세에서 제공된 확정 샘플값.
 */
export const NATIONAL = {
  baseDate: {
    population: '2025년 기준',
    facility: '2025년 12월',
    district: '2025년',
  },
  analyzedRegions: 229,
  totalPopulation: 51_117_378,
  seniorRate: 21.2,
  hospitalCount: 3_405,
  cautionDangerRegions: 68,
  cautionDangerPct: 29.7,
  insight:
    '전국 229개 지역 중 68개 지역(29.7%)이 주의 또는 위험 단계이며, 고령화와 의료공급 부족이 주요 위험 요인입니다.',
} as const

/**
 * 2SFCA 접근성 전국 KPI — 명세 제공 확정 샘플값.
 * 실시간 API가 실패했을 때의 캐시/폴백 값으로도 사용한다.
 */
export const ACCESSIBILITY_KPI = {
  seniorAccess30min: 96.43,
  demandPoints: 3_559,
  regions: 229,
  routes: 106_770,
  estimatedRouteRatio: 40.85,
  updatedAt: '2025-12-31T00:00:00+09:00',
  definition:
    '병상 공급과 30분 생활권 내 잠재 수요 경쟁을 함께 반영한 의료 접근성 지표입니다.',
} as const

/**
 * 대표 지역 샘플 데이터. 도시(안정)부터 농·산·어촌(위험)까지 등급을 고루 포함한다.
 * 좌표는 실제 지리 정보, 그 외 값은 샘플이며 취약도 공식과 내부적으로 일관된다.
 */
const REGIONS: Region[] = [
  { code: '11680', province: '서울특별시', name: '강남구', lat: 37.517, lng: 127.047, population: 539_000, populationChange5yr: 1.2, agingRate: 15.8, hospitalCount: 210, avgAccessDistanceKm: 0.9, avgDriveMinutes: 4, seniorCoverage30min: 99.1, twoSfcaScore: 0.00184, vulnerability: v(6.0, 2.0, 3.0, 3.0) },
  { code: '11110', province: '서울특별시', name: '종로구', lat: 37.573, lng: 126.979, population: 147_000, populationChange5yr: -3.1, agingRate: 19.4, hospitalCount: 96, avgAccessDistanceKm: 1.1, avgDriveMinutes: 5, seniorCoverage30min: 98.5, twoSfcaScore: 0.00152, vulnerability: v(8.0, 5.0, 4.0, 4.0) },
  { code: '41135', province: '경기도', name: '성남시 분당구', lat: 37.382, lng: 127.119, population: 480_000, populationChange5yr: 0.6, agingRate: 16.9, hospitalCount: 120, avgAccessDistanceKm: 1.3, avgDriveMinutes: 6, seniorCoverage30min: 97.8, twoSfcaScore: 0.00132, vulnerability: v(6.5, 3.0, 4.0, 5.5) },
  { code: '41117', province: '경기도', name: '수원시 영통구', lat: 37.259, lng: 127.046, population: 360_000, populationChange5yr: 2.1, agingRate: 13.2, hospitalCount: 78, avgAccessDistanceKm: 1.5, avgDriveMinutes: 6, seniorCoverage30min: 97.2, twoSfcaScore: 0.00121, vulnerability: v(5.0, 2.0, 6.0, 6.0) },
  { code: '28237', province: '인천광역시', name: '부평구', lat: 37.507, lng: 126.722, population: 498_000, populationChange5yr: -1.4, agingRate: 18.6, hospitalCount: 88, avgAccessDistanceKm: 1.4, avgDriveMinutes: 6, seniorCoverage30min: 96.5, twoSfcaScore: 0.0011, vulnerability: v(8.0, 6.0, 5.5, 6.5) },
  { code: '26350', province: '부산광역시', name: '해운대구', lat: 35.163, lng: 129.164, population: 388_000, populationChange5yr: -0.9, agingRate: 21.5, hospitalCount: 74, avgAccessDistanceKm: 1.6, avgDriveMinutes: 7, seniorCoverage30min: 95.2, twoSfcaScore: 0.00123, vulnerability: v(9.5, 5.0, 7.0, 7.0) },
  { code: '27110', province: '대구광역시', name: '중구', lat: 35.869, lng: 128.606, population: 78_000, populationChange5yr: -5.2, agingRate: 24.8, hospitalCount: 40, avgAccessDistanceKm: 1.8, avgDriveMinutes: 7, seniorCoverage30min: 92.0, twoSfcaScore: 0.0011, vulnerability: v(11.0, 8.5, 9.0, 8.5) },
  { code: '30200', province: '대전광역시', name: '유성구', lat: 36.362, lng: 127.356, population: 355_000, populationChange5yr: 3.4, agingRate: 12.1, hospitalCount: 60, avgAccessDistanceKm: 1.7, avgDriveMinutes: 7, seniorCoverage30min: 96.8, twoSfcaScore: 0.00118, vulnerability: v(4.5, 1.5, 7.5, 7.5) },
  { code: '29140', province: '광주광역시', name: '서구', lat: 35.152, lng: 126.89, population: 300_000, populationChange5yr: -0.7, agingRate: 17.3, hospitalCount: 66, avgAccessDistanceKm: 1.6, avgDriveMinutes: 6, seniorCoverage30min: 96.1, twoSfcaScore: 0.0012, vulnerability: v(7.0, 4.5, 6.5, 6.5) },
  { code: '31140', province: '울산광역시', name: '남구', lat: 35.544, lng: 129.33, population: 320_000, populationChange5yr: -1.1, agingRate: 16.4, hospitalCount: 58, avgAccessDistanceKm: 1.9, avgDriveMinutes: 8, seniorCoverage30min: 95.6, twoSfcaScore: 0.00114, vulnerability: v(6.5, 5.0, 7.5, 8.0) },
  { code: '36110', province: '세종특별자치시', name: '세종시', lat: 36.48, lng: 127.289, population: 386_000, populationChange5yr: 6.8, agingRate: 10.5, hospitalCount: 44, avgAccessDistanceKm: 2.4, avgDriveMinutes: 10, seniorCoverage30min: 94.1, twoSfcaScore: 0.00101, vulnerability: v(3.5, 1.0, 9.5, 11.0) },
  { code: '50130', province: '제주특별자치도', name: '서귀포시', lat: 33.254, lng: 126.56, population: 185_000, populationChange5yr: 1.2, agingRate: 20.1, hospitalCount: 38, avgAccessDistanceKm: 4.2, avgDriveMinutes: 16, seniorCoverage30min: 84.9, twoSfcaScore: 0.00047, vulnerability: v(9.0, 3.0, 10.5, 16.0) },
  { code: '46110', province: '전라남도', name: '목포시', lat: 34.812, lng: 126.392, population: 217_000, populationChange5yr: -4.3, agingRate: 22.6, hospitalCount: 42, avgAccessDistanceKm: 3.1, avgDriveMinutes: 13, seniorCoverage30min: 82.3, twoSfcaScore: 0.00061, vulnerability: v(10.0, 7.5, 9.5, 14.0) },
  { code: '51150', province: '강원특별자치도', name: '강릉시', lat: 37.752, lng: 128.876, population: 210_000, populationChange5yr: -2.6, agingRate: 23.4, hospitalCount: 40, avgAccessDistanceKm: 5.1, avgDriveMinutes: 19, seniorCoverage30min: 78.4, twoSfcaScore: 0.0005, vulnerability: v(10.5, 6.5, 10.0, 18.0) },
  { code: '43150', province: '충청북도', name: '제천시', lat: 37.132, lng: 128.191, population: 132_000, populationChange5yr: -3.8, agingRate: 26.1, hospitalCount: 28, avgAccessDistanceKm: 5.6, avgDriveMinutes: 21, seniorCoverage30min: 72.1, twoSfcaScore: 0.00042, vulnerability: v(12.0, 7.0, 11.5, 19.5) },
  { code: '47170', province: '경상북도', name: '안동시', lat: 36.568, lng: 128.729, population: 155_000, populationChange5yr: -3.2, agingRate: 25.7, hospitalCount: 34, avgAccessDistanceKm: 6.4, avgDriveMinutes: 23, seniorCoverage30min: 70.3, twoSfcaScore: 0.0004, vulnerability: v(11.5, 7.0, 12.0, 21.5) },
  { code: '46910', province: '전라남도', name: '신안군', lat: 34.833, lng: 126.351, population: 38_000, populationChange5yr: -6.1, agingRate: 34.2, hospitalCount: 8, avgAccessDistanceKm: 9.8, avgDriveMinutes: 38, seniorCoverage30min: 42.0, twoSfcaScore: 0.00016, vulnerability: v(18.0, 12.0, 15.0, 24.0) },
  { code: '51770', province: '강원특별자치도', name: '정선군', lat: 37.38, lng: 128.661, population: 35_000, populationChange5yr: -5.9, agingRate: 33.1, hospitalCount: 9, avgAccessDistanceKm: 8.7, avgDriveMinutes: 34, seniorCoverage30min: 46.8, twoSfcaScore: 0.00018, vulnerability: v(17.5, 11.5, 14.0, 22.5) },
  { code: '52770', province: '전북특별자치도', name: '장수군', lat: 35.647, lng: 127.521, population: 21_000, populationChange5yr: -6.7, agingRate: 35.6, hospitalCount: 5, avgAccessDistanceKm: 10.4, avgDriveMinutes: 37, seniorCoverage30min: 38.2, twoSfcaScore: 0.00013, vulnerability: v(19.0, 12.5, 15.5, 24.5) },
  { code: '48890', province: '경상남도', name: '합천군', lat: 35.567, lng: 128.166, population: 42_000, populationChange5yr: -6.3, agingRate: 39.4, hospitalCount: 7, avgAccessDistanceKm: 9.1, avgDriveMinutes: 35, seniorCoverage30min: 40.5, twoSfcaScore: 0.00014, vulnerability: v(21.5, 13.0, 15.0, 23.0) },
  { code: '46770', province: '전라남도', name: '고흥군', lat: 34.611, lng: 127.285, population: 62_000, populationChange5yr: -5.7, agingRate: 40.1, hospitalCount: 11, avgAccessDistanceKm: 8.3, avgDriveMinutes: 32, seniorCoverage30min: 44.1, twoSfcaScore: 0.00017, vulnerability: v(22.0, 12.0, 13.5, 22.0) },
  { code: '47730', province: '경상북도', name: '영양군', lat: 36.667, lng: 129.112, population: 16_000, populationChange5yr: -7.4, agingRate: 37.8, hospitalCount: 4, avgAccessDistanceKm: 12.1, avgDriveMinutes: 41, seniorCoverage30min: 30.5, twoSfcaScore: 0.0001, vulnerability: v(20.5, 13.5, 16.5, 25.5) },
  { code: '47730b', province: '경상북도', name: '의성군', lat: 36.352, lng: 128.697, population: 50_000, populationChange5yr: -6.9, agingRate: 43.2, hospitalCount: 8, avgAccessDistanceKm: 10.9, avgDriveMinutes: 39, seniorCoverage30min: 33.0, twoSfcaScore: 0.00011, vulnerability: v(23.5, 13.5, 14.5, 25.0) },
  { code: '47720', province: '경상북도', name: '군위군', lat: 36.243, lng: 128.573, population: 22_000, populationChange5yr: -7.1, agingRate: 42.5, hospitalCount: 4, avgAccessDistanceKm: 11.6, avgDriveMinutes: 40, seniorCoverage30min: 31.2, twoSfcaScore: 0.0001, vulnerability: v(23.0, 13.5, 16.0, 25.5) },
]

// ── selector 함수 (FastAPI 연결 시 교체 지점) ──────────────────────────────

export function listRegions(): Region[] {
  return REGIONS
}

export function getRegionByCode(code: string): Region | undefined {
  return REGIONS.find((r) => r.code === code)
}

export function listProvinces(): string[] {
  return Array.from(new Set(REGIONS.map((r) => r.province)))
}

export function regionRisk(region: Region): RiskInfo {
  return getRiskGrade(region.vulnerability.total)
}

export interface RegionFilter {
  province?: string
  query?: string
}

export function filterRegions({ province, query }: RegionFilter): Region[] {
  const q = query?.trim()
  return REGIONS.filter((r) => {
    if (province && province !== '전체' && r.province !== province) return false
    if (q && !`${r.province} ${r.name}`.includes(q)) return false
    return true
  })
}

export function topVulnerable(limit?: number): Region[] {
  const sorted = [...REGIONS].sort(
    (a, b) => b.vulnerability.total - a.vulnerability.total,
  )
  return limit ? sorted.slice(0, limit) : sorted
}

/** 등급별 지역 수(샘플 지역 기준). */
export function gradeDistribution(): Record<string, number> {
  const counts: Record<string, number> = { low: 0, mid: 0, high: 0, critical: 0 }
  for (const r of REGIONS) counts[getRiskGrade(r.vulnerability.total).level] += 1
  return counts
}

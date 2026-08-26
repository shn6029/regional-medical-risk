/**
 * 병원 폐업 영향 시뮬레이션 (데이터 서비스 계층).
 * 샘플 지역/병원 입력으로부터 전·후 지표를 결정적으로 계산한다.
 * ⚠️ 결과는 프로토타입용 샘플 계산이며 실제 정책 판단용이 아니다.
 */

import type { Region } from './sample-data'
import { getRiskGrade } from './risk'
import { listDemandPoints, listHospitals, type Hospital } from './hospitals'
import type { RiskInfo } from './types'

export interface ClosureMetrics {
  hospitalCount: number
  avgAccessDistanceKm: number
  avgDriveMinutes: number
  vulnerabilityTotal: number
  risk: RiskInfo
}

export interface ClosureResult {
  region: Region
  hospital: Hospital
  before: ClosureMetrics
  after: ClosureMetrics
  affectedPopulation: number
  affectedSenior: number
  distanceDeltaKm: number
  driveDeltaMinutes: number
  vulnerabilityDelta: number
  /** 취약도 상승을 구성요인 관점에서 설명하는 문장. */
  explanation: string
}

/** 폐업으로 담당 수요점의 최근접 병원이 사라지는 정도에 비례해 지표를 조정한다. */
export function simulateClosure(region: Region, hospital: Hospital): ClosureResult {
  const demandPoints = listDemandPoints(region)
  const affected = demandPoints.filter((d) => d.nearestHospitalId === hospital.id)
  const affectedPopulation = affected.reduce((s, d) => s + d.population, 0)
  const affectedSenior = affected.reduce((s, d) => s + d.seniorPopulation, 0)

  const share = hospital.demandShare // 0~1
  // 접근거리·이동시간 증가: 담당 비중이 클수록 크다(샘플 계수).
  const distanceDeltaKm = Number((share * region.avgAccessDistanceKm * 0.18).toFixed(2))
  const driveDeltaMinutes = Number((share * region.avgDriveMinutes * 0.16).toFixed(1))

  // 취약도 구성요인 재계산: 의료공급 부족 + 접근거리 항목 상승.
  const supplyBump = Math.min(
    25 - region.vulnerability.supply,
    Number((share * 2.4).toFixed(1)),
  )
  const accessBump = Math.min(
    30 - region.vulnerability.access,
    Number((share * 1.2).toFixed(1)),
  )
  const afterTotal = Number(
    (region.vulnerability.total + supplyBump + accessBump).toFixed(1),
  )
  const vulnerabilityDelta = Number((afterTotal - region.vulnerability.total).toFixed(1))

  const before: ClosureMetrics = {
    hospitalCount: region.hospitalCount,
    avgAccessDistanceKm: region.avgAccessDistanceKm,
    avgDriveMinutes: region.avgDriveMinutes,
    vulnerabilityTotal: region.vulnerability.total,
    risk: getRiskGrade(region.vulnerability.total),
  }
  const after: ClosureMetrics = {
    hospitalCount: region.hospitalCount - 1,
    avgAccessDistanceKm: Number((region.avgAccessDistanceKm + distanceDeltaKm).toFixed(2)),
    avgDriveMinutes: Number((region.avgDriveMinutes + driveDeltaMinutes).toFixed(1)),
    vulnerabilityTotal: afterTotal,
    risk: getRiskGrade(afterTotal),
  }

  const distanceText =
    distanceDeltaKm < 0.05 ? '0.05km 미만' : `${distanceDeltaKm.toFixed(2)}km`
  const explanation =
    `접근거리 변화는 ${distanceText}로 크지 않지만, 의료기관 공급 감소로 ` +
    `취약도가 ${vulnerabilityDelta.toFixed(1)}점 상승했습니다.`

  return {
    region,
    hospital,
    before,
    after,
    affectedPopulation,
    affectedSenior,
    distanceDeltaKm,
    driveDeltaMinutes,
    vulnerabilityDelta,
    explanation,
  }
}

/**
 * 실제 폐업 사례 검증 요약 — 샘플값.
 * 방향 일치율만 강조하지 않고 사례 수, 분포, 예측·관측 비교를 함께 제공한다.
 */
export const CLOSURE_VALIDATION = {
  caseCount: 37,
  directionAgreementPct: 73.0,
  observedDistanceIncreaseCases: 27,
  confusion: {
    // 예측 증가/유지 × 관측 증가/유지
    predictedIncreaseObservedIncrease: 24,
    predictedIncreaseObservedFlat: 6,
    predictedFlatObservedIncrease: 3,
    predictedFlatObservedFlat: 4,
  },
  /** 예측 거리 변화(km) vs 관측 거리 변화(km) 표본. */
  scatter: [
    { predicted: 0.4, observed: 0.6 },
    { predicted: 1.1, observed: 0.9 },
    { predicted: 0.2, observed: 0.1 },
    { predicted: 2.3, observed: 2.8 },
    { predicted: 0.8, observed: 1.4 },
    { predicted: 1.6, observed: 1.2 },
    { predicted: 0.1, observed: 0.5 },
    { predicted: 3.0, observed: 2.6 },
    { predicted: 0.5, observed: 0.3 },
    { predicted: 1.9, observed: 2.1 },
    { predicted: 0.7, observed: 1.0 },
    { predicted: 2.5, observed: 3.2 },
  ],
} as const

import type { RiskLevel, RiskInfo } from './types'

/**
 * 의료 취약도 점수(0~100)를 위험등급으로 변환한다.
 * 등급 경계는 서비스 명세를 그대로 따른다.
 *   안정 0~39.9 / 관심 40~59.9 / 주의 60~74.9 / 위험 75~100
 */
export const RISK_HEX: Record<RiskLevel, string> = {
  low: '#16a34a', // 안정 (green)
  mid: '#eab308', // 관심 (yellow)
  high: '#f97316', // 주의 (orange)
  critical: '#dc2626', // 위험 (red)
}

export const RISK_LABEL: Record<RiskLevel, string> = {
  low: '안정',
  mid: '관심',
  high: '주의',
  critical: '위험',
}

export const RISK_RANGE: Record<RiskLevel, string> = {
  low: '0–39.9',
  mid: '40–59.9',
  high: '60–74.9',
  critical: '75–100',
}

/** 범례/필터 순서용. 낮은 위험 → 높은 위험. */
export const RISK_ORDER: RiskLevel[] = ['low', 'mid', 'high', 'critical']

export function getRiskGrade(score: number): RiskInfo {
  let level: RiskLevel
  if (score >= 75) level = 'critical'
  else if (score >= 60) level = 'high'
  else if (score >= 40) level = 'mid'
  else level = 'low'
  return {
    level,
    label: RISK_LABEL[level],
    color: `var(--risk-${level})`,
    hex: RISK_HEX[level],
  }
}

/** 취약도 구성요인별 최대 배점. 합계 = 100. */
export const VULNERABILITY_WEIGHTS = {
  aging: 25, // 고령화
  decline: 20, // 인구감소
  supply: 25, // 의료공급 부족
  access: 30, // 접근거리
} as const

export const VULNERABILITY_FACTOR_LABEL: Record<
  keyof typeof VULNERABILITY_WEIGHTS,
  string
> = {
  aging: '고령화',
  decline: '인구감소',
  supply: '의료공급 부족',
  access: '접근거리',
}

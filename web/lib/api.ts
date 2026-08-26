import type { RiskInfo, RiskLevel } from './types'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * SWR 전용 fetcher. 상대 경로 key(예: `/api/v1/accessibility/latest`)를 받아
 * 같은 출처의 서버 사이드 프록시(`/api/proxy/...`)를 통해 FastAPI로 전달한다.
 * 브라우저가 FastAPI를 직접 호출하지 않으므로 CORS/Mixed Content가 없다.
 * 실제 업스트림 주소는 프록시가 서버에서 NEXT_PUBLIC_API_BASE_URL로 읽는다.
 */
export async function fetcher<T>(path: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/proxy${path}`, {
      headers: { Accept: 'application/json' },
    })
  } catch {
    throw new ApiError('API 서버에 연결할 수 없습니다.', 0)
  }

  if (!response.ok) {
    let detail = `요청이 실패했습니다. (HTTP ${response.status})`
    try {
      const body = await response.json()
      if (body?.detail) detail = String(body.detail)
    } catch {
      /* JSON 파싱 실패는 무시 */
    }
    throw new ApiError(detail, response.status)
  }

  return response.json() as Promise<T>
}

/**
 * 접근성 커버리지(고령자 임계시간 내 비율)를 기반으로 지역 위험도를 도출한다.
 * 백엔드에 별도 위험 점수 API가 없으므로 2SFCA 커버리지에서 파생한 지표다.
 */
const RISK_HEX: Record<RiskLevel, string> = {
  low: '#16a34a',
  mid: '#eab308',
  high: '#f97316',
  critical: '#dc2626',
}

export function getRiskFromCoverage(seniorCoveragePct: number): RiskInfo {
  let level: RiskLevel
  let label: string
  if (seniorCoveragePct >= 80) {
    level = 'low'
    label = '안정'
  } else if (seniorCoveragePct >= 60) {
    level = 'mid'
    label = '양호'
  } else if (seniorCoveragePct >= 40) {
    level = 'high'
    label = '주의'
  } else {
    level = 'critical'
    label = '위험'
  }
  return { level, label, color: `var(--risk-${level})`, hex: RISK_HEX[level] }
}

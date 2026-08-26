/**
 * 병원 및 행정동 수요점 샘플 생성기 (데이터 서비스 계층).
 * 지역별로 결정적으로 생성되어 페이지 간 동일한 결과를 보장한다.
 * ⚠️ 병원명·병상수·주소·개설일은 프로토타입용 샘플이다.
 */

import type { Region } from './sample-data'

export type HospitalType = '종합병원' | '병원' | '요양병원' | '의원'

export interface Hospital {
  id: string
  name: string
  type: HospitalType
  beds: number
  address: string
  openedAt: string
  lat: number
  lng: number
  /** 이 병원이 담당(최근접)하는 수요점 비중(0~1). 폐업 영향 계산용. */
  demandShare: number
}

export interface DemandPoint {
  id: string
  name: string
  population: number
  seniorPopulation: number
  lat: number
  lng: number
  /** 최근접 병원 id. */
  nearestHospitalId: string
  withinThreshold: boolean
}

const TYPE_CYCLE: HospitalType[] = ['종합병원', '병원', '요양병원', '의원']
const BEDS_BY_TYPE: Record<HospitalType, number> = {
  종합병원: 420,
  병원: 160,
  요양병원: 210,
  의원: 30,
}

// 결정적 유사난수 (시드 기반).
function seeded(seed: number): () => number {
  let s = seed % 2147483647
  if (s <= 0) s += 2147483646
  return () => {
    s = (s * 16807) % 2147483647
    return (s - 1) / 2147483646
  }
}

function codeSeed(code: string): number {
  let h = 0
  for (let i = 0; i < code.length; i += 1) h = (h * 31 + code.charCodeAt(i)) % 2147483647
  return h + 1
}

export function listHospitals(region: Region): Hospital[] {
  const count = Math.min(region.hospitalCount, 6)
  const rand = seeded(codeSeed(region.code))
  const shares = Array.from({ length: count }, () => 0.4 + rand() * 0.6)
  const shareSum = shares.reduce((a, b) => a + b, 0)
  return Array.from({ length: count }, (_, i) => {
    const type = TYPE_CYCLE[i % TYPE_CYCLE.length]
    const beds = Math.round(BEDS_BY_TYPE[type] * (0.7 + rand() * 0.6))
    const openYear = 1985 + Math.floor(rand() * 35)
    const openMonth = 1 + Math.floor(rand() * 12)
    return {
      id: `${region.code}-H${i + 1}`,
      name: `${region.name} ${['중앙', '제일', '한마음', '연세', '성모', '새로운'][i % 6]}${
        type === '의원' ? '의원' : type === '요양병원' ? '요양병원' : '병원'
      }`,
      type,
      beds,
      address: `${region.province} ${region.name} 샘플로 ${10 + i * 7}`,
      openedAt: `${openYear}-${String(openMonth).padStart(2, '0')}-01`,
      lat: region.lat + (rand() - 0.5) * 0.06,
      lng: region.lng + (rand() - 0.5) * 0.06,
      demandShare: shares[i] / shareSum,
    }
  })
}

export function listDemandPoints(region: Region): DemandPoint[] {
  const hospitals = listHospitals(region)
  const count = Math.max(6, Math.min(14, Math.round(region.population / 12000)))
  const rand = seeded(codeSeed(region.code) + 7)
  const withinRate = region.seniorCoverage30min / 100
  return Array.from({ length: count }, (_, i) => {
    const hospital = hospitals.length
      ? hospitals[Math.floor(rand() * hospitals.length)]
      : undefined
    const population = Math.round((region.population / count) * (0.6 + rand() * 0.8))
    return {
      id: `${region.code}-D${i + 1}`,
      name: `${region.name} ${i + 1}행정동`,
      population,
      seniorPopulation: Math.round(population * (region.agingRate / 100)),
      lat: region.lat + (rand() - 0.5) * 0.1,
      lng: region.lng + (rand() - 0.5) * 0.1,
      nearestHospitalId: hospital?.id ?? '',
      withinThreshold: rand() < withinRate,
    }
  })
}

'use client'

import { useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { latLngBounds } from 'leaflet'
import { getRiskFromCoverage } from '@/lib/api'
import { formatNumber, formatPercent } from '@/lib/utils'
import type { RegionScore } from '@/lib/types'

// 대한민국 본토+제주를 감싸는 범위. 지도가 이 밖(중국·일본)으로
// 넘어가지 않도록 maxBounds/최소 줌으로 제한한다.
const KOREA_BOUNDS = latLngBounds([33.0, 125.0], [38.7, 130.0])

// 커버리지가 낮을수록(위험) 마커를 크게 강조한다.
function markerRadius(coveragePct: number): number {
  const clamped = Math.max(0, Math.min(100, coveragePct))
  return 5 + ((100 - clamped) / 100) * 9
}

/**
 * 지도를 항상 대한민국 범위에 맞춰 프레이밍하고, 그 밖으로 나가지 못하게
 * 잠근다. 화면 크기에 따라 최소 줌을 계산해 축소해도 이웃 국가가 크게
 * 보이지 않도록 하고, 리사이즈 시 다시 맞춘다.
 */
function ConstrainToKorea() {
  const map = useMap()

  useEffect(() => {
    const apply = () => {
      map.setMaxBounds(KOREA_BOUNDS)
      // 한국 전체(전국 마커)가 한눈에 들어오도록 맞추고, 그 줌을 최소 줌으로
      // 잠근다 → 더 축소하거나 범위 밖으로 이동할 수 없다.
      const fitZoom = map.getBoundsZoom(KOREA_BOUNDS, false)
      map.setMinZoom(fitZoom)
      map.fitBounds(KOREA_BOUNDS, { animate: false })
    }
    apply()
    map.on('resize', apply)
    return () => {
      map.off('resize', apply)
    }
  }, [map])

  return null
}

export default function RiskMap({
  regions,
  selectedCode,
  onSelect,
}: {
  regions: RegionScore[]
  selectedCode: string | null
  onSelect: (code: string) => void
}) {
  const mappable = regions.filter(
    (r) => r.center_latitude != null && r.center_longitude != null,
  )

  return (
    <MapContainer
      center={[36.5, 127.8]}
      zoom={7}
      maxBounds={KOREA_BOUNDS}
      maxBoundsViscosity={1.0}
      scrollWheelZoom
      className="h-[560px] w-full rounded-xl md:h-[640px]"
      style={{ zIndex: 0 }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
      />
      <ConstrainToKorea />
      {mappable.map((region) => {
        const risk = getRiskFromCoverage(region.senior_within_threshold_pct)
        const isSelected = region.region_code === selectedCode
        return (
          <CircleMarker
            key={region.region_code}
            center={[region.center_latitude as number, region.center_longitude as number]}
            radius={markerRadius(region.senior_within_threshold_pct)}
            pathOptions={{
              color: isSelected ? '#1e293b' : risk.hex,
              weight: isSelected ? 2.5 : 1,
              fillColor: risk.hex,
              fillOpacity: 0.65,
            }}
            eventHandlers={{ click: () => onSelect(region.region_code) }}
          >
            <Tooltip direction="top" offset={[0, -4]}>
              <div className="text-xs">
                <p className="font-semibold">
                  {region.province_name} {region.region_name}
                </p>
                <p>고령자 커버리지 {formatPercent(region.senior_within_threshold_pct)}</p>
                <p>인구 {formatNumber(region.population)}명</p>
                <p>2SFCA {region.two_sfca_score.toFixed(4)}</p>
              </div>
            </Tooltip>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}

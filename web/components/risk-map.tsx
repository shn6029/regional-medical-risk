'use client'

import { useMemo } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { getRiskFromCoverage } from '@/lib/api'
import { formatNumber, formatPercent } from '@/lib/utils'
import type { RegionScore } from '@/lib/types'

// 커버리지가 낮을수록(위험) 마커를 크게 강조한다.
function markerRadius(coveragePct: number): number {
  const clamped = Math.max(0, Math.min(100, coveragePct))
  return 5 + ((100 - clamped) / 100) * 9
}

function FitBounds({ regions }: { regions: RegionScore[] }) {
  const map = useMap()
  const points = regions
    .filter((r) => r.center_latitude != null && r.center_longitude != null)
    .map((r) => [r.center_latitude as number, r.center_longitude as number] as [number, number])

  useMemo(() => {
    if (points.length === 0) return
    if (points.length === 1) {
      map.setView(points[0], 10)
    } else {
      map.fitBounds(points, { padding: [30, 30] })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [regions])

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
      scrollWheelZoom
      className="h-[520px] w-full rounded-xl"
      style={{ zIndex: 0 }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
      />
      <FitBounds regions={mappable} />
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

'use client'

import { useEffect } from 'react'
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Tooltip,
  useMap,
} from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { latLngBounds } from 'leaflet'
import { formatNumber } from '@/lib/utils'
import type { Region } from '@/lib/sample-data'
import type { Hospital, DemandPoint } from '@/lib/hospitals'

const HOSPITAL_COLOR = '#2563eb'
const DEMAND_IN = '#16a34a'
const DEMAND_OUT = '#dc2626'

function FitToPoints({
  points,
}: {
  points: [number, number][]
}) {
  const map = useMap()
  useEffect(() => {
    if (points.length === 0) return
    if (points.length === 1) {
      map.setView(points[0], 12, { animate: false })
    } else {
      map.fitBounds(latLngBounds(points).pad(0.2), { animate: false })
    }
  }, [map, points])
  return null
}

export function RegionDetailMap({
  region,
  hospitals,
  demandPoints,
}: {
  region: Region
  hospitals: Hospital[]
  demandPoints: DemandPoint[]
}) {
  const points: [number, number][] = [
    [region.lat, region.lng],
    ...hospitals.map((h) => [h.lat, h.lng] as [number, number]),
    ...demandPoints.map((d) => [d.lat, d.lng] as [number, number]),
  ]

  return (
    <MapContainer
      center={[region.lat, region.lng]}
      zoom={11}
      scrollWheelZoom
      className="h-[420px] w-full rounded-xl md:h-[480px]"
      style={{ zIndex: 0 }}
    >
      <FitToPoints points={points} />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
      />

      {demandPoints.map((d) => (
        <CircleMarker
          key={d.id}
          center={[d.lat, d.lng]}
          radius={5}
          pathOptions={{
            color: d.withinThreshold ? DEMAND_IN : DEMAND_OUT,
            weight: 1,
            fillColor: d.withinThreshold ? DEMAND_IN : DEMAND_OUT,
            fillOpacity: 0.55,
          }}
        >
          <Tooltip direction="top">
            <div className="space-y-0.5">
              <p className="font-semibold">{d.name}</p>
              <p>인구 {formatNumber(d.population)}명</p>
              <p>{d.withinThreshold ? '30분 생활권 내' : '30분 생활권 밖'}</p>
            </div>
          </Tooltip>
        </CircleMarker>
      ))}

      {hospitals.map((h) => (
        <CircleMarker
          key={h.id}
          center={[h.lat, h.lng]}
          radius={9}
          pathOptions={{
            color: '#fff',
            weight: 2,
            fillColor: HOSPITAL_COLOR,
            fillOpacity: 1,
          }}
        >
          <Tooltip direction="top">
            <div className="space-y-0.5">
              <p className="font-semibold">{h.name}</p>
              <p>{h.type} · {formatNumber(h.beds)}병상</p>
            </div>
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}

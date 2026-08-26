'use client'

import { useMemo } from 'react'
import dynamic from 'next/dynamic'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { PageHeader } from '@/components/page-header'
import { FilterBar } from '@/components/filter-bar'
import { MapLegend } from '@/components/map-legend'
import { SampleNotice } from '@/components/sample-notice'
import { RegionRankTable } from '@/components/region-rank-table'
import { useSelection } from '@/components/selection-context'
import { filterRegions } from '@/lib/sample-data'

// Leaflet은 window에 의존하므로 클라이언트에서만 로드한다.
const VulnerabilityMap = dynamic(
  () => import('@/components/vulnerability-map').then((m) => m.VulnerabilityMap),
  {
    ssr: false,
    loading: () => <Skeleton className="h-[560px] w-full rounded-xl md:h-[640px]" />,
  },
)

export default function MapPage() {
  const { province, query, selectedRegionCode, setSelectedRegionCode } =
    useSelection()

  const regions = useMemo(
    () => filterRegions({ province, query }),
    [province, query],
  )

  const handleSelect = (code: string) => {
    setSelectedRegionCode(code)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="전국 취약도 지도"
        description="지역별 의료 취약도를 지도에서 확인합니다. 마커를 선택하면 지역이 강조되고, 표에서 상세 페이지로 이동할 수 있습니다."
      />

      <Card>
        <CardContent className="space-y-4 py-4">
          <FilterBar />
          <MapLegend />
          {regions.length > 0 ? (
            <VulnerabilityMap
              regions={regions}
              selectedCode={selectedRegionCode}
              onSelect={handleSelect}
            />
          ) : (
            <div className="flex h-[560px] w-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border text-center md:h-[640px]">
              <p className="text-sm font-medium text-foreground">
                표시할 지역이 없습니다
              </p>
              <p className="text-sm text-muted-foreground">
                검색어나 시·도 필터를 조정해 보세요.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {regions.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>지도에 표시된 지역</CardTitle>
          </CardHeader>
          <CardContent>
            <RegionRankTable
              regions={[...regions].sort(
                (a, b) => b.vulnerability.total - a.vulnerability.total,
              )}
            />
          </CardContent>
        </Card>
      ) : null}

      <SampleNotice />
    </div>
  )
}

'use client'

import { useMemo, useState } from 'react'
import dynamic from 'next/dynamic'
import useSWR from 'swr'
import { Map as MapIcon, Table2, BarChart3 } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { SummaryCards, SummaryCardsSkeleton } from '@/components/summary-cards'
import { Filters, type FilterState } from '@/components/filters'
import { RegionTable } from '@/components/region-table'
import { AccessibilityCharts } from '@/components/accessibility-charts'
import { RegionDetail } from '@/components/region-detail'
import { ErrorState, EmptyState } from '@/components/states'
import { fetcher, getRiskFromCoverage } from '@/lib/api'
import { formatDateTime } from '@/lib/utils'
import type { AccessibilitySummary, RegionsResponse } from '@/lib/types'

const RiskMap = dynamic(() => import('@/components/risk-map'), {
  ssr: false,
  loading: () => <Skeleton className="h-[520px] w-full rounded-xl" />,
})

const RISK_LEGEND = [
  { hex: '#16a34a', label: '안정 (80%+)' },
  { hex: '#eab308', label: '양호 (60–80%)' },
  { hex: '#f97316', label: '주의 (40–60%)' },
  { hex: '#dc2626', label: '위험 (<40%)' },
]

export function Dashboard() {
  const summaryQuery = useSWR<AccessibilitySummary>(
    '/api/v1/accessibility/latest',
    fetcher,
  )
  const regionsQuery = useSWR<RegionsResponse>(
    '/api/v1/accessibility/regions',
    fetcher,
  )

  const [filters, setFilters] = useState<FilterState>({
    province: 'all',
    risk: 'all',
    query: '',
  })
  const [selectedCode, setSelectedCode] = useState<string | null>(null)

  const allRegions = regionsQuery.data?.items ?? []

  const provinces = useMemo(
    () => Array.from(new Set(allRegions.map((r) => r.province_name))).sort((a, b) => a.localeCompare(b, 'ko')),
    [allRegions],
  )

  const filteredRegions = useMemo(() => {
    return allRegions.filter((r) => {
      if (filters.province !== 'all' && r.province_name !== filters.province) return false
      if (filters.risk !== 'all') {
        if (getRiskFromCoverage(r.senior_within_threshold_pct).level !== filters.risk) {
          return false
        }
      }
      if (filters.query.trim()) {
        const q = filters.query.trim().toLowerCase()
        const haystack = `${r.province_name} ${r.region_name}`.toLowerCase()
        if (!haystack.includes(q)) return false
      }
      return true
    })
  }, [allRegions, filters])

  function handleSelect(code: string) {
    setSelectedCode((prev) => (prev === code ? null : code))
  }

  // 로딩
  if (summaryQuery.isLoading || regionsQuery.isLoading) {
    return (
      <div className="space-y-4">
        <SummaryCardsSkeleton />
        <Skeleton className="h-16 w-full rounded-xl" />
        <Skeleton className="h-[520px] w-full rounded-xl" />
      </div>
    )
  }

  // 오류: regions가 핵심. summary 오류는 상단에서만 처리
  if (regionsQuery.error) {
    return <ErrorState error={regionsQuery.error} onRetry={() => regionsQuery.mutate()} />
  }

  if (allRegions.length === 0) {
    return (
      <EmptyState
        title="분석 결과가 아직 없습니다"
        description="완료된 2SFCA 실행이 등록되면 여기에 지역별 접근성 결과가 표시됩니다."
      />
    )
  }

  return (
    <div className="space-y-5">
      {summaryQuery.data ? (
        <SummaryCards summary={summaryQuery.data} regions={allRegions} />
      ) : (
        <SummaryCardsSkeleton />
      )}

      {summaryQuery.data && (
        <p className="text-xs text-muted-foreground">
          최근 실행 {summaryQuery.data.method} {summaryQuery.data.method_version} · 완료{' '}
          {formatDateTime(summaryQuery.data.completed_at)} · 임계 시간{' '}
          {summaryQuery.data.catchment_minutes}분
        </p>
      )}

      <Filters provinces={provinces} value={filters} onChange={setFilters} />

      <Tabs defaultValue="map">
        <TabsList>
          <TabsTrigger value="map" className="gap-1.5">
            <MapIcon className="h-4 w-4" /> 지도
          </TabsTrigger>
          <TabsTrigger value="table" className="gap-1.5">
            <Table2 className="h-4 w-4" /> 지역 순위
          </TabsTrigger>
          <TabsTrigger value="charts" className="gap-1.5">
            <BarChart3 className="h-4 w-4" /> 접근성 분석
          </TabsTrigger>
        </TabsList>

        <TabsContent value="map">
          <Card>
            <CardContent className="p-3">
              {filteredRegions.length === 0 ? (
                <EmptyState
                  title="지도에 표시할 지역이 없습니다"
                  description="필터 조건을 조정해 주세요."
                />
              ) : (
                <>
                  <RiskMap
                    regions={filteredRegions}
                    selectedCode={selectedCode}
                    onSelect={handleSelect}
                  />
                  <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 px-1">
                    {RISK_LEGEND.map((item) => (
                      <div key={item.label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <span
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: item.hex }}
                        />
                        {item.label}
                      </div>
                    ))}
                    <span className="text-xs text-muted-foreground">
                      · 마커가 클수록 접근성이 낮음
                    </span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="table">
          <RegionTable
            regions={filteredRegions}
            selectedCode={selectedCode}
            onSelect={handleSelect}
          />
        </TabsContent>

        <TabsContent value="charts">
          {filteredRegions.length === 0 ? (
            <EmptyState title="차트를 표시할 지역이 없습니다" />
          ) : (
            <AccessibilityCharts regions={filteredRegions} />
          )}
        </TabsContent>
      </Tabs>

      {selectedCode && (
        <RegionDetail regionCode={selectedCode} onClose={() => setSelectedCode(null)} />
      )}
    </div>
  )
}

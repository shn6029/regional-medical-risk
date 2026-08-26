'use client'

import useSWR from 'swr'
import { useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/page-header'
import { ErrorState, EmptyState } from '@/components/states'
import { fetcher, getRiskFromCoverage } from '@/lib/api'
import { formatNumber, formatPercent } from '@/lib/utils'
import type { AccessibilitySummary, RegionsResponse, RegionScore } from '@/lib/types'

function KpiSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-24" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-32" />
        <Skeleton className="mt-2 h-3 w-20" />
      </CardContent>
    </Card>
  )
}

function LiveKpi(props: { label: string; value: string; sub: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{props.label}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold tabular-nums text-foreground">{props.value}</p>
        <p className="mt-1 text-xs text-muted-foreground">{props.sub}</p>
      </CardContent>
    </Card>
  )
}

export default function AccessibilityPage() {
  const {
    data: summary,
    error: summaryError,
    isLoading: summaryLoading,
    mutate: mutateSummary,
  } = useSWR<AccessibilitySummary>('/api/v1/accessibility/latest', fetcher)

  const {
    data: regionsData,
    error: regionsError,
    isLoading: regionsLoading,
    mutate: mutateRegions,
  } = useSWR<RegionsResponse>('/api/v1/accessibility/regions', fetcher)

  const [order, setOrder] = useState<'worst' | 'best'>('worst')

  const sorted = useMemo(() => {
    const items = regionsData?.items ?? []
    const copy = [...items]
    copy.sort((a, b) =>
      order === 'worst'
        ? a.senior_within_threshold_pct - b.senior_within_threshold_pct
        : b.senior_within_threshold_pct - a.senior_within_threshold_pct,
    )
    return copy.slice(0, 15)
  }, [regionsData, order])

  const error = summaryError || regionsError
  const loading = summaryLoading || regionsLoading

  const retry = () => {
    void mutateSummary()
    void mutateRegions()
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="2SFCA 접근성 분석"
        description="기존 FastAPI 서버의 2SFCA(2단계 유동 의료권) 실행 결과를 실시간으로 조회합니다."
        badge={
          <Badge className="gap-1.5 border-primary/30 bg-primary/10 text-primary">
            <span className="size-1.5 rounded-full bg-primary" aria-hidden />
            실시간 API
          </Badge>
        }
      />

      {error ? (
        <ErrorState error={error} onRetry={retry} />
      ) : loading ? (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiSkeleton />
            <KpiSkeleton />
            <KpiSkeleton />
            <KpiSkeleton />
          </div>
          <Card>
            <CardHeader>
              <Skeleton className="h-5 w-40" />
            </CardHeader>
            <CardContent className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </CardContent>
          </Card>
        </>
      ) : !summary || (regionsData?.items.length ?? 0) === 0 ? (
        <EmptyState
          title="표시할 2SFCA 결과가 없습니다"
          description="아직 실행된 분석 결과가 없습니다. 백엔드에서 분석을 실행하면 이곳에 표시됩니다."
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <LiveKpi
              label="고령자 접근성 커버리지"
              value={formatPercent(summary.senior_coverage_pct, 1)}
              sub={`${formatNumber(summary.covered_senior_population)}명 임계시간 내`}
            />
            <LiveKpi
              label="분석 수요점"
              value={formatNumber(summary.demand_point_count)}
              sub={`커버 ${formatNumber(summary.covered_demand_count)}개`}
            />
            <LiveKpi
              label="분석 경로 수"
              value={formatNumber(summary.route_count)}
              sub={`임계 ${summary.catchment_minutes}분`}
            />
            <LiveKpi
              label="분석 방법"
              value={summary.method}
              sub={`버전 ${summary.method_version}`}
            />
          </div>

          <p className="text-xs text-muted-foreground">
            실행 ID <span className="font-mono">{summary.run_id}</span>
            {summary.completed_at
              ? ` · 완료 ${new Date(summary.completed_at).toLocaleString('ko-KR')}`
              : ''}
          </p>

          <Card>
            <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
              <CardTitle className="text-base">
                {order === 'worst' ? '고령자 접근성 하위 지역' : '고령자 접근성 상위 지역'}
              </CardTitle>
              <div className="flex gap-1">
                <Button
                  variant={order === 'worst' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setOrder('worst')}
                >
                  하위
                </Button>
                <Button
                  variant={order === 'best' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setOrder('best')}
                >
                  상위
                </Button>
              </div>
            </CardHeader>
            <CardContent className="px-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="pl-6">지역</TableHead>
                      <TableHead className="text-right">고령 인구</TableHead>
                      <TableHead className="text-right">고령자 커버리지</TableHead>
                      <TableHead className="hidden text-right sm:table-cell">전체 커버리지</TableHead>
                      <TableHead className="pr-6 text-right">등급</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sorted.map((r: RegionScore) => {
                      const risk = getRiskFromCoverage(r.senior_within_threshold_pct)
                      return (
                        <TableRow key={r.region_code}>
                          <TableCell className="pl-6">
                            <span className="font-medium text-foreground">{r.region_name}</span>
                            <span className="ml-1.5 text-xs text-muted-foreground">
                              {r.province_name}
                            </span>
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatNumber(r.senior_population)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatPercent(r.senior_within_threshold_pct, 1)}
                          </TableCell>
                          <TableCell className="hidden text-right tabular-nums sm:table-cell">
                            {formatPercent(r.population_within_threshold_pct, 1)}
                          </TableCell>
                          <TableCell className="pr-6 text-right">
                            <span
                              className="inline-flex items-center gap-1.5 text-sm font-medium"
                              style={{ color: risk.color }}
                            >
                              <span
                                className="size-2 rounded-full"
                                style={{ backgroundColor: risk.hex }}
                                aria-hidden
                              />
                              {risk.label}
                            </span>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

'use client'

import useSWR from 'swr'
import { X, Building2, Hospital, Users, MapPin } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { RiskBadge } from '@/components/risk-badge'
import { ErrorState, EmptyState } from '@/components/states'
import { fetcher } from '@/lib/api'
import { cn, formatNumber, formatPercent } from '@/lib/utils'
import type { RegionDetail as RegionDetailType } from '@/lib/types'

function Stat({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType
  label: string
  value: string
}) {
  return (
    <div className="rounded-lg border bg-background p-3">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <p className="mt-1 font-mono text-lg font-semibold">{value}</p>
    </div>
  )
}

export function RegionDetail({
  regionCode,
  onClose,
}: {
  regionCode: string
  onClose: () => void
}) {
  const { data, error, isLoading, mutate } = useSWR<RegionDetailType>(
    `/api/v1/accessibility/regions/${regionCode}`,
    fetcher,
  )

  return (
    <Card className="border-primary/30">
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <CardTitle>
            {isLoading
              ? '지역 상세'
              : data
                ? `${data.province_name} ${data.region_name}`
                : '지역 상세'}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            수요점(행정동)별 의료기관 접근성 · 2SFCA 결과
          </p>
        </div>
        <Button variant="ghost" size="icon" aria-label="상세 닫기" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading && (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
            <Skeleton className="h-48 w-full" />
          </>
        )}

        {error && <ErrorState error={error} onRetry={() => mutate()} />}

        {data && !isLoading && !error && (
          <>
            <div className="flex items-center gap-2">
              <RiskBadge coveragePct={data.senior_within_threshold_pct} />
              <span className="text-xs text-muted-foreground">
                고령자 접근성 커버리지 기준
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat
                icon={Users}
                label="인구"
                value={`${formatNumber(data.population)}명`}
              />
              <Stat
                icon={Users}
                label="고령자 커버리지"
                value={formatPercent(data.senior_within_threshold_pct)}
              />
              <Stat
                icon={MapPin}
                label="전체 커버리지"
                value={formatPercent(data.population_within_threshold_pct)}
              />
              <Stat
                icon={Hospital}
                label="2SFCA 점수"
                value={data.two_sfca_score.toFixed(4)}
              />
            </div>

            {data.demand_points.length === 0 ? (
              <EmptyState
                title="수요점 데이터가 없습니다"
                description="이 지역에 대한 행정동 수요점 접근성 결과가 없습니다."
              />
            ) : (
              <div className="rounded-lg border">
                <div className="flex items-center gap-2 border-b bg-muted/40 px-3 py-2 text-xs font-medium text-muted-foreground">
                  <Building2 className="h-3.5 w-3.5" />
                  행정동 수요점 {formatNumber(data.demand_points.length)}곳
                </div>
                <div className="max-h-72 overflow-auto">
                  <Table>
                    <TableHeader className="sticky top-0 bg-card">
                      <TableRow>
                        <TableHead>행정동</TableHead>
                        <TableHead className="text-right">고령자</TableHead>
                        <TableHead className="text-right">접근 병원</TableHead>
                        <TableHead className="text-right">접근 병상</TableHead>
                        <TableHead className="text-right">임계 내</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.demand_points.map((point) => (
                        <TableRow key={point.demand_id}>
                          <TableCell className="font-medium">
                            {point.demand_name}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {formatNumber(point.senior_population)}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {formatNumber(point.accessible_hospital_count)}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {formatNumber(point.accessible_beds)}
                          </TableCell>
                          <TableCell className="text-right">
                            <span
                              className={cn(
                                'inline-block h-2 w-2 rounded-full',
                                point.within_threshold
                                  ? 'bg-[var(--risk-low)]'
                                  : 'bg-[var(--risk-critical)]',
                              )}
                              aria-label={point.within_threshold ? '임계시간 내' : '임계시간 초과'}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

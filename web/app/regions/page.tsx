'use client'

import { useMemo } from 'react'
import dynamic from 'next/dynamic'
import { MapPin, Users, Building2, Route, Clock } from 'lucide-react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { PageHeader } from '@/components/page-header'
import { KpiCard } from '@/components/kpi-card'
import { FilterBar } from '@/components/filter-bar'
import { RiskGradeBadge } from '@/components/risk-grade-badge'
import { VulnerabilityBars } from '@/components/vulnerability-bars'
import { SampleNotice } from '@/components/sample-notice'
import { useSelection } from '@/components/selection-context'
import { getRegionByCode, filterRegions } from '@/lib/sample-data'
import { listHospitals, listDemandPoints } from '@/lib/hospitals'
import { formatNumber, formatPercent } from '@/lib/utils'

const RegionDetailMap = dynamic(
  () => import('@/components/region-detail-map').then((m) => m.RegionDetailMap),
  {
    ssr: false,
    loading: () => <Skeleton className="h-[420px] w-full rounded-xl md:h-[480px]" />,
  },
)

export default function RegionDetailPage() {
  const { province, query, selectedRegionCode } = useSelection()

  const region = useMemo(
    () => (selectedRegionCode ? getRegionByCode(selectedRegionCode) : undefined),
    [selectedRegionCode],
  )
  const candidates = useMemo(
    () => filterRegions({ province, query }),
    [province, query],
  )
  const hospitals = useMemo(() => (region ? listHospitals(region) : []), [region])
  const demandPoints = useMemo(
    () => (region ? listDemandPoints(region) : []),
    [region],
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="지역 상세 분석"
        description="선택한 지역의 인구·의료 지표와 취약도 구성요인, 병원·수요점 분포를 확인합니다."
      />

      <Card>
        <CardContent className="py-4">
          <FilterBar />
        </CardContent>
      </Card>

      {!region ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <span className="flex size-12 items-center justify-center rounded-full bg-secondary text-primary">
              <MapPin className="size-6" />
            </span>
            <div className="space-y-1">
              <p className="text-base font-semibold text-foreground">
                지역을 선택하세요
              </p>
              <p className="text-sm text-muted-foreground text-pretty">
                위 검색창이나 시·군·구 선택에서 지역을 고르면 상세 분석이 표시됩니다.
              </p>
            </div>
            {candidates.length > 0 ? (
              <div className="flex flex-wrap justify-center gap-2 pt-2">
                {candidates.slice(0, 6).map((r) => (
                  <QuickPick key={r.code} code={r.code} name={r.name} />
                ))}
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-lg font-bold text-foreground break-keep">
              {region.province} {region.name}
            </h2>
            <RiskGradeBadge score={region.vulnerability.total} />
          </div>

          <section
            className="grid grid-cols-2 gap-3 lg:grid-cols-5"
            aria-label="지역 지표"
          >
            <KpiCard
              label="인구"
              value={formatNumber(region.population)}
              unit="명"
              sub={`5년 변화 ${region.populationChange5yr > 0 ? '+' : ''}${region.populationChange5yr}%`}
              icon={Users}
            />
            <KpiCard
              label="고령화율"
              value={formatPercent(region.agingRate)}
              sub="65세 이상"
              icon={Users}
            />
            <KpiCard
              label="의료기관"
              value={formatNumber(region.hospitalCount)}
              unit="개소"
              icon={Building2}
            />
            <KpiCard
              label="평균 접근거리"
              value={region.avgAccessDistanceKm.toFixed(1)}
              unit="km"
              sub={`차량 ${region.avgDriveMinutes}분`}
              icon={Route}
            />
            <KpiCard
              label="고령자 30분 접근률"
              value={formatPercent(region.seniorCoverage30min)}
              icon={Clock}
              accent="var(--risk-low)"
              className="col-span-2 lg:col-span-1"
            />
          </section>

          <div className="grid gap-6 lg:grid-cols-5">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>취약도 구성요인</CardTitle>
                <CardDescription>가중 기여 점수(합계 = 총 취약도)</CardDescription>
              </CardHeader>
              <CardContent>
                <VulnerabilityBars breakdown={region.vulnerability} />
              </CardContent>
            </Card>

            <Card className="lg:col-span-3">
              <CardHeader>
                <CardTitle>병원 · 수요점 분포</CardTitle>
                <CardDescription>
                  파란 점 = 병원, 초록/빨강 점 = 30분 생활권 내/외 수요점
                </CardDescription>
              </CardHeader>
              <CardContent>
                <RegionDetailMap
                  region={region}
                  hospitals={hospitals}
                  demandPoints={demandPoints}
                />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>지역 내 주요 의료기관</CardTitle>
              <CardDescription>샘플 병원 목록</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-hidden rounded-lg border border-border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>의료기관</TableHead>
                      <TableHead>종별</TableHead>
                      <TableHead className="text-right">병상</TableHead>
                      <TableHead className="hidden md:table-cell">개설</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {hospitals.map((h) => (
                      <TableRow key={h.id}>
                        <TableCell className="font-medium text-foreground break-keep">
                          {h.name}
                        </TableCell>
                        <TableCell className="text-muted-foreground">{h.type}</TableCell>
                        <TableCell className="text-right font-mono">
                          {formatNumber(h.beds)}
                        </TableCell>
                        <TableCell className="hidden font-mono text-muted-foreground md:table-cell">
                          {h.openedAt.slice(0, 7)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      <SampleNotice />
    </div>
  )
}

function QuickPick({ code, name }: { code: string; name: string }) {
  const { setSelectedRegionCode } = useSelection()
  return (
    <button
      type="button"
      onClick={() => setSelectedRegionCode(code)}
      className="rounded-full border border-border bg-card px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-secondary"
    >
      {name}
    </button>
  )
}

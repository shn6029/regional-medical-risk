'use client'

import { useMemo } from 'react'
import {
  Users,
  Building2,
  MapPinned,
  TriangleAlert,
  Lightbulb,
} from 'lucide-react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { PageHeader } from '@/components/page-header'
import { KpiCard } from '@/components/kpi-card'
import { GradeDistribution } from '@/components/grade-distribution'
import { FilterBar } from '@/components/filter-bar'
import { RegionRankTable } from '@/components/region-rank-table'
import { SampleNotice } from '@/components/sample-notice'
import { useSelection } from '@/components/selection-context'
import {
  NATIONAL,
  filterRegions,
  gradeDistribution,
} from '@/lib/sample-data'
import { formatNumber, formatPercent } from '@/lib/utils'

export default function OverviewPage() {
  const { province, query } = useSelection()

  const filtered = useMemo(
    () =>
      [...filterRegions({ province, query })].sort(
        (a, b) => b.vulnerability.total - a.vulnerability.total,
      ),
    [province, query],
  )
  const distribution = useMemo(() => gradeDistribution(), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="전국 의료 인프라 취약도 개요"
        description={`전국 ${NATIONAL.analyzedRegions}개 시·군·자치구의 인구구조와 의료 접근성을 종합한 취약도 진단입니다. (인구 ${NATIONAL.baseDate.population} · 의료기관 ${NATIONAL.baseDate.facility})`}
      />

      <section
        className="grid grid-cols-2 gap-3 lg:grid-cols-5"
        aria-label="전국 요약 지표"
      >
        <KpiCard
          label="분석 지역"
          value={formatNumber(NATIONAL.analyzedRegions)}
          unit="개"
          sub="시·군·자치구 단위"
          icon={MapPinned}
        />
        <KpiCard
          label="총 인구"
          value={formatNumber(NATIONAL.totalPopulation)}
          unit="명"
          sub={`고령화율 ${formatPercent(NATIONAL.seniorRate)}`}
          icon={Users}
        />
        <KpiCard
          label="의료기관"
          value={formatNumber(NATIONAL.hospitalCount)}
          unit="개소"
          sub="병원급 이상"
          icon={Building2}
        />
        <KpiCard
          label="주의·위험 지역"
          value={formatNumber(NATIONAL.cautionDangerRegions)}
          unit="개"
          sub={`전체의 ${formatPercent(NATIONAL.cautionDangerPct)}`}
          icon={TriangleAlert}
          accent="var(--risk-high)"
        />
        <KpiCard
          label="고령화율"
          value={formatPercent(NATIONAL.seniorRate)}
          sub="65세 이상 비율"
          icon={Users}
          className="col-span-2 lg:col-span-1"
        />
      </section>

      <Card className="border-l-4 border-l-primary">
        <CardContent className="flex items-start gap-3 py-4">
          <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-secondary text-primary">
            <Lightbulb className="size-4" />
          </span>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-foreground">핵심 인사이트</p>
            <p className="text-sm leading-relaxed text-muted-foreground text-pretty break-keep">
              {NATIONAL.insight}
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>위험등급 분포</CardTitle>
            <CardDescription>취약도 점수 기준 4단계 등급</CardDescription>
          </CardHeader>
          <CardContent>
            <GradeDistribution counts={distribution} />
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>취약도 상위 지역</CardTitle>
            <CardDescription>
              행을 선택하면 지역 상세로 이동합니다
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <FilterBar />
            {filtered.length > 0 ? (
              <RegionRankTable regions={filtered.slice(0, 10)} />
            ) : (
              <p className="rounded-lg border border-dashed border-border py-10 text-center text-sm text-muted-foreground">
                조건에 맞는 지역이 없습니다. 필터를 조정해 보세요.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <SampleNotice />
    </div>
  )
}

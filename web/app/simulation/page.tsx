'use client'

import { useMemo, useState } from 'react'
import type { LucideIcon } from 'lucide-react'
import { ArrowRight, Users, Building2, Route, ShieldAlert } from 'lucide-react'
import { KpiCard } from '@/components/kpi-card'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PageHeader } from '@/components/page-header'
import { RiskGradeBadge } from '@/components/risk-grade-badge'
import { SampleNotice } from '@/components/sample-notice'
import { ClosureScatter } from '@/components/closure-scatter'
import { listRegions, getRegionByCode } from '@/lib/sample-data'
import { listHospitals } from '@/lib/hospitals'
import { simulateClosure, CLOSURE_VALIDATION } from '@/lib/simulation'
import { formatNumber } from '@/lib/utils'

export default function SimulationPage() {
  const regions = useMemo(() => listRegions(), [])
  const [regionCode, setRegionCode] = useState(regions[0].code)
  const region = getRegionByCode(regionCode) ?? regions[0]
  const hospitals = useMemo(() => listHospitals(region), [region])
  const [hospitalId, setHospitalId] = useState(hospitals[0]?.id ?? '')

  const hospital =
    hospitals.find((h) => h.id === hospitalId) ?? hospitals[0]
  const result = useMemo(
    () => (hospital ? simulateClosure(region, hospital) : null),
    [region, hospital],
  )

  const onRegionChange = (code: string) => {
    setRegionCode(code)
    const first = listHospitals(getRegionByCode(code) ?? regions[0])[0]
    setHospitalId(first?.id ?? '')
  }

  const v = CLOSURE_VALIDATION

  return (
    <div className="space-y-6">
      <PageHeader
        title="병원 폐업 영향 시뮬레이션"
        description="특정 의료기관이 폐업할 경우 지역 접근성과 취약도가 어떻게 변하는지 전·후로 비교합니다."
      />

      <Card>
        <CardHeader>
          <CardTitle>시뮬레이션 조건</CardTitle>
          <CardDescription>폐업을 가정할 지역과 의료기관을 선택하세요</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row">
          <Select value={regionCode} onValueChange={onRegionChange}>
            <SelectTrigger className="sm:w-64" aria-label="지역 선택">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {regions.map((r) => (
                <SelectItem key={r.code} value={r.code}>
                  {r.province} {r.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={hospitalId} onValueChange={setHospitalId}>
            <SelectTrigger className="sm:w-72" aria-label="의료기관 선택">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {hospitals.map((h) => (
                <SelectItem key={h.id} value={h.id}>
                  {h.name} ({h.type})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {result ? (
        <>
          <section
            className="grid grid-cols-2 gap-3 lg:grid-cols-4"
            aria-label="폐업 영향 요약"
          >
            <KpiDelta
              label="영향 인구"
              value={formatNumber(result.affectedPopulation)}
              unit="명"
              sub={`고령자 ${formatNumber(result.affectedSenior)}명`}
              icon={Users}
            />
            <KpiDelta
              label="의료기관"
              value={`${result.before.hospitalCount} → ${result.after.hospitalCount}`}
              unit="개소"
              sub="1개소 감소"
              icon={Building2}
            />
            <KpiDelta
              label="평균 접근거리"
              value={`+${result.distanceDeltaKm.toFixed(2)}`}
              unit="km"
              sub={`${result.before.avgAccessDistanceKm} → ${result.after.avgAccessDistanceKm}km`}
              icon={Route}
            />
            <KpiDelta
              label="취약도 변화"
              value={`+${result.vulnerabilityDelta.toFixed(1)}`}
              unit="점"
              sub={`${result.before.vulnerabilityTotal.toFixed(1)} → ${result.after.vulnerabilityTotal.toFixed(1)}`}
              icon={ShieldAlert}
              accent="var(--risk-high)"
            />
          </section>

          <Card>
            <CardHeader>
              <CardTitle>폐업 전 · 후 비교</CardTitle>
              <CardDescription>{region.province} {region.name} · {hospital.name} 폐업 가정</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
                <BeforeAfterCard
                  title="폐업 전"
                  distance={result.before.avgAccessDistanceKm}
                  drive={result.before.avgDriveMinutes}
                  score={result.before.vulnerabilityTotal}
                />
                <ArrowRight className="mx-auto hidden size-6 text-muted-foreground sm:block" />
                <BeforeAfterCard
                  title="폐업 후"
                  distance={result.after.avgAccessDistanceKm}
                  drive={result.after.avgDriveMinutes}
                  score={result.after.vulnerabilityTotal}
                  highlight
                />
              </div>
              <p className="rounded-lg bg-muted/50 px-4 py-3 text-sm leading-relaxed text-muted-foreground text-pretty break-keep">
                {result.explanation}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>실제 폐업 사례 검증</CardTitle>
              <CardDescription>
                과거 {v.caseCount}건의 폐업 사례로 예측 방향성을 점검했습니다
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-6 lg:grid-cols-2">
              <div className="space-y-3">
                <div className="flex flex-wrap gap-3">
                  <MiniStat label="검증 사례" value={`${v.caseCount}건`} />
                  <MiniStat
                    label="방향 일치율"
                    value={`${v.directionAgreementPct}%`}
                  />
                  <MiniStat
                    label="거리 증가 관측"
                    value={`${v.observedDistanceIncreaseCases}건`}
                  />
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground text-pretty break-keep">
                  예측이 &lsquo;접근성 악화&rsquo;를 가리킨 사례의 상당수가 실제로도
                  거리 증가로 이어졌지만, 일부는 대체 의료기관 덕분에 변화가 크지
                  않았습니다. 방향 일치율({v.directionAgreementPct}%)만으로 성능을
                  단정하기보다, 사례 수와 예측·관측 산점도를 함께 해석해야 합니다.
                </p>
              </div>
              <div>
                <ClosureScatter />
                <p className="mt-1 text-center text-xs text-muted-foreground">
                  점이 대각선에 가까울수록 예측과 관측이 일치
                </p>
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            선택한 지역에 시뮬레이션할 의료기관 정보가 없습니다.
          </CardContent>
        </Card>
      )}

      <SampleNotice />
    </div>
  )
}

import type { LucideIcon } from 'lucide-react'
import { KpiCard } from '@/components/kpi-card'

function KpiDelta(props: {
  label: string
  value: string
  unit?: string
  sub?: string
  icon?: LucideIcon
  accent?: string
}) {
  return <KpiCard {...props} />
}

function BeforeAfterCard({
  title,
  distance,
  drive,
  score,
  highlight,
}: {
  title: string
  distance: number
  drive: number
  score: number
  highlight?: boolean
}) {
  return (
    <div
      className={`rounded-lg border p-4 ${highlight ? 'border-[var(--risk-high)] bg-[color-mix(in_oklch,var(--risk-high)_8%,var(--card))]' : 'border-border bg-card'}`}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-semibold text-foreground">{title}</span>
        <RiskGradeBadge score={score} />
      </div>
      <dl className="space-y-2 text-sm">
        <div className="flex justify-between">
          <dt className="text-muted-foreground">평균 접근거리</dt>
          <dd className="font-mono font-medium">{distance.toFixed(2)}km</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">평균 이동시간</dt>
          <dd className="font-mono font-medium">{drive.toFixed(1)}분</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">취약도</dt>
          <dd className="font-mono font-semibold">{score.toFixed(1)}</dd>
        </div>
      </dl>
    </div>
  )
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-mono text-lg font-bold text-foreground">{value}</p>
    </div>
  )
}

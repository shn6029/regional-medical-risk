import { Activity, MapPin, ShieldAlert, Users, Route } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatNumber, formatPercent } from '@/lib/utils'
import { getRiskFromCoverage } from '@/lib/api'
import type { AccessibilitySummary, RegionScore } from '@/lib/types'

interface MetricCardProps {
  label: string
  value: string
  hint?: string
  icon: React.ElementType
  accent?: string
}

function MetricCard({ label, value, hint, icon: Icon, accent }: MetricCardProps) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3 p-4">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-1 font-mono text-2xl font-semibold tracking-tight text-foreground">
            {value}
          </p>
          {hint && <p className="mt-1 truncate text-xs text-muted-foreground">{hint}</p>}
        </div>
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
          style={{
            backgroundColor: `color-mix(in oklch, ${accent ?? 'var(--primary)'} 12%, transparent)`,
            color: accent ?? 'var(--primary)',
          }}
        >
          <Icon className="h-4.5 w-4.5" />
        </span>
      </CardContent>
    </Card>
  )
}

export function SummaryCardsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="p-4">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="mt-3 h-7 w-24" />
            <Skeleton className="mt-2 h-3 w-20" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export function SummaryCards({
  summary,
  regions,
}: {
  summary: AccessibilitySummary
  regions: RegionScore[]
}) {
  const atRiskCount = regions.filter((r) => {
    const level = getRiskFromCoverage(r.senior_within_threshold_pct).level
    return level === 'high' || level === 'critical'
  }).length

  const totalPopulation = regions.reduce((sum, r) => sum + r.population, 0)

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
      <MetricCard
        label="분석 지역"
        value={`${formatNumber(regions.length)}개`}
        hint="시·군·구 단위"
        icon={MapPin}
      />
      <MetricCard
        label="총 인구"
        value={formatNumber(totalPopulation)}
        hint={`고령자 ${formatNumber(summary.senior_population)}명`}
        icon={Users}
      />
      <MetricCard
        label="고령자 접근성 커버리지"
        value={formatPercent(summary.senior_coverage_pct)}
        hint={`${formatNumber(summary.covered_senior_population)}명 임계시간 내`}
        icon={Activity}
        accent="var(--risk-low)"
      />
      <MetricCard
        label="주의·위험 지역"
        value={`${formatNumber(atRiskCount)}개`}
        hint="고령자 커버리지 60% 미만"
        icon={ShieldAlert}
        accent="var(--risk-high)"
      />
      <MetricCard
        label="분석 경로 수"
        value={formatNumber(summary.route_count)}
        hint={`임계 ${summary.catchment_minutes}분 · ${summary.method}`}
        icon={Route}
      />
    </div>
  )
}

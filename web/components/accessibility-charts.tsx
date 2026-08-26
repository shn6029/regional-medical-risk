'use client'

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getRiskFromCoverage } from '@/lib/api'
import type { RegionScore, RiskLevel } from '@/lib/types'

const RISK_META: { level: RiskLevel; label: string; hex: string }[] = [
  { level: 'critical', label: '위험', hex: '#dc2626' },
  { level: 'high', label: '주의', hex: '#f97316' },
  { level: 'mid', label: '양호', hex: '#eab308' },
  { level: 'low', label: '안정', hex: '#16a34a' },
]

function ChartTooltip({
  active,
  payload,
  suffix,
}: {
  active?: boolean
  payload?: { payload: Record<string, unknown>; value: number }[]
  suffix?: string
}) {
  if (!active || !payload?.length) return null
  const p = payload[0]
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-popover-foreground">{String(p.payload.name)}</p>
      <p className="text-muted-foreground">
        {p.value.toLocaleString('ko-KR')}
        {suffix}
      </p>
    </div>
  )
}

export function AccessibilityCharts({ regions }: { regions: RegionScore[] }) {
  const distribution = RISK_META.map((meta) => ({
    name: meta.label,
    hex: meta.hex,
    value: regions.filter(
      (r) => getRiskFromCoverage(r.senior_within_threshold_pct).level === meta.level,
    ).length,
  }))

  const bottom = [...regions]
    .sort((a, b) => a.senior_within_threshold_pct - b.senior_within_threshold_pct)
    .slice(0, 8)
    .map((r) => ({
      name: r.region_name,
      value: Number(r.senior_within_threshold_pct.toFixed(1)),
      hex: getRiskFromCoverage(r.senior_within_threshold_pct).hex,
    }))

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>위험도 지역 분포</CardTitle>
          <p className="text-sm text-muted-foreground">
            고령자 접근성 커버리지 기준으로 분류한 지역 수
          </p>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={distribution} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip
                cursor={{ fill: 'var(--muted)', opacity: 0.4 }}
                content={<ChartTooltip suffix="개" />}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={64}>
                {distribution.map((d) => (
                  <Cell key={d.name} fill={d.hex} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>고령자 접근성 하위 지역</CardTitle>
          <p className="text-sm text-muted-foreground">
            임계시간 내 고령자 비율이 가장 낮은 지역 (%)
          </p>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart
              data={bottom}
              layout="vertical"
              margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
              <XAxis
                type="number"
                domain={[0, 100]}
                tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={72}
                tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: 'var(--muted)', opacity: 0.4 }}
                content={<ChartTooltip suffix="%" />}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={22}>
                {bottom.map((d) => (
                  <Cell key={d.name} fill={d.hex} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}

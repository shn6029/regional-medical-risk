'use client'

import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Legend,
} from 'recharts'
import { FORECAST_SERIES, FORECAST_MODELS, EVAL_YEAR } from '@/lib/forecast'
import { formatNumber } from '@/lib/utils'

const AXIS = 'var(--muted-foreground)'
const GRID = 'var(--border)'

function tickManman(v: number) {
  return `${(v / 10000).toFixed(0)}만`
}

/** 실측(2016~2024) vs 예측(2024~2028) 라인차트. */
export function ForecastSeriesChart() {
  return (
    <ResponsiveContainer width="100%" height={340}>
      <LineChart
        data={FORECAST_SERIES}
        margin={{ top: 28, right: 16, bottom: 4, left: 12 }}
      >
        <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="year" stroke={AXIS} fontSize={12} tickLine={false} />
        <YAxis
          stroke={AXIS}
          fontSize={12}
          tickLine={false}
          axisLine={false}
          tickFormatter={tickManman}
          width={52}
        />
        <Tooltip
          formatter={(value: number) => [`${formatNumber(value)}명`, '']}
          contentStyle={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <ReferenceLine
          x={EVAL_YEAR}
          stroke={AXIS}
          strokeDasharray="4 4"
          label={{ value: '예측 시작', position: 'top', fontSize: 11, fill: AXIS }}
        />
        <Line
          name="실측"
          type="monotone"
          dataKey="actual"
          stroke="var(--chart-1)"
          strokeWidth={2.5}
          dot={false}
          connectNulls
        />
        <Line
          name="예측"
          type="monotone"
          dataKey="predicted"
          stroke="var(--chart-4)"
          strokeWidth={2.5}
          strokeDasharray="5 4"
          dot={false}
          connectNulls
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}

/** 모델별 MAE 비교 막대. 기준선은 강조 색으로 구분. */
export function ModelMaeChart() {
  const data = FORECAST_MODELS.map((m) => ({
    name: m.label,
    mae: m.mae,
    isBaseline: m.isBaseline,
  }))
  return (
    <ResponsiveContainer width="100%" height={380}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 12, right: 16, bottom: 12, left: 8 }}
      >
        <CartesianGrid stroke={GRID} strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" stroke={AXIS} fontSize={12} tickLine={false} />
        <YAxis
          type="category"
          dataKey="name"
          stroke={AXIS}
          fontSize={12}
          tickLine={false}
          axisLine={false}
          width={96}
        />
        <Tooltip
          formatter={(value: number) => [`${formatNumber(value)}명`, 'MAE']}
          contentStyle={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Bar dataKey="mae" radius={[0, 4, 4, 0]}>
          {data.map((d) => (
            <Cell
              key={d.name}
              fill={d.isBaseline ? 'var(--chart-2)' : 'var(--chart-1)'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

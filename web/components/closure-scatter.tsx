'use client'

import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ZAxis,
} from 'recharts'
import { CLOSURE_VALIDATION } from '@/lib/simulation'

/**
 * 예측 거리 변화(x) vs 관측 거리 변화(y) 산점도.
 * 대각선(y=x)에 가까울수록 예측이 관측과 일치한다.
 */
export function ClosureScatter() {
  const data = CLOSURE_VALIDATION.scatter
  const max =
    Math.ceil(
      Math.max(...data.flatMap((d) => [d.predicted, d.observed])) * 10,
    ) / 10

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 16, left: 4 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
        <XAxis
          type="number"
          dataKey="predicted"
          name="예측"
          unit="km"
          domain={[0, max]}
          stroke="var(--muted-foreground)"
          fontSize={12}
          tickLine={false}
          label={{
            value: '예측 거리 변화(km)',
            position: 'insideBottom',
            offset: -8,
            fontSize: 11,
            fill: 'var(--muted-foreground)',
          }}
        />
        <YAxis
          type="number"
          dataKey="observed"
          name="관측"
          unit="km"
          domain={[0, max]}
          stroke="var(--muted-foreground)"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          width={36}
        />
        <ZAxis range={[80, 80]} />
        <ReferenceLine
          segment={[
            { x: 0, y: 0 },
            { x: max, y: max },
          ]}
          stroke="var(--muted-foreground)"
          strokeDasharray="4 4"
        />
        <Tooltip
          cursor={{ strokeDasharray: '3 3' }}
          formatter={(value: number, name: string) => [`${value}km`, name]}
          contentStyle={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Scatter data={data} fill="var(--chart-1)" fillOpacity={0.75} />
      </ScatterChart>
    </ResponsiveContainer>
  )
}

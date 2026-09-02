'use client'

import { TrendingUp, Target, AlertCircle } from 'lucide-react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { PageHeader } from '@/components/page-header'
import { KpiCard } from '@/components/kpi-card'
import { SampleNotice } from '@/components/sample-notice'
import {
  ForecastSeriesChart,
  ModelMaeChart,
} from '@/components/forecast-charts'
import {
  FORECAST_MODELS,
  bestBaseline,
  getModel,
  improvementOverBaseline,
  SELECTED_MODEL_ID,
  EVAL_YEAR,
} from '@/lib/forecast'
import { formatNumber } from '@/lib/utils'

export default function ForecastPage() {
  const baseline = bestBaseline()
  const selected = getModel(SELECTED_MODEL_ID)
  const improvement = improvementOverBaseline(SELECTED_MODEL_ID)
  const beatsBaseline = improvement > 0

  return (
    <div className="space-y-6">
      <PageHeader
        title="고령인구 예측"
        description={`전국 65세 이상 인구 추이와 ${EVAL_YEAR}년 기준 예측 모델 검증 결과입니다. 여러 모델을 단순 기준선과 비교해 실질적 개선 여부를 평가했습니다.`}
      />

      <section
        className="grid grid-cols-2 gap-3 lg:grid-cols-4"
        aria-label="예측 요약"
      >
        <KpiCard
          label="2028년 예측"
          value="1,193"
          unit="만명"
          sub="65세 이상"
          icon={TrendingUp}
        />
        <KpiCard
          label="최적 기준선 MAE"
          value={formatNumber(baseline.mae)}
          unit="명"
          sub={baseline.label}
          icon={Target}
        />
        <KpiCard
          label="대표 모델 MAE"
          value={formatNumber(selected.mae)}
          unit="명"
          sub={selected.label}
          icon={Target}
          accent="var(--chart-1)"
        />
        <KpiCard
          label="기준선 대비"
          value={`${improvement > 0 ? '+' : ''}${improvement}`}
          unit="%"
          sub={beatsBaseline ? '기준선보다 우수' : '기준선과 동등 이하'}
          icon={AlertCircle}
          accent={beatsBaseline ? 'var(--risk-low)' : 'var(--risk-high)'}
        />
      </section>

      <Card className="border-l-4 border-l-primary">
        <CardContent className="flex items-start gap-3 py-4">
          <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-secondary text-primary">
            <AlertCircle className="size-4" />
          </span>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-foreground">모델 검증 결론</p>
            <p className="text-sm leading-relaxed text-muted-foreground text-pretty break-keep">
              Random Forest·XGBoost 등 복잡한 머신러닝 모델은 &lsquo;선형 추세&rsquo;
              기준선(MAE {formatNumber(baseline.mae)}명)을 유의미하게 넘어서지
              못했습니다. 데이터가 단조 증가 추세를 보여 단순 모델이 이미 강력한
              기준선이 되기 때문입니다. 복잡도보다 해석 가능성과 안정성을 기준으로
              모델을 선택하는 것이 합리적입니다.
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="min-w-0 lg:col-span-3">
          <CardHeader>
            <CardTitle>전국 65세 이상 인구 추이</CardTitle>
            <CardDescription>실측(2016–2024) 및 예측(2024–2028)</CardDescription>
          </CardHeader>
          <CardContent>
            <ForecastSeriesChart />
            <p className="mt-2 text-xs leading-relaxed text-muted-foreground text-pretty">
              점선 구간은 예측값이며 불확실성을 포함합니다. 예측이 멀어질수록
              신뢰구간이 넓어진다는 점을 감안해 해석해야 합니다.
            </p>
          </CardContent>
        </Card>

        <Card className="min-w-0 lg:col-span-2">
          <CardHeader>
            <CardTitle>모델별 예측오차(MAE)</CardTitle>
            <CardDescription>막대가 짧을수록 정확 · 청록은 기준선</CardDescription>
          </CardHeader>
          <CardContent>
            <ModelMaeChart />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>모델 성능 요약</CardTitle>
          <CardDescription>{EVAL_YEAR}년 홀드아웃 검증 기준</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50 text-left">
                  <th className="px-4 py-2.5 font-medium text-muted-foreground">모델</th>
                  <th className="px-4 py-2.5 font-medium text-muted-foreground">구분</th>
                  <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">
                    MAE (명)
                  </th>
                  <th className="hidden px-4 py-2.5 text-right font-medium text-muted-foreground sm:table-cell">
                    기준선 대비
                  </th>
                </tr>
              </thead>
              <tbody>
                {FORECAST_MODELS.map((m) => {
                  const diff = Number(
                    (((baseline.mae - m.mae) / baseline.mae) * 100).toFixed(1),
                  )
                  return (
                    <tr key={m.id} className="border-b border-border last:border-0">
                      <td className="px-4 py-2.5 font-medium text-foreground break-keep">
                        {m.label}
                      </td>
                      <td className="px-4 py-2.5 text-muted-foreground">
                        {m.isBaseline ? '기준선' : '학습 모델'}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono">
                        {formatNumber(m.mae)}
                      </td>
                      <td className="hidden px-4 py-2.5 text-right font-mono sm:table-cell">
                        <span
                          style={{
                            color: diff > 0 ? 'var(--risk-low)' : 'var(--risk-high)',
                          }}
                        >
                          {m.isBaseline ? '—' : `${diff > 0 ? '+' : ''}${diff}%`}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <SampleNotice />
    </div>
  )
}

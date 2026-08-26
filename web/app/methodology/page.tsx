'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Accordion } from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { PageHeader } from '@/components/page-header'
import { Database, Sigma, GitCompare, TriangleAlert } from 'lucide-react'

const DATA_SOURCES = [
  {
    name: '주민등록 인구통계',
    org: '행정안전부',
    detail: '시·군·자치구 단위 총인구 및 65세 이상 고령인구',
  },
  {
    name: '건강보험 요양기관 현황',
    org: '건강보험심사평가원',
    detail: '병원 위치·병상 수·진료과목 (병원 공급 지표)',
  },
  {
    name: '도로망·통행시간',
    org: 'OpenStreetMap / 국가교통DB',
    detail: '수요점–병원 간 자동차 통행시간 (임계 30분)',
  },
  {
    name: '행정구역 경계',
    org: '통계청 SGIS',
    detail: '시·군·구 중심좌표 및 경계 폴리곤',
  },
]

export default function MethodologyPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="데이터 · 방법론"
        description="본 대시보드가 사용하는 데이터 출처와 접근성·취약도 산출 방식, 그리고 해석 시 유의사항을 정리했습니다."
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Database className="size-4 text-primary" aria-hidden />
            데이터 출처
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          {DATA_SOURCES.map((s) => (
            <div key={s.name} className="rounded-lg border border-border bg-muted/30 p-4">
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium text-foreground text-pretty break-keep">{s.name}</p>
                <Badge variant="secondary" className="shrink-0 text-xs">
                  {s.org}
                </Badge>
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground break-keep">
                {s.detail}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Sigma className="size-4 text-primary" aria-hidden />
              2SFCA 접근성 지표
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-relaxed text-muted-foreground break-keep">
            <p>
              2SFCA(2단계 유동 의료권, 2-Step Floating Catchment Area)는 병원의
              공급량과 주변 인구의 수요량을 두 단계로 나누어 지역별 의료 접근성을
              계산하는 표준 방법입니다.
            </p>
            <ol className="list-decimal space-y-1.5 pl-5">
              <li>
                <span className="text-foreground">1단계:</span> 각 병원마다 임계
                통행시간(30분) 내 인구를 합산해 공급–수요비(병상/인구)를 구합니다.
              </li>
              <li>
                <span className="text-foreground">2단계:</span> 각 수요점에서 임계
                시간 내 도달 가능한 병원들의 공급–수요비를 합산해 접근성 점수로
                삼습니다.
              </li>
            </ol>
            <p>
              커버리지는 &ldquo;임계시간 내 하나 이상의 병원에 도달 가능한 고령
              인구 비율&rdquo;로 정의하며, 본 대시보드의 위험등급은 이 커버리지에서
              파생된 참고 지표입니다.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <GitCompare className="size-4 text-primary" aria-hidden />
              취약도 점수 구성
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-relaxed text-muted-foreground break-keep">
            <p>
              지역 취약도(0–100)는 네 가지 요인의 가중 합으로 산출합니다. 점수가
              높을수록 의료 인프라가 취약함을 의미합니다.
            </p>
            <ul className="space-y-1.5">
              {[
                ['접근성 부족', '35점', '2SFCA 커버리지가 낮을수록'],
                ['고령화 정도', '30점', '고령인구 비율이 높을수록'],
                ['공급 부족', '20점', '인구 대비 병상 수가 적을수록'],
                ['지리적 고립', '15점', '병원까지 평균 거리가 멀수록'],
              ].map(([label, max, desc]) => (
                <li key={label} className="flex items-baseline justify-between gap-3">
                  <span>
                    <span className="text-foreground">{label}</span>
                    <span className="ml-1.5 text-xs">{desc}</span>
                  </span>
                  <span className="shrink-0 font-mono text-xs text-foreground">{max}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <TriangleAlert className="size-4 text-[var(--risk-high)]" aria-hidden />
            한계와 해석 시 유의사항
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Accordion
            defaultOpenId="1"
            items={[
              {
                id: '1',
                title: '위험등급은 참고 지표입니다',
                content:
                  '위험등급은 고령자 접근성 커버리지에서 파생한 상대적 참고 지표이며, 실제 의료 수요·질·응급 대응 역량을 직접 측정한 값이 아닙니다. 정책 판단의 단일 근거로 사용해서는 안 됩니다.',
              },
              {
                id: '2',
                title: '예측 모델의 한계',
                content:
                  '고령인구 예측에서 복잡한 머신러닝 모델이 단순 추세 기반 기준선보다 일관되게 낫지 않았습니다. 표본이 적고 추세가 단조로운 인구 시계열에서는 단순 모델이 과적합을 피해 더 안정적일 수 있습니다. 따라서 예측값은 불확실성을 동반한 시나리오로 해석해야 합니다.',
              },
              {
                id: '3',
                title: '통행시간·경계의 근사',
                content:
                  '통행시간은 평상시 도로망 기준 추정치로 교통혼잡·기상·야간 응급 상황을 반영하지 않습니다. 지역 대표 좌표(중심점)를 사용하므로 넓은 시·군 내부의 편차는 평활화됩니다.',
              },
              {
                id: '4',
                title: '샘플 데이터 표기',
                content:
                  '2SFCA 접근성 페이지는 기존 FastAPI 서버의 실제 실행 결과를 조회합니다. 그 외 지역 상세·예측·시뮬레이션 화면의 세부 수치 중 일부는 방법론을 설명하기 위한 예시 데이터이며, 해당 화면에 “예시” 안내가 함께 표기됩니다.',
              },
            ]}
          />
        </CardContent>
      </Card>
    </div>
  )
}

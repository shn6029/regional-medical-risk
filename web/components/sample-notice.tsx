import { Info } from 'lucide-react'

/**
 * 지역별 세부 수치가 대표성 있는 샘플 데이터임을 명확히 알리는 배너.
 * 국가 집계 KPI는 실제 분석 수치이며, 지역 단위 값은 FastAPI 연동 시
 * 그대로 교체된다.
 */
export function SampleNotice({ className }: { className?: string }) {
  return (
    <div
      className={`flex items-start gap-2 rounded-lg border border-border bg-muted/50 px-3 py-2 text-xs leading-relaxed text-muted-foreground ${className ?? ''}`}
      role="note"
    >
      <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
      <p className="text-pretty">
        지역 단위 세부 지표는 분석 방법을 보여주기 위한 대표 샘플입니다. 국가
        집계 지표는 실제 분석 결과이며, FastAPI 연동 시 지역별 값이 실데이터로
        대체됩니다.
      </p>
    </div>
  )
}

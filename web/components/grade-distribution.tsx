import { RISK_HEX, RISK_LABEL, RISK_RANGE, RISK_ORDER } from '@/lib/risk'
import type { RiskLevel } from '@/lib/types'

/**
 * 등급별 지역 수를 가로 스택 막대 + 범례로 표현한다.
 */
export function GradeDistribution({
  counts,
}: {
  counts: Record<string, number>
}) {
  const total = RISK_ORDER.reduce((sum, lvl) => sum + (counts[lvl] ?? 0), 0)

  return (
    <div className="space-y-4">
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
        {RISK_ORDER.map((lvl) => {
          const count = counts[lvl] ?? 0
          const pct = total > 0 ? (count / total) * 100 : 0
          if (pct === 0) return null
          return (
            <div
              key={lvl}
              style={{ width: `${pct}%`, backgroundColor: RISK_HEX[lvl] }}
              title={`${RISK_LABEL[lvl]} ${count}개`}
            />
          )
        })}
      </div>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {RISK_ORDER.map((lvl: RiskLevel) => {
          const count = counts[lvl] ?? 0
          const pct = total > 0 ? (count / total) * 100 : 0
          return (
            <li key={lvl} className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5">
                <span
                  className="size-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: RISK_HEX[lvl] }}
                  aria-hidden
                />
                <span className="text-sm font-medium text-foreground">
                  {RISK_LABEL[lvl]}
                </span>
              </div>
              <div className="flex items-baseline gap-1 pl-4">
                <span className="font-mono text-lg font-bold text-foreground">
                  {count}
                </span>
                <span className="text-xs text-muted-foreground">
                  개 · {pct.toFixed(0)}%
                </span>
              </div>
              <span className="pl-4 text-[0.7rem] text-muted-foreground">
                {RISK_RANGE[lvl]}점
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

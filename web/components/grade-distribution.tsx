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
      <ul className="space-y-3">
        {RISK_ORDER.map((lvl: RiskLevel) => {
          const count = counts[lvl] ?? 0
          const pct = total > 0 ? (count / total) * 100 : 0
          const maxCount = Math.max(
            1,
            ...RISK_ORDER.map((l) => counts[l] ?? 0),
          )
          const barPct = (count / maxCount) * 100
          return (
            <li key={lvl} className="space-y-1.5">
              <div className="flex items-center justify-between gap-2 text-sm">
                <span className="flex items-center gap-1.5">
                  <span
                    className="size-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: RISK_HEX[lvl] }}
                    aria-hidden
                  />
                  <span className="font-medium text-foreground">
                    {RISK_LABEL[lvl]}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {RISK_RANGE[lvl]}점
                  </span>
                </span>
                <span className="shrink-0 tabular-nums">
                  <span className="font-mono font-bold text-foreground">
                    {count}
                  </span>
                  <span className="ml-1 text-xs text-muted-foreground">
                    개 · {pct.toFixed(0)}%
                  </span>
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${barPct}%`, backgroundColor: RISK_HEX[lvl] }}
                />
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

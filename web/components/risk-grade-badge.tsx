import { cn } from '@/lib/utils'
import { getRiskGrade, RISK_RANGE } from '@/lib/risk'
import type { RiskInfo } from '@/lib/types'

/**
 * 위험등급 badge. 점수 또는 RiskInfo를 받는다.
 * 색상만으로 정보를 전달하지 않도록 등급명 텍스트를 항상 포함한다.
 */
export function RiskGradeBadge({
  score,
  risk,
  showRange = false,
  className,
}: {
  score?: number
  risk?: RiskInfo
  showRange?: boolean
  className?: string
}) {
  const info = risk ?? getRiskGrade(score ?? 0)
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-semibold',
        className,
      )}
      style={{
        backgroundColor: `color-mix(in oklch, ${info.color} 16%, transparent)`,
        color: info.color,
      }}
    >
      <span
        className="size-1.5 rounded-full"
        style={{ backgroundColor: info.color }}
        aria-hidden
      />
      {info.label}
      {showRange ? (
        <span className="font-normal opacity-80">{RISK_RANGE[info.level]}</span>
      ) : null}
    </span>
  )
}

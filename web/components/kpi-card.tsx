import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * KPI 카드. 값과 단위의 시각적 계층을 명확히 한다.
 */
export function KpiCard({
  label,
  value,
  unit,
  sub,
  icon: Icon,
  accent,
  className,
}: {
  label: string
  value: string
  unit?: string
  sub?: string
  icon?: LucideIcon
  accent?: string
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col gap-2 rounded-lg border border-border bg-card p-4',
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted-foreground break-keep">
          {label}
        </span>
        {Icon ? (
          <span
            className="flex size-7 shrink-0 items-center justify-center rounded-md bg-secondary"
            style={accent ? { color: accent } : undefined}
          >
            <Icon className="size-4" />
          </span>
        ) : null}
      </div>
      <div className="flex items-baseline gap-1">
        <span className="font-mono text-2xl font-bold tracking-tight text-foreground">
          {value}
        </span>
        {unit ? (
          <span className="text-sm font-medium text-muted-foreground">{unit}</span>
        ) : null}
      </div>
      {sub ? (
        <span className="text-xs leading-relaxed text-muted-foreground break-keep">
          {sub}
        </span>
      ) : null}
    </div>
  )
}

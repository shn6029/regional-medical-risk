import { cn } from '@/lib/utils'

/**
 * 단순 진행 막대. value는 0~100.
 * color는 CSS 색상 문자열(예: var(--risk-high) 또는 hex).
 */
export function Progress({
  value,
  color,
  className,
  trackClassName,
}: {
  value: number
  color?: string
  className?: string
  trackClassName?: string
}) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div
      className={cn('h-2.5 w-full overflow-hidden rounded-full bg-muted', trackClassName)}
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={cn('h-full rounded-full transition-[width] duration-500', className)}
        style={{ width: `${clamped}%`, backgroundColor: color ?? 'var(--primary)' }}
      />
    </div>
  )
}

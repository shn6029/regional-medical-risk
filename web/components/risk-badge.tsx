import { cn } from '@/lib/utils'
import { getRiskFromCoverage } from '@/lib/api'

export function RiskBadge({
  coveragePct,
  className,
}: {
  coveragePct: number
  className?: string
}) {
  const risk = getRiskFromCoverage(coveragePct)
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium',
        className,
      )}
      style={{
        backgroundColor: `color-mix(in oklch, ${risk.color} 16%, transparent)`,
        color: risk.color,
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: risk.color }}
        aria-hidden
      />
      {risk.label}
    </span>
  )
}

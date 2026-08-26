'use client'

import { Search, X } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import type { RiskLevel } from '@/lib/types'

export interface FilterState {
  province: string
  risk: RiskLevel | 'all'
  query: string
}

const RISK_OPTIONS: { value: RiskLevel | 'all'; label: string }[] = [
  { value: 'all', label: '전체 위험도' },
  { value: 'critical', label: '위험' },
  { value: 'high', label: '주의' },
  { value: 'mid', label: '양호' },
  { value: 'low', label: '안정' },
]

export function Filters({
  provinces,
  value,
  onChange,
}: {
  provinces: string[]
  value: FilterState
  onChange: (next: FilterState) => void
}) {
  const hasActive = value.province !== 'all' || value.risk !== 'all' || value.query !== ''

  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-3 sm:flex-row sm:items-center">
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          value={value.query}
          onChange={(e) => onChange({ ...value, query: e.target.value })}
          placeholder="지역명 검색 (예: 강남, 안동)"
          aria-label="지역명 검색"
          className="h-9 w-full rounded-md border bg-background pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      <div className="flex gap-2">
        <Select
          value={value.province}
          onValueChange={(province) => onChange({ ...value, province })}
        >
          <SelectTrigger className="w-full sm:w-40" aria-label="시·도 선택">
            <SelectValue placeholder="시·도" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">전체 시·도</SelectItem>
            {provinces.map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={value.risk}
          onValueChange={(risk) => onChange({ ...value, risk: risk as FilterState['risk'] })}
        >
          <SelectTrigger className="w-full sm:w-36" aria-label="위험도 선택">
            <SelectValue placeholder="위험도" />
          </SelectTrigger>
          <SelectContent>
            {RISK_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {hasActive && (
          <Button
            variant="ghost"
            size="icon"
            aria-label="필터 초기화"
            onClick={() => onChange({ province: 'all', risk: 'all', query: '' })}
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}

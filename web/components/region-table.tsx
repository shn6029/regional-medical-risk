'use client'

import { useState } from 'react'
import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { RiskBadge } from '@/components/risk-badge'
import { EmptyState } from '@/components/states'
import { cn, formatNumber, formatPercent } from '@/lib/utils'
import type { RegionScore } from '@/lib/types'

type SortKey =
  | 'region'
  | 'population'
  | 'senior_within_threshold_pct'
  | 'population_within_threshold_pct'
  | 'two_sfca_score'

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: 'region', label: '지역', numeric: false },
  { key: 'population', label: '인구', numeric: true },
  { key: 'senior_within_threshold_pct', label: '고령자 커버리지', numeric: true },
  { key: 'population_within_threshold_pct', label: '전체 커버리지', numeric: true },
  { key: 'two_sfca_score', label: '2SFCA 점수', numeric: true },
]

export function RegionTable({
  regions,
  selectedCode,
  onSelect,
}: {
  regions: RegionScore[]
  selectedCode: string | null
  onSelect: (code: string) => void
}) {
  const [sortKey, setSortKey] = useState<SortKey>('senior_within_threshold_pct')
  const [asc, setAsc] = useState(true)

  if (regions.length === 0) {
    return (
      <EmptyState
        title="조건에 맞는 지역이 없습니다"
        description="필터나 검색어를 조정해 다시 시도해 주세요."
      />
    )
  }

  const sorted = [...regions].sort((a, b) => {
    let cmp: number
    if (sortKey === 'region') {
      cmp = `${a.province_name}${a.region_name}`.localeCompare(
        `${b.province_name}${b.region_name}`,
        'ko',
      )
    } else {
      cmp = (a[sortKey] as number) - (b[sortKey] as number)
    }
    return asc ? cmp : -cmp
  })

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setAsc((v) => !v)
    } else {
      setSortKey(key)
      setAsc(key === 'region')
    }
  }

  return (
    <div className="rounded-xl border bg-card">
      <div className="max-h-[560px] overflow-auto">
        <Table>
          <TableHeader className="sticky top-0 z-10 bg-card">
            <TableRow>
              {COLUMNS.map((col) => {
                const active = col.key === sortKey
                const Icon = !active ? ChevronsUpDown : asc ? ArrowUp : ArrowDown
                return (
                  <TableHead
                    key={col.key}
                    className={cn(col.numeric && 'text-right')}
                  >
                    <button
                      type="button"
                      onClick={() => toggleSort(col.key)}
                      className={cn(
                        'inline-flex items-center gap-1 hover:text-foreground',
                        col.numeric && 'flex-row-reverse',
                        active && 'text-foreground',
                      )}
                    >
                      {col.label}
                      <Icon className="h-3 w-3" />
                    </button>
                  </TableHead>
                )
              })}
              <TableHead className="text-right">위험도</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((region) => (
              <TableRow
                key={region.region_code}
                data-state={region.region_code === selectedCode ? 'selected' : undefined}
                className="cursor-pointer"
                onClick={() => onSelect(region.region_code)}
              >
                <TableCell>
                  <div className="font-medium">{region.region_name}</div>
                  <div className="text-xs text-muted-foreground">
                    {region.province_name}
                  </div>
                </TableCell>
                <TableCell className="text-right font-mono">
                  {formatNumber(region.population)}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {formatPercent(region.senior_within_threshold_pct)}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {formatPercent(region.population_within_threshold_pct)}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {region.two_sfca_score.toFixed(4)}
                </TableCell>
                <TableCell className="text-right">
                  <RiskBadge coveragePct={region.senior_within_threshold_pct} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

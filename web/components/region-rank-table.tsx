'use client'

import { useRouter } from 'next/navigation'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { RiskGradeBadge } from '@/components/risk-grade-badge'
import { useSelection } from '@/components/selection-context'
import type { Region } from '@/lib/sample-data'

/**
 * 취약도 상위 지역 표. 행 클릭 시 지역 상세로 이동한다.
 * 소수점은 최대 한 자리. 모바일에서는 핵심 열만 노출한다.
 */
export function RegionRankTable({ regions }: { regions: Region[] }) {
  const router = useRouter()
  const { setSelectedRegionCode, setProvince } = useSelection()

  const open = (region: Region) => {
    setProvince(region.province)
    setSelectedRegionCode(region.code)
    router.push('/regions')
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50">
            <TableHead className="w-12 text-center">순위</TableHead>
            <TableHead className="hidden sm:table-cell">시·도</TableHead>
            <TableHead>시·군·구</TableHead>
            <TableHead className="text-right">취약도</TableHead>
            <TableHead>등급</TableHead>
            <TableHead className="hidden text-right md:table-cell">고령화율</TableHead>
            <TableHead className="hidden text-right md:table-cell">접근거리</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {regions.map((r, i) => (
            <TableRow
              key={r.code}
              onClick={() => open(r)}
              className="cursor-pointer"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter') open(r)
              }}
            >
              <TableCell className="text-center font-mono text-muted-foreground">
                {i + 1}
              </TableCell>
              <TableCell className="hidden text-muted-foreground sm:table-cell">
                {r.province}
              </TableCell>
              <TableCell className="font-medium text-foreground break-keep">
                {r.name}
              </TableCell>
              <TableCell className="text-right font-mono font-semibold">
                {r.vulnerability.total.toFixed(1)}
              </TableCell>
              <TableCell>
                <RiskGradeBadge score={r.vulnerability.total} />
              </TableCell>
              <TableCell className="hidden text-right font-mono text-muted-foreground md:table-cell">
                {r.agingRate.toFixed(1)}%
              </TableCell>
              <TableCell className="hidden text-right font-mono text-muted-foreground md:table-cell">
                {r.avgAccessDistanceKm.toFixed(1)}km
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

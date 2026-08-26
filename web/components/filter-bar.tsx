'use client'

import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useSelection } from '@/components/selection-context'
import { filterRegions, listProvinces } from '@/lib/sample-data'

/**
 * 한 줄 compact 필터 바: 지역명 검색 + 시·도 선택 + 시·군·구 선택.
 * 선택 상태는 전역 SelectionContext에 저장되어 페이지 간 공유된다.
 */
export function FilterBar() {
  const { province, query, selectedRegionCode, setProvince, setQuery, setSelectedRegionCode } =
    useSelection()
  const provinces = listProvinces()
  const regionsInProvince = filterRegions({ province })

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <div className="relative flex-1">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="지역명 검색 (예: 강남, 안동)"
          className="pl-9"
          aria-label="지역명 검색"
        />
      </div>
      <div className="flex gap-2">
        <Select
          value={province}
          onValueChange={(val) => {
            setProvince(val)
            setSelectedRegionCode(null)
          }}
        >
          <SelectTrigger className="w-[7.5rem] shrink-0" aria-label="시·도 선택">
            <SelectValue placeholder="시·도" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="전체">전체 시·도</SelectItem>
            {provinces.map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={selectedRegionCode ?? 'none'}
          onValueChange={(val) => setSelectedRegionCode(val === 'none' ? null : val)}
        >
          <SelectTrigger className="w-[8.5rem] shrink-0" aria-label="시·군·구 선택">
            <SelectValue placeholder="시·군·구" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">시·군·구 선택</SelectItem>
            {regionsInProvince.map((r) => (
              <SelectItem key={r.code} value={r.code}>
                {r.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}

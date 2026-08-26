'use client'

import * as React from 'react'
import { getRegionByCode, type Region } from '@/lib/sample-data'

interface SelectionState {
  province: string
  query: string
  selectedRegionCode: string | null
  setProvince: (p: string) => void
  setQuery: (q: string) => void
  setSelectedRegionCode: (code: string | null) => void
  selectedRegion: Region | undefined
}

const SelectionContext = React.createContext<SelectionState | null>(null)

export function SelectionProvider({ children }: { children: React.ReactNode }) {
  const [province, setProvince] = React.useState('전체')
  const [query, setQuery] = React.useState('')
  const [selectedRegionCode, setSelectedRegionCode] = React.useState<string | null>(null)

  const selectedRegion = selectedRegionCode
    ? getRegionByCode(selectedRegionCode)
    : undefined

  const value = React.useMemo<SelectionState>(
    () => ({
      province,
      query,
      selectedRegionCode,
      setProvince,
      setQuery,
      setSelectedRegionCode,
      selectedRegion,
    }),
    [province, query, selectedRegionCode, selectedRegion],
  )

  return <SelectionContext.Provider value={value}>{children}</SelectionContext.Provider>
}

export function useSelection(): SelectionState {
  const ctx = React.useContext(SelectionContext)
  if (!ctx) throw new Error('useSelection must be used within SelectionProvider')
  return ctx
}

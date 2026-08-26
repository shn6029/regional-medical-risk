'use client'

import * as React from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface AccordionItemData {
  id: string
  title: string
  content: React.ReactNode
}

export function Accordion({
  items,
  defaultOpenId,
}: {
  items: AccordionItemData[]
  defaultOpenId?: string
}) {
  const [openId, setOpenId] = React.useState<string | null>(defaultOpenId ?? null)
  return (
    <div className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-card">
      {items.map((item) => {
        const open = openId === item.id
        return (
          <div key={item.id}>
            <button
              type="button"
              aria-expanded={open}
              onClick={() => setOpenId(open ? null : item.id)}
              className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left text-sm font-medium text-foreground hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
            >
              <span className="text-pretty">{item.title}</span>
              <ChevronDown
                className={cn(
                  'size-4 shrink-0 text-muted-foreground transition-transform',
                  open && 'rotate-180',
                )}
                aria-hidden
              />
            </button>
            {open ? (
              <div className="px-4 pb-4 text-sm leading-relaxed text-muted-foreground">
                {item.content}
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}

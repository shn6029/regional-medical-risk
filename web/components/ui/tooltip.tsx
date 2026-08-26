'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * 경량 툴팁. hover/focus 시 설명을 표시한다.
 * 접근성을 위해 트리거는 button, 내용은 role="tooltip"로 노출한다.
 */
export function InfoTooltip({
  content,
  children,
  className,
}: {
  content: React.ReactNode
  children?: React.ReactNode
  className?: string
}) {
  const [open, setOpen] = React.useState(false)
  return (
    <span className="relative inline-flex">
      <button
        type="button"
        aria-label="설명 보기"
        className={cn(
          'inline-flex items-center text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-full',
          className,
        )}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={(e) => {
          e.preventDefault()
          setOpen((v) => !v)
        }}
      >
        {children}
      </button>
      {open ? (
        <span
          role="tooltip"
          className="absolute bottom-full left-1/2 z-50 mb-2 w-56 -translate-x-1/2 rounded-md border border-border bg-popover px-3 py-2 text-xs leading-relaxed text-popover-foreground shadow-md"
        >
          {content}
        </span>
      ) : null}
    </span>
  )
}

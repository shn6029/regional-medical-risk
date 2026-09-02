'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Activity,
  BookOpen,
  Building2,
  LayoutDashboard,
  Map as MapIcon,
  MapPin,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  TrendingUp,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItem {
  href: string
  label: string
  icon: React.ComponentType<{ className?: string }>
}

const NAV: NavItem[] = [
  { href: '/', label: '전국 개요', icon: LayoutDashboard },
  { href: '/map', label: '전국 지도', icon: MapIcon },
  { href: '/regions', label: '지역 상세', icon: MapPin },
  { href: '/forecast', label: '고령인구 예측', icon: TrendingUp },
  { href: '/simulation', label: '폐업 시뮬레이션', icon: Building2 },
  { href: '/accessibility', label: '2SFCA 접근성', icon: Activity },
  { href: '/methodology', label: '데이터 및 방법론', icon: BookOpen },
]

const BADGES = ['인구 2025년', '의료기관 2025.12', '행정구역 2025년', '탐색적 분석']

function isActive(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/'
  return pathname === href || pathname.startsWith(`${href}/`)
}

function Brand({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <Activity className="size-5" />
      </span>
      {!collapsed ? (
        <span className="leading-tight break-keep">
          <span className="block text-base font-bold tracking-tight text-foreground">
            메디리치
          </span>
          <span className="block text-[11px] font-medium tracking-wide text-muted-foreground">
            MediReach
          </span>
        </span>
      ) : null}
    </div>
  )
}

function NavLinks({
  collapsed = false,
  onNavigate,
}: {
  collapsed?: boolean
  onNavigate?: () => void
}) {
  const pathname = usePathname()
  return (
    <nav className="flex flex-col gap-1" aria-label="주요 메뉴">
      {NAV.map((item) => {
        const active = isActive(pathname, item.href)
        const Icon = item.icon
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? 'page' : undefined}
            aria-label={collapsed ? item.label : undefined}
            title={collapsed ? item.label : undefined}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors',
              collapsed && 'justify-center px-2',
              active
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground',
            )}
          >
            <Icon className="size-4 shrink-0" />
            {!collapsed ? <span className="break-keep">{item.label}</span> : null}
          </Link>
        )
      })}
    </nav>
  )
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = React.useState(false)
  const [desktopCollapsed, setDesktopCollapsed] = React.useState(false)

  return (
    <div className="min-h-screen bg-background lg:flex">
      {/* 데스크톱 사이드바 */}
      <aside
        className={cn(
          'hidden shrink-0 flex-col border-r border-border bg-card transition-[width] duration-200 lg:flex lg:h-screen lg:sticky lg:top-0',
          desktopCollapsed ? 'w-20' : 'w-64',
        )}
      >
        <div
          className={cn(
            'border-b border-border p-3',
            desktopCollapsed
              ? 'flex flex-col items-center gap-2'
              : 'flex items-center justify-between',
          )}
        >
          <Brand collapsed={desktopCollapsed} />
          <button
            type="button"
            aria-label={desktopCollapsed ? '사이드바 펼치기' : '사이드바 접기'}
            title={desktopCollapsed ? '사이드바 펼치기' : '사이드바 접기'}
            aria-expanded={!desktopCollapsed}
            onClick={() => setDesktopCollapsed((collapsed) => !collapsed)}
            className="flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            {desktopCollapsed ? (
              <PanelLeftOpen className="size-4" />
            ) : (
              <PanelLeftClose className="size-4" />
            )}
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          <NavLinks collapsed={desktopCollapsed} />
        </div>
        {!desktopCollapsed ? (
          <div className="border-t border-border p-4 text-xs leading-relaxed text-muted-foreground">
            의료가 닿지 않는 곳을 데이터로 찾다
            <br />
            전국 229개 시·군·자치구 분석
          </div>
        ) : null}
      </aside>

      {/* 모바일 상단바 */}
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-border bg-card px-4 py-3 lg:hidden">
        <Brand />
        <button
          type="button"
          aria-label="메뉴 열기"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen(true)}
          className="flex size-10 items-center justify-center rounded-md border border-border text-foreground"
        >
          <Menu className="size-5" />
        </button>
      </header>

      {/* 모바일 드로어 */}
      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="메뉴 닫기"
            className="absolute inset-0 bg-foreground/40"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute left-0 top-0 flex h-full w-72 max-w-[85%] flex-col bg-card shadow-xl">
            <div className="flex items-center justify-between border-b border-border p-4">
              <Brand />
              <button
                type="button"
                aria-label="메뉴 닫기"
                onClick={() => setMobileOpen(false)}
                className="flex size-9 items-center justify-center rounded-md border border-border text-foreground"
              >
                <X className="size-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-3">
              <NavLinks onNavigate={() => setMobileOpen(false)} />
            </div>
          </div>
        </div>
      ) : null}

      {/* 메인 */}
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8">
          <PageHeader />
          {children}
        </div>
      </div>
    </div>
  )
}

function PageHeader() {
  return (
    <header className="mb-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <h1 className="text-balance text-2xl font-bold tracking-tight text-foreground break-keep sm:text-3xl">
            메디리치
          </h1>
          <p className="mt-1.5 max-w-2xl text-pretty text-sm leading-relaxed text-muted-foreground break-keep">
            의료가 닿지 않는 곳을 데이터로 찾습니다. 전국 229개 시·군·자치구의
            의료 접근성과 병원 폐업 영향을 분석합니다.
          </p>
        </div>
        <ul className="flex flex-wrap gap-1.5 lg:justify-end">
          {BADGES.map((b) => (
            <li
              key={b}
              className="rounded-full border border-border bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground"
            >
              {b}
            </li>
          ))}
        </ul>
      </div>
      <div className="mt-4 flex items-start gap-2.5 rounded-md border border-border bg-accent/40 px-3.5 py-2.5 text-xs leading-relaxed text-accent-foreground">
        <Activity className="mt-0.5 size-4 shrink-0" aria-hidden />
        <p className="break-keep">
          본 대시보드는 2SFCA 기반 탐색적 분석 결과이며, 실제 의료·정책 판단용
          공식 지표가 아닙니다. 위험등급은 고령자 접근성과 의료공급에서 파생된 참고
          지표입니다.
        </p>
      </div>
    </header>
  )
}

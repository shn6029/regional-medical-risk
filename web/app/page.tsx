import { Activity } from 'lucide-react'
import { Dashboard } from '@/components/dashboard'

export default function Page() {
  return (
    <div className="min-h-dvh">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Activity className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-balance">
                지역별 의료 취약도 · 접근성 대시보드
              </h1>
              <p className="text-sm text-muted-foreground">
                전국 시·군·구 2SFCA 의료 접근성 분석
              </p>
            </div>
          </div>
          <div className="hidden items-center gap-1.5 rounded-full border bg-background px-3 py-1.5 text-xs text-muted-foreground sm:flex">
            <span className="h-2 w-2 rounded-full bg-[var(--risk-low)]" aria-hidden />
            FastAPI REST 연동
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <Dashboard />
      </main>

      <footer className="border-t">
        <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6">
          <p className="text-xs leading-relaxed text-muted-foreground text-pretty">
            본 대시보드는 2SFCA(2-Step Floating Catchment Area) 기반 접근성 분석을 시각화합니다.
            위험도 등급은 고령자 접근성 커버리지에서 파생된 참고 지표이며, 실제 의료·정책 판단용
            지표가 아닙니다.
          </p>
        </div>
      </footer>
    </div>
  )
}

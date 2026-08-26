import { AlertTriangle, Inbox, ServerCrash } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api'

export function ErrorState({
  error,
  onRetry,
}: {
  error: unknown
  onRetry?: () => void
}) {
  const isApiError = error instanceof ApiError
  const status = isApiError ? error.status : undefined
  const message =
    error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.'

  const isNotFound = status === 404
  const Icon = isNotFound ? Inbox : ServerCrash

  return (
    <Alert variant="destructive" className="flex flex-col gap-3">
      <Icon className="h-5 w-5" />
      <div>
        <AlertTitle>
          {isNotFound ? '표시할 분석 결과가 없습니다' : 'API 요청에 실패했습니다'}
        </AlertTitle>
        <AlertDescription>
          <p>{message}</p>
          {status === 0 && (
            <p className="mt-1 text-xs text-muted-foreground">
              {'NEXT_PUBLIC_API_BASE_URL'} 값과 FastAPI 서버 상태를 확인해 주세요.
            </p>
          )}
        </AlertDescription>
      </div>
      {onRetry && !isNotFound && (
        <Button variant="outline" size="sm" onClick={onRetry} className="w-fit">
          다시 시도
        </Button>
      )}
    </Alert>
  )
}

export function EmptyState({
  title = '데이터가 없습니다',
  description,
}: {
  title?: string
  description?: string
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed bg-card/50 px-6 py-14 text-center">
      <Inbox className="h-8 w-8 text-muted-foreground" />
      <p className="font-medium">{title}</p>
      {description && (
        <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      )}
    </div>
  )
}

export function InlineNotice({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>{children}</span>
    </div>
  )
}

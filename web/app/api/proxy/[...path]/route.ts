import { type NextRequest, NextResponse } from 'next/server'

// 항상 런타임에 요청을 전달 (캐시/정적화 방지)
export const dynamic = 'force-dynamic'

/**
 * 기존 FastAPI 서버로 요청을 대신 전달하는 서버 사이드 프록시.
 *
 * 브라우저는 같은 출처(this Next.js 앱)로만 요청하므로 CORS와
 * Mixed Content(http/https) 문제가 발생하지 않는다. 실제 업스트림
 * 주소는 서버에서만 읽는다.
 *   - API_BASE_URL (서버 전용, 우선) 또는
 *   - NEXT_PUBLIC_API_BASE_URL (클라이언트 공개용, 하위호환)
 */
function upstreamBase(): string {
  const raw = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? ''
  return raw.trim().replace(/\/$/, '')
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const base = upstreamBase()
  if (!base) {
    return NextResponse.json(
      { detail: 'API 서버 주소(NEXT_PUBLIC_API_BASE_URL)가 설정되지 않았습니다.' },
      { status: 500 },
    )
  }

  const { path } = await context.params
  const search = request.nextUrl.search
  const target = `${base}/${(path ?? []).join('/')}${search}`

  let upstream: Response
  try {
    upstream = await fetch(target, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    })
  } catch {
    return NextResponse.json(
      { detail: 'API 서버에 연결할 수 없습니다.' },
      { status: 502 },
    )
  }

  const body = await upstream.text()
  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      'Content-Type': upstream.headers.get('content-type') ?? 'application/json',
      'Cache-Control': 'no-store',
    },
  })
}

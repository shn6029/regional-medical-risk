import type { Metadata, Viewport } from 'next'
import { Noto_Sans_KR, Geist_Mono } from 'next/font/google'
import './globals.css'
import { SelectionProvider } from '@/components/selection-context'
import { AppShell } from '@/components/app-shell'

const notoSansKr = Noto_Sans_KR({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  variable: '--font-noto-sans-kr',
  display: 'swap',
})

const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: {
    default: '메디리치 | 지역 의료 접근성 분석',
    template: '%s | 메디리치',
  },
  description:
    '메디리치(MediReach)는 전국 229개 시·군·자치구의 의료 접근성과 병원 폐업 영향을 분석하는 공공 데이터 대시보드입니다.',
  applicationName: '메디리치',
}

export const viewport: Viewport = {
  themeColor: '#0d5c82',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko" className={`${notoSansKr.variable} ${geistMono.variable} bg-background`}>
      <body className="font-sans antialiased">
        <SelectionProvider>
          <AppShell>{children}</AppShell>
        </SelectionProvider>
      </body>
    </html>
  )
}

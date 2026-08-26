import { RISK_HEX, RISK_LABEL, RISK_ORDER } from '@/lib/risk'

/** 지도 위험등급 색상 범례. */
export function MapLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
      {RISK_ORDER.map((lvl) => (
        <span key={lvl} className="flex items-center gap-1.5">
          <span
            className="size-2.5 rounded-full"
            style={{ backgroundColor: RISK_HEX[lvl] }}
            aria-hidden
          />
          {RISK_LABEL[lvl]}
        </span>
      ))}
      <span className="text-muted-foreground/70">· 원이 클수록 인구가 많음</span>
    </div>
  )
}

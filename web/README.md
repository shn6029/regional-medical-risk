# 메디리치(MediReach) 웹 대시보드

기존 FastAPI 서버(`src/regional_medical_risk/api.py`)의 REST API를 소비하는
Next.js(App Router) + TypeScript + Tailwind CSS 프론트엔드입니다.
기존 Python Streamlit 앱, Supabase, `render.yaml`은 그대로 유지되며 이 디렉터리는
독립적인 새 프론트엔드입니다. 백엔드는 새로 만들지 않고 기존 API만 호출합니다.

## 환경 변수

`.env.local` 파일을 만들고 기존 FastAPI 서버 주소를 지정합니다.

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- 로컬에서 FastAPI를 함께 실행한다면 `http://localhost:8000`
- 배포된 서버라면 해당 도메인 (예: `https://<render-service>.onrender.com`)

## 실행

```bash
cd web
npm install
npm run dev      # http://localhost:3000
npm run build    # 프로덕션 빌드
```

## 소비하는 API 엔드포인트

| 엔드포인트 | 용도 |
| --- | --- |
| `GET /health` | 서버 상태 확인 |
| `GET /api/v1/accessibility/latest` | 최신 2SFCA 실행 요약(요약 지표 카드) |
| `GET /api/v1/accessibility/regions` | 지역별 2SFCA 점수 목록(지도·표·차트) |
| `GET /api/v1/accessibility/regions/{region_code}` | 지역 상세 + 수요점별 접근성 |

## 화면 구성

- **요약 지표 카드**: 분석 지역 수, 총 인구, 고령자 접근성 커버리지, 주의·위험 지역 수, 분석 경로 수
- **필터**: 지역명 검색, 시·도, 위험도
- **지도 탭**: Leaflet 기반 위험도 색상 마커 (커버리지에서 파생한 위험 등급)
- **지역 순위 탭**: 정렬 가능한 지역별 표
- **접근성 분석 탭**: 위험도 분포 / 고령자 접근성 하위 지역 차트 (Recharts)
- **지역 상세 패널**: 선택 지역의 수요점(행정동)별 의료기관·병상 접근성

## 상태 처리

- **로딩**: 스켈레톤 UI
- **빈 데이터**: 필터 결과 없음 / 데이터 없음 안내
- **API 오류**: 오류 메시지 + 재시도 버튼 (네트워크 실패, HTTP 오류, 환경변수 누락 구분)

> 위험도 등급은 백엔드에 별도 위험 점수 API가 없어 고령자 접근성 커버리지(임계시간 내 고령자 비율)에서
> 파생한 참고 지표입니다.

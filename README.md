# 전국 의료 인프라 취약도 예측 및 폐업 시뮬레이션

포트폴리오 발표용 8단계 설명과 목표 서비스 아키텍처는
[`PORTFOLIO_GUIDE.md`](PORTFOLIO_GUIDE.md), 실제 구현 진행률은
[`PROJECT_STATUS.md`](PROJECT_STATUS.md)를 참고하세요.

Supabase 초기 PostGIS 테이블과 적용 방법은 [`supabase/README.md`](supabase/README.md)를
참고하세요.

인구가 줄고 고령화되는 지역에서 **병원 수만으로는 드러나지 않는 의료 접근성 위험**을
찾고, 특정 병원이 사라질 때 취약도가 얼마나 변하는지 탐색하는 개인 프로젝트입니다.

> 주민등록인구·HIRA·SGIS 공공데이터를 사용한 탐색적 지표입니다. 취약도 점수와
> 폐업 시나리오는 실제 의료·정책 판단에 사용할 수 없습니다.

## 핵심 질문

1. 인구구조가 빠르게 바뀌는 지역의 병원급 공급과 접근성은 충분한가?
2. 최근 추세와 머신러닝 모델 중 고령인구를 더 잘 예측하는 방법은 무엇인가?
3. 특정 병원이 폐업하면 접근거리와 취약도, 영향 인구는 어떻게 달라지는가?

## 데이터와 정합 기준

| 자료 | 기준 | 분석에 사용한 항목 |
|---|---|---|
| 행정안전부 주민등록 인구통계 | 2014~2025년 연말 | 총인구, 65세 이상, 19~34세 인구 |
| 건강보험심사평가원 전국 병의원 및 약국 현황 | 2025년 12월 | 기관 ID, 종별, 좌표, 병상 |
| SGIS 행정구역 통계 및 경계 | 2025년 2분기 경계·2024년 인구 | 시군구 polygon, 행정동 인구와 중심점 |

출처: [행정안전부 주민등록 인구통계](https://jumin.mois.go.kr/),
[건강보험심사평가원 전국 병의원 및 약국 현황](https://www.data.go.kr/data/15051059/fileData.do),
[SGIS 행정구역 통계 및 경계](https://www.data.go.kr/data/15129688/fileData.do)

- 전국 **229개 시·군·자치구**를 현재 기준으로 통일했습니다. 도(道)의 일반시는 하위 구를
  시 단위로 합산하고, 군위군 편입과 미추홀구 개명은 현재 코드로 연결했습니다.
- HIRA 좌표 보유 기관 79,425개 중 병원·종합병원·요양병원·정신병원·보건의료원
  3,405개를 공급·접근성·폐업 분석 대상으로 사용했습니다.
- SGIS 행정동 3,559개의 중심점에서 행정구역 경계를 넘는 전국 최근접 병원까지의
  직선거리를 계산하고 인구로
  가중했습니다. SGIS 비밀보호 결측은 0으로 처리한 뒤 시군별 주민등록인구 합계에 맞게
  재조정했습니다.

## 구현 기능

- **전국 개요:** 인구, 5년 인구 변화, 고령화율, 병원급 기관 수, 취약도와 구성 요인
- **전국 지도:** 전국 229개 지역 polygon에 취약도·고령화율·접근거리 표시
- **지역 상세:** 전국 어느 지역이든 Kakao 지도에서 병원급 기관과 행정동 수요점 확인
- **미래 예측:** 작년 값 유지·선형추세 기준선과 Linear Regression, Random Forest,
  XGBoost 비교 및 4년 예측
- **What-if:** 병원 제거 전후의 공급, 인구가중 접근거리, 취약도, 영향 인구 비교

## 모델 결과

2025년을 시간 홀드아웃으로 둔 65세 이상 인구 예측 결과입니다.

| Model | MAE (명) |
|---|---:|
| Linear Trend Baseline | 315 |
| Linear Regression | 340 |
| Random Forest | 670 |
| XGBoost | 771 |
| Naive Baseline (Last Value) | 2,551 |

Linear Regression은 가장 강한 단순 기준선인 선형추세 외삽보다 MAE가 7.9% 높아
예측 성능 개선으로 볼 수 없습니다. 단일 연도 홀드아웃의 소규모 패널 결과이므로 일반화
성능으로 해석하지 않습니다.

## 취약도 정의

취약도는 설명 가능한 고정 경계값의 가중합으로 0~100점 범위에서 산출합니다.

| 요인 | 가중치 | 고정 경계 | 위험이 커지는 방향 |
|---|---:|---:|---|
| 고령화율 | 25% | 20~45% | 높을수록 |
| 5년 인구변화율 | 20% | -20~5% | 감소가 클수록 |
| 인구 1,000명당 병원급 기관 | 25% | 0.04~0.20개 | 적을수록 |
| 인구가중 병원 접근거리 | 30% | 1~10km | 멀수록 |

경계값과 가중치는 MVP의 분석 가정입니다. 데이터셋 내부 min-max가 아니라 고정 기준을
사용해 폐업 전후 점수를 같은 척도로 비교하지만, 실제 적용 전에는 전문가 검토와 민감도
분석이 필요합니다.

## 실행

Python 3.10 이상이 필요합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
streamlit run app\streamlit_app.py
```

테스트는 `python -m pytest -q`로 실행합니다.

## 2SFCA 조회 API

Supabase에 저장된 최신 완료 2SFCA 실행을 읽는 FastAPI 서버입니다. `.env`의
`DATABASE_URL`은 서버에서만 사용하며 브라우저 코드에 넣지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn regional_medical_risk.api:app `
  --host 127.0.0.1 --port 8000
```

실행 후 API 문서는 `http://127.0.0.1:8000/docs`에서 확인할 수 있습니다.

- `GET /health`: 서버 상태
- `GET /api/v1/accessibility/latest`: 최신 전국 2SFCA 요약
- `GET /api/v1/accessibility/regions`: 229개 지역 결과
- `GET /api/v1/accessibility/regions/{region_code}`: 지역 및 행정동 상세

Render 배포 설정은 루트의 `render.yaml`에 준비되어 있습니다. GitHub에 푸시한 뒤
Render Dashboard에서 `New > Blueprint`로 저장소를 선택하고, 화면에 표시되는
`DATABASE_URL`에 Supabase Session pooler 연결 문자열을 입력합니다. Python은
`.python-version`에 따라 3.12 최신 패치 버전을 사용합니다. Blueprint는 FastAPI와
Streamlit을 각각 별도 Web Service로 만들고, Streamlit의 `API_BASE_URL`은 FastAPI의
Render URL을 자동으로 참조합니다.

```text
Region: Singapore
Plan: Free
API Health Check: /health
Web Health Check: /_stcore/health
```

원본 파일에서 처리 데이터를 다시 생성하려면 다음 명령을 사용합니다.

```powershell
python -m regional_medical_risk.etl `
  --population-dir "<전국 주민등록인구 CSV 12개 폴더>" `
  --hira-zip "<전국 병의원 및 약국 현황 2025.12.zip>" `
  --sgis-zip "<SGIS 행정구역 통계 및 경계 ZIP>" `
  --output-dir "data\processed\national"
```

Docker를 사용할 경우:

```powershell
docker build -t regional-medical-risk .
docker run --rm -p 8501:8501 regional-medical-risk
```

## 실제 폐업 검증과 Kakao 지도

2023년 말 HIRA 스냅샷에 존재하고 2024년 말 스냅샷에서 사라진 병원급 기관을
누적 폐업 신고자료와 기관명·종별·시군구로 교차 검증합니다.

```powershell
python -m regional_medical_risk.validation `
  --closures "<요양기관 폐업 현황 CSV>" `
  --baseline-zip "<전국 병의원 및 약국 현황 2023.12.zip>" `
  --comparison-zip "<전국 병의원 및 약국 현황 2024.12.zip>" `
  --data-dir "data\processed\national" `
  --output "data\processed\national\closure_validation.csv"

python -m regional_medical_risk.validation `
  --closures "<요양기관 폐업 현황 CSV>" `
  --baseline-zip "<전국 병의원 및 약국 현황 2024.12.zip>" `
  --comparison-zip "<전국 병의원 및 약국 현황 2025.12.zip>" `
  --baseline-date "2024-12-31" `
  --comparison-date "2025-12-31" `
  --data-dir "data\processed\national" `
  --output "data\processed\national\closure_validation.csv" `
  --append
```

전국 2023→2024 구간 127건과 2024→2025 구간 110건, 총 237건을 정확 매칭했습니다.
±0.1km를 변화 없음으로 볼 때 예측과 관측의 접근성 변화 방향 일치율은 92.4%였고,
관측 접근거리 증가 사례는 16건이었습니다. 기관명·종별·지역 기반의 보수적 매칭이므로
인과 효과나 일반적인 예측 성능으로 해석하지 않습니다.

전국 지역 상세를 Kakao 지도로 표시하려면 `.env`의 `KAKAO_JAVASCRIPT_KEY`에 Kakao
Developers의 JavaScript 키를 입력합니다. 키가 없으면 Plotly 지도로 자동 대체됩니다.
전국 자동차 경로를 수집하기 전까지 접근성 지표와 What-if는 전국 최근접 직선거리로
동일하게 계산합니다.

카카오 다중 목적지 길찾기로 하루 최대 1,000개 행정동에서 가까운 병원 30곳의 경로를
수집합니다. 같은 명령을 매일 다시 실행하면 `kakao_routes.csv`를 기준으로 중단 지점부터
이어집니다. 처음부터 실행하면 전국 3,559개 행정동을 4일에 수집할 수 있으며, 기존
최근접 5개 경로 997개 출발지는 2SFCA 분석을 위해 나머지 25개를 한 차례 보충합니다.

```powershell
python -m regional_medical_risk.routing `
  --data-dir "data\processed\national" `
  --candidate-count 30 `
  --daily-origin-limit 1000
```

전체 수집이 끝난 실행에서만 `medical_supply.csv`의 접근거리·자동차 이동시간을 갱신합니다.

## 프로젝트 구조

```text
regional-medical-risk/
├── app/streamlit_app.py
├── data/
│   ├── raw/README.md
│   └── processed/
│       └── national/          # 전국 229개 지역·직선거리·실제 폐업 237건
├── src/regional_medical_risk/
│   ├── etl.py                 # 원본 3종 수집물 정합·가공
│   ├── data.py                # 데이터 계약과 지역 스냅샷
│   ├── risk.py                # 설명 가능한 취약도 산식
│   ├── forecast.py            # baseline/ML 비교와 예측
│   ├── accessibility.py       # 30분 접근 가능 인구와 2SFCA 계산
│   ├── accessibility_pipeline.py # Supabase 2SFCA 배치 계산·저장
│   ├── api.py                 # 최신 2SFCA 읽기 전용 FastAPI
│   ├── optimization.py        # K개 신규 의료시설 입지 최적화·기준 배치 비교
│   ├── simulation.py          # 병원 폐업 What-if
│   ├── validation.py          # 실제 폐업 사례 검증
│   └── routing.py             # 카카오 자동차 경로 수집·캐시
├── tests/
├── Dockerfile
└── pyproject.toml
```

## 한계와 다음 개선

- 전국 접근성은 자동차 이동시간이 아닌 직선거리입니다.
- 행정동 내부의 실제 인구 분포 대신 도형 중심점을 사용합니다.
- 실제 폐업 검증은 기관명·종별·지역 기반 매칭이고 비교 기간의 신규 개설 등 다른 공급 변화도
  함께 반영되므로, 폐업의 인과 효과나 일반화된 예측 정확도로 해석할 수 없습니다.
- 다음 단계에서는 더 긴 기간의 폐업 사례, 지역 단위 교차검증, 취약도 가중치 민감도 분석을
  우선 추가합니다.

## 포트폴리오 한 줄

> 서로 다른 코드 체계의 주민등록인구·HIRA·SGIS 데이터를 전국 229개 시·군·자치구로
> 정합해 설명 가능한 의료 취약지수를 설계하고, 실제 폐업 237건 검증과 전국 지역 상세
> Kakao 지도를 결합한 What-if 대시보드를 구축했습니다.

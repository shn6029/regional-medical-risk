# Supabase 데이터베이스

## 현재 원격 적용 상태

Supabase 프로젝트 `wufcdjkrcolfjjyxahzv`의 `main` 데이터베이스에는
`20260818051531_initial_medical_schema` migration이 적용되어 있습니다. 같은 SQL을
Dashboard에서 다시 실행하지 않습니다.

## 새 Supabase 프로젝트에 첫 migration 적용

현재 PC에는 Supabase CLI와 `psql`이 설치되어 있지 않으므로 첫 적용은 Dashboard의
SQL Editor를 사용합니다.

1. Supabase 프로젝트 왼쪽 메뉴에서 `SQL Editor`(`>_`)를 선택합니다.
2. `New query`를 선택합니다.
3. `migrations/20260818051531_initial_medical_schema.sql` 전체를 붙여넣습니다.
4. 오른쪽 아래 `Run`을 한 번 누릅니다.
5. `Table Editor`에서 `regions`, `facilities`, `route_matrix` 등이 생성됐는지 확인합니다.

Migration이 PostGIS 확장까지 활성화하므로 Dashboard에서 따로 확장을 켤 필요는 없습니다.

## 생성되는 데이터 영역

- 기준 데이터: `regions`, `population_history`, `demand_points`
- 의료 공급: `facilities`, `facility_snapshots`, `facility_closures`
- 자동차 이동시간: `route_matrix`, `routing_jobs`
- 분석 결과: `accessibility_runs`, `demand_accessibility_scores`,
  `regional_accessibility_scores`, `population_predictions`
- 정책 시뮬레이션: `candidate_sites`, `candidate_routes`, `scenario_runs`
- 데이터 계보: `data_imports`

`route_matrix`의 기본키는 `(demand_id, facility_id)`입니다. 매일 카카오 수집 결과를
같은 키로 UPSERT하면 기존 데이터는 갱신되고 새로운 경로만 추가됩니다.

## 보안 기본값

모든 테이블에는 RLS가 활성화되어 있고 공개 정책은 만들지 않았습니다. 따라서
publishable key를 사용하는 브라우저는 테이블을 직접 읽거나 쓸 수 없습니다. 데이터
적재와 분석 조회는 FastAPI/ETL의 서버 전용 DB 연결 또는 Supabase secret key로 처리합니다.

## CLI 전환 시

Node.js가 준비된 환경에서는 별도 전역 설치 없이 다음 명령을 사용할 수 있습니다.

```powershell
npx supabase login
npx supabase link --project-ref <project-ref>
npx supabase db push
```

Secret key, DB 비밀번호, connection string은 migration이나 Git 저장소에 넣지 않습니다.

## 전국 CSV 적재

Supabase Dashboard 상단 `Connect`에서 Session pooler 연결 문자열을 복사해 `.env`의
`DATABASE_URL`에 입력합니다. 비밀번호를 포함한 연결 문자열은 채팅이나 Git에 올리지
않습니다.

먼저 파일 구조와 행 수만 검증합니다.

```powershell
.\.venv\Scripts\python.exe -m regional_medical_risk.supabase_loader --dry-run
```

검증이 끝나면 전체 데이터를 외래키 순서대로 적재합니다.

```powershell
.\.venv\Scripts\python.exe -m regional_medical_risk.supabase_loader
```

카카오 경로가 추가된 날에는 경로만 다시 UPSERT할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m regional_medical_risk.supabase_loader `
  --only route_matrix
```

적재기는 `COPY → 임시 테이블 → ON CONFLICT UPSERT`를 사용합니다. 데이터셋 하나가
실패하면 해당 데이터셋 트랜잭션만 롤백하고 `data_imports`에 실패 원인을 남깁니다.

## 2SFCA 접근성 계산

전국 데이터와 수요점별 경로 30개가 모두 적재됐는지 검증하고 결과만 미리 계산합니다.

```powershell
.\.venv\Scripts\python.exe -m regional_medical_risk.accessibility_pipeline --dry-run
```

검증 후 `accessibility_runs`에 실행 이력을 만들고 수요점·지역 결과를 저장합니다.

```powershell
.\.venv\Scripts\python.exe -m regional_medical_risk.accessibility_pipeline
```

계산은 DB 트랜잭션 밖에서 수행하며, 결과 저장만 하나의 짧은 트랜잭션으로 처리합니다.

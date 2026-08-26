-- 전국 의료 인프라 취약도 서비스 초기 스키마
-- Remote migration: 20260818051531_initial_medical_schema
-- Supabase SQL Editor 또는 `supabase db push`로 적용한다.

create schema if not exists extensions;
create extension if not exists postgis with schema extensions;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.regions (
  region_code text primary key check (region_code ~ '^[0-9]{5}$'),
  province_name text not null,
  region_name text not null,
  center_latitude double precision check (center_latitude between -90 and 90),
  center_longitude double precision check (center_longitude between -180 and 180),
  center extensions.geography(Point, 4326) generated always as (
    case
      when center_latitude is not null and center_longitude is not null
      then extensions.st_setsrid(
        extensions.st_makepoint(center_longitude, center_latitude), 4326
      )::extensions.geography
    end
  ) stored,
  boundary extensions.geometry(MultiPolygon, 4326),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (province_name, region_name)
);

create table public.population_history (
  region_code text not null references public.regions(region_code) on delete cascade,
  year smallint not null check (year between 2000 and 2100),
  population integer not null check (population >= 0),
  senior_population integer not null check (senior_population >= 0),
  youth_population integer not null check (youth_population >= 0),
  created_at timestamptz not null default now(),
  primary key (region_code, year),
  check (senior_population <= population),
  check (youth_population <= population)
);

create table public.demand_points (
  demand_id text primary key check (demand_id ~ '^[0-9]{8,10}$'),
  region_code text not null references public.regions(region_code) on delete cascade,
  demand_name text not null,
  population integer not null check (population >= 0),
  senior_population integer not null check (senior_population >= 0),
  latitude double precision not null check (latitude between -90 and 90),
  longitude double precision not null check (longitude between -180 and 180),
  location extensions.geography(Point, 4326) generated always as (
    extensions.st_setsrid(extensions.st_makepoint(longitude, latitude), 4326)::extensions.geography
  ) stored,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (senior_population <= population)
);

create table public.facilities (
  facility_id text primary key,
  region_code text not null references public.regions(region_code),
  facility_name text not null,
  facility_type text not null,
  address text,
  opened_on date,
  closed_on date,
  beds integer not null default 0 check (beds >= 0),
  latitude double precision not null check (latitude between -90 and 90),
  longitude double precision not null check (longitude between -180 and 180),
  location extensions.geography(Point, 4326) generated always as (
    extensions.st_setsrid(extensions.st_makepoint(longitude, latitude), 4326)::extensions.geography
  ) stored,
  is_analysis_target boolean not null default false,
  source_snapshot_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (closed_on is null or opened_on is null or closed_on >= opened_on)
);

create table public.facility_snapshots (
  facility_id text not null references public.facilities(facility_id) on delete cascade,
  snapshot_date date not null,
  region_code text not null references public.regions(region_code),
  facility_type text not null,
  beds integer not null default 0 check (beds >= 0),
  is_open boolean not null default true,
  created_at timestamptz not null default now(),
  primary key (facility_id, snapshot_date)
);

create table public.facility_closures (
  closure_id bigint generated always as identity primary key,
  facility_id text,
  facility_name text not null,
  facility_type text,
  region_code text not null references public.regions(region_code),
  closed_on date not null,
  baseline_date date,
  comparison_date date,
  predicted_distance_delta_km numeric(10, 3),
  observed_distance_delta_km numeric(10, 3),
  predicted_risk_delta numeric(10, 4),
  observed_risk_delta numeric(10, 4),
  predicted_direction text,
  observed_direction text,
  direction_agreement boolean,
  affected_population integer check (affected_population >= 0),
  affected_senior_population integer check (affected_senior_population >= 0),
  hospital_count_before integer check (hospital_count_before >= 0),
  hospital_count_observed integer check (hospital_count_observed >= 0),
  source_snapshot_date date,
  created_at timestamptz not null default now(),
  unique (facility_id, closed_on)
);

create table public.route_matrix (
  demand_id text not null references public.demand_points(demand_id) on delete cascade,
  facility_id text not null references public.facilities(facility_id) on delete cascade,
  straight_distance_km numeric(10, 3) not null check (straight_distance_km >= 0),
  route_distance_km numeric(10, 3) check (route_distance_km >= 0),
  route_duration_min numeric(10, 2) check (route_duration_min >= 0),
  route_status text not null,
  collected_at timestamptz not null,
  updated_at timestamptz not null default now(),
  primary key (demand_id, facility_id)
);

create table public.accessibility_runs (
  run_id uuid primary key default gen_random_uuid(),
  method text not null default '2SFCA',
  method_version text not null,
  catchment_minutes numeric(6, 2) not null check (catchment_minutes > 0),
  demand_column text not null default 'senior_population',
  supply_column text not null default 'beds',
  route_count integer not null check (route_count >= 0),
  parameters jsonb not null default '{}'::jsonb,
  status text not null default 'running' check (status in ('running', 'completed', 'failed')),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  error_message text
);

create table public.demand_accessibility_scores (
  run_id uuid not null references public.accessibility_runs(run_id) on delete cascade,
  demand_id text not null references public.demand_points(demand_id) on delete cascade,
  accessible_hospital_count integer not null check (accessible_hospital_count >= 0),
  accessible_beds integer not null check (accessible_beds >= 0),
  within_threshold boolean not null,
  two_sfca_score numeric(14, 6) not null check (two_sfca_score >= 0),
  primary key (run_id, demand_id)
);

create table public.regional_accessibility_scores (
  run_id uuid not null references public.accessibility_runs(run_id) on delete cascade,
  region_code text not null references public.regions(region_code) on delete cascade,
  population integer not null check (population >= 0),
  population_within_threshold integer not null check (population_within_threshold >= 0),
  population_within_threshold_pct numeric(5, 2) not null check (
    population_within_threshold_pct between 0 and 100
  ),
  senior_population integer not null check (senior_population >= 0),
  senior_within_threshold integer not null check (senior_within_threshold >= 0),
  senior_within_threshold_pct numeric(5, 2) not null check (
    senior_within_threshold_pct between 0 and 100
  ),
  two_sfca_score numeric(14, 6) not null check (two_sfca_score >= 0),
  primary key (run_id, region_code)
);

create table public.population_predictions (
  region_code text not null references public.regions(region_code) on delete cascade,
  target_year smallint not null check (target_year between 2000 and 2100),
  model_name text not null,
  trained_through_year smallint not null check (trained_through_year between 2000 and 2100),
  predicted_population integer not null check (predicted_population >= 0),
  predicted_senior_population integer check (predicted_senior_population >= 0),
  model_metrics jsonb not null default '{}'::jsonb,
  calculated_at timestamptz not null default now(),
  primary key (region_code, target_year, model_name, trained_through_year)
);

create table public.candidate_sites (
  candidate_id text primary key,
  region_code text not null references public.regions(region_code),
  candidate_name text not null,
  latitude double precision not null check (latitude between -90 and 90),
  longitude double precision not null check (longitude between -180 and 180),
  location extensions.geography(Point, 4326) generated always as (
    extensions.st_setsrid(extensions.st_makepoint(longitude, latitude), 4326)::extensions.geography
  ) stored,
  assumed_beds integer not null default 0 check (assumed_beds >= 0),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table public.candidate_routes (
  candidate_id text not null references public.candidate_sites(candidate_id) on delete cascade,
  demand_id text not null references public.demand_points(demand_id) on delete cascade,
  route_distance_km numeric(10, 3) check (route_distance_km >= 0),
  route_duration_min numeric(10, 2) check (route_duration_min >= 0),
  route_status text not null,
  collected_at timestamptz not null,
  primary key (candidate_id, demand_id)
);

create table public.scenario_runs (
  scenario_id uuid primary key default gen_random_uuid(),
  scenario_type text not null check (
    scenario_type in ('facility_closure', 'bed_reduction', 'new_facility', 'location_optimization')
  ),
  status text not null default 'queued' check (
    status in ('queued', 'running', 'completed', 'failed')
  ),
  request_payload jsonb not null,
  result_payload jsonb,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.routing_jobs (
  job_id uuid primary key default gen_random_uuid(),
  status text not null default 'queued' check (
    status in ('queued', 'running', 'quota_exhausted', 'completed', 'failed')
  ),
  candidate_count smallint not null default 30 check (candidate_count between 1 and 30),
  total_origins integer not null check (total_origins >= 0),
  completed_origins integer not null default 0 check (completed_origins >= 0),
  total_routes integer not null check (total_routes >= 0),
  completed_routes integer not null default 0 check (completed_routes >= 0),
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (completed_origins <= total_origins),
  check (completed_routes <= total_routes)
);

create table public.data_imports (
  import_id uuid primary key default gen_random_uuid(),
  dataset_name text not null,
  source_file text not null,
  source_snapshot_date date,
  file_sha256 text,
  row_count integer check (row_count >= 0),
  status text not null default 'running' check (status in ('running', 'completed', 'failed')),
  error_message text,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create index regions_boundary_gix on public.regions using gist (boundary);
create index regions_center_gix on public.regions using gist (center);
create index demand_points_location_gix on public.demand_points using gist (location);
create index demand_points_region_idx on public.demand_points (region_code);
create index facilities_location_gix on public.facilities using gist (location);
create index facilities_region_type_idx on public.facilities (region_code, facility_type);
create index facility_snapshots_date_idx on public.facility_snapshots (snapshot_date, region_code);
create index facility_snapshots_region_idx on public.facility_snapshots (region_code);
create index facility_closures_region_date_idx on public.facility_closures (region_code, closed_on);
create index route_matrix_demand_duration_idx on public.route_matrix (demand_id, route_duration_min);
create index route_matrix_facility_demand_idx on public.route_matrix (facility_id, demand_id);
create index demand_accessibility_scores_demand_idx
  on public.demand_accessibility_scores (demand_id, run_id);
create index regional_accessibility_region_idx on public.regional_accessibility_scores (region_code, run_id);
create index candidate_sites_region_idx on public.candidate_sites (region_code);
create index candidate_routes_demand_duration_idx on public.candidate_routes (demand_id, route_duration_min);
create index scenario_runs_type_created_idx on public.scenario_runs (scenario_type, created_at desc);
create index routing_jobs_created_idx on public.routing_jobs (created_at desc);

create trigger regions_set_updated_at
before update on public.regions
for each row execute function public.set_updated_at();

create trigger demand_points_set_updated_at
before update on public.demand_points
for each row execute function public.set_updated_at();

create trigger facilities_set_updated_at
before update on public.facilities
for each row execute function public.set_updated_at();

create trigger route_matrix_set_updated_at
before update on public.route_matrix
for each row execute function public.set_updated_at();

create trigger scenario_runs_set_updated_at
before update on public.scenario_runs
for each row execute function public.set_updated_at();

create trigger routing_jobs_set_updated_at
before update on public.routing_jobs
for each row execute function public.set_updated_at();

-- 모든 데이터 접근은 우선 FastAPI/ETL의 서버 전용 자격증명을 통하도록 한다.
-- RLS 정책을 만들기 전까지 publishable key를 통한 직접 조회·수정은 차단된다.
alter table public.regions enable row level security;
alter table public.population_history enable row level security;
alter table public.demand_points enable row level security;
alter table public.facilities enable row level security;
alter table public.facility_snapshots enable row level security;
alter table public.facility_closures enable row level security;
alter table public.route_matrix enable row level security;
alter table public.accessibility_runs enable row level security;
alter table public.demand_accessibility_scores enable row level security;
alter table public.regional_accessibility_scores enable row level security;
alter table public.population_predictions enable row level security;
alter table public.candidate_sites enable row level security;
alter table public.candidate_routes enable row level security;
alter table public.scenario_runs enable row level security;
alter table public.routing_jobs enable row level security;
alter table public.data_imports enable row level security;

comment on table public.route_matrix is '행정동 수요지와 병원 간 카카오 자동차 이동시간 캐시';
comment on table public.accessibility_runs is '2SFCA 산출 조건과 데이터 버전을 관리하는 실행 단위';
comment on table public.scenario_runs is '폐업·병상 감소·신규 시설·K개 입지 최적화 요청과 결과';

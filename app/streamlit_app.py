import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from regional_medical_risk.data import (
    build_latest_snapshot,
    load_demand_points,
    load_demo_data,
    load_route_matrix,
)
from regional_medical_risk.forecast import (
    LAST_VALUE_BASELINE,
    LINEAR_TREND_BASELINE,
    benchmark_models,
    forecast_population,
)
from regional_medical_risk.risk import score_regions
from regional_medical_risk.simulation import simulate_hospital_closure


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
NATIONAL_DIR = PROCESSED_DIR / "national"

st.set_page_config(page_title="전국 의료 취약도", page_icon="🏥", layout="wide")


def _env_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, separator, raw = line.partition("=")
            if separator and key.strip() == name:
                return raw.strip().strip("'\"")
    return ""


@st.cache_data
def load_bundle(data_dir: Path):
    population, supply, hospitals = load_demo_data(data_dir)
    demand = load_demand_points(data_dir)
    routes = load_route_matrix(data_dir)
    if routes is not None:
        covered = set(routes["demand_id"].astype(str))
        expected = set(demand["demand_id"].astype(str))
        if not expected.issubset(covered):
            routes = None
    snapshot = score_regions(build_latest_snapshot(population, supply))
    return population, hospitals, demand, snapshot, routes


@st.cache_data
def load_validation(data_dir: Path) -> pd.DataFrame:
    path = data_dir / "closure_validation.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


@st.cache_data
def load_geojson(data_dir: Path) -> dict | None:
    path = data_dir / "regions.geojson"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


@st.cache_data
def model_benchmarks(population: pd.DataFrame) -> pd.DataFrame:
    return benchmark_models(population)


def risk_components(region: pd.Series) -> pd.DataFrame:
    labels = {
        "aging_component": "고령화",
        "decline_component": "인구감소",
        "supply_component": "의료공급 부족",
        "access_component": "접근거리",
    }
    return pd.DataFrame(
        {"요인": labels.values(), "점수": [float(region[column]) * 100 for column in labels]}
    )


def region_label(regions: pd.DataFrame, code: int) -> str:
    region = regions.loc[regions["region_code"].eq(code)].iloc[0]
    return f"{region['province_name']} {region['region_name']}"


def region_metrics(region: pd.Series, driving: bool = False) -> None:
    cols = st.columns(5)
    cols[0].metric("인구", f"{region['population']:,.0f}명")
    cols[1].metric("5년 인구 변화", f"{region['population_change_5y_pct']:.1f}%")
    cols[2].metric("65세 이상", f"{region['aging_rate']:.1f}%")
    cols[3].metric("병원급 기관", f"{region['hospital_count']:,.0f}개")
    cols[4].metric("의료 취약도", f"{region['risk_score']:.1f}점", region["risk_level"])
    if driving and "access_duration_min" in region and pd.notna(region["access_duration_min"]):
        st.caption(
            f"인구가중 자동차 접근시간 {region['access_duration_min']:.1f}분 · "
            f"실제 Kakao 경로 비중 {region.get('route_exact_share_pct', 0):.1f}%"
        )


def kakao_detail_map(
    region: pd.Series, region_hospitals: pd.DataFrame, region_demand: pd.DataFrame
) -> bool:
    app_key = _env_value("KAKAO_JAVASCRIPT_KEY")
    if not app_key:
        return False
    hospital_data = region_hospitals[
        [
            "hospital_name",
            "hospital_type",
            "beds",
            "address",
            "opened_on",
            "latitude",
            "longitude",
        ]
    ].copy()
    hospital_data["beds"] = pd.to_numeric(hospital_data["beds"], errors="coerce").fillna(0).astype(int)
    hospital_data = hospital_data.fillna("")
    payload = {
        "center": [float(region["latitude"]), float(region["longitude"])],
        "hospitals": hospital_data.to_dict("records"),
        "demand": region_demand[["latitude", "longitude"]].astype(float).values.tolist(),
    }
    data = json.dumps(payload, ensure_ascii=True).replace("</", "<\\/")
    html = f"""
    <div id="map" style="width:100%;height:620px;border-radius:10px;background:#f8fafc;display:flex;align-items:center;justify-content:center;color:#475569">Kakao 지도를 불러오는 중입니다.</div>
    <script>
      const data = {data};
      function showKakaoError() {{
        document.getElementById('map').innerHTML = '<div style="padding:24px;text-align:center"><b>Kakao 지도를 불러오지 못했습니다.</b><br><small>카카오디벨로퍼스에서 Kakao Map API 활성화와 JavaScript SDK 도메인을 확인해 주세요.</small></div>';
      }}
      function initKakaoMap() {{
        if (!window.kakao || !kakao.maps) {{ showKakaoError(); return; }}
        kakao.maps.load(function() {{
        const regionCenter = new kakao.maps.LatLng(data.center[0], data.center[1]);
        const map = new kakao.maps.Map(document.getElementById('map'), {{
          center: regionCenter, level: 7
        }});
        window.detailMap = map;
        const bounds = new kakao.maps.LatLngBounds();
        let activeInfoWindow = null;
        function escapeHtml(value) {{
          return String(value ?? '').replace(/[&<>"']/g, character => ({{
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
          }})[character]);
        }}
        function hospitalInfoHtml(hospital) {{
          const beds = hospital.beds > 0 ? hospital.beds.toLocaleString() + '개' : '정보 없음';
          return '<div style="width:270px;padding:15px 18px;font-family:Arial,sans-serif">' +
            '<strong style="display:block;margin-bottom:9px;color:#0f172a;font-size:15px">' + escapeHtml(hospital.hospital_name) + '</strong>' +
            '<div style="font-size:12px;line-height:1.65;color:#334155">' +
            '<b>종별</b> · ' + escapeHtml(hospital.hospital_type || '정보 없음') + '<br>' +
            '<b>병상</b> · ' + escapeHtml(beds) + '<br>' +
            '<b>주소</b> · ' + escapeHtml(hospital.address || '정보 없음') + '<br>' +
            '<b>개설일</b> · ' + escapeHtml(hospital.opened_on || '정보 없음') +
            '</div></div>';
        }}
        data.demand.forEach(p => {{
          const pos = new kakao.maps.LatLng(p[0], p[1]); bounds.extend(pos);
          new kakao.maps.CustomOverlay({{map, position: pos,
            content: '<div style="width:7px;height:7px;border-radius:50%;background:#2563eb;opacity:.55"></div>'}});
        }});
        const hospitalMarkerSvg = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(
          '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20">' +
          '<circle cx="10" cy="10" r="8" fill="#dc2626" stroke="white" stroke-width="3"/>' +
          '</svg>'
        );
        const hospitalMarkerImage = new kakao.maps.MarkerImage(
          hospitalMarkerSvg,
          new kakao.maps.Size(20, 20),
          {{offset: new kakao.maps.Point(10, 10)}}
        );
        data.hospitals.forEach(hospital => {{
          const pos = new kakao.maps.LatLng(hospital.latitude, hospital.longitude); bounds.extend(pos);
          const marker = new kakao.maps.Marker({{
            map, position: pos, image: hospitalMarkerImage, title: hospital.hospital_name
          }});
          kakao.maps.event.addListener(marker, 'click', function() {{
            if (activeInfoWindow) activeInfoWindow.close();
            activeInfoWindow = new kakao.maps.InfoWindow({{
              content: hospitalInfoHtml(hospital), removable: true
            }});
            activeInfoWindow.open(map, marker);
          }});
        }});
        if (!bounds.isEmpty()) map.setBounds(bounds, 35, 35, 35, 35);
        map.setCenter(regionCenter);
        const appliedCenter = map.getCenter();
        document.getElementById('map').dataset.centerLatitude = appliedCenter.getLat();
        document.getElementById('map').dataset.centerLongitude = appliedCenter.getLng();
        }});
      }}
    </script>
    <script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={app_key}&autoload=false" onload="initKakaoMap()" onerror="showKakaoError()"></script>
    """
    st.iframe(html, height=640)
    return True


national = load_bundle(NATIONAL_DIR)
(
    national_population,
    national_hospitals,
    national_demand,
    national_snapshot,
    national_routes,
) = national
national_validation = load_validation(NATIONAL_DIR)

st.title("전국 의료 인프라 취약도")
st.caption(
    "전국 229개 시·군·자치구의 의료 접근성·인구구조·폐업 시나리오 통합 분석 · "
    "실제 의료·정책 판단용 지표가 아닙니다."
)

tab_overview, tab_map, tab_detail, tab_forecast, tab_simulation = st.tabs(
    ["① 전국 개요", "② 전국 지도", "③ 지역 상세", "④ 미래 예측", "⑤ What-if"]
)

with tab_overview:
    total_population = national_snapshot["population"].sum()
    total_seniors = national_snapshot["senior_population"].sum()
    cols = st.columns(5)
    cols[0].metric("분석 지역", f"{len(national_snapshot)}개")
    cols[1].metric("총인구", f"{total_population:,.0f}명")
    cols[2].metric("65세 이상", f"{total_seniors / total_population * 100:.1f}%")
    cols[3].metric("병원급 기관", f"{national_snapshot['hospital_count'].sum():,.0f}개")
    cols[4].metric("주의·위험 지역", f"{national_snapshot['risk_level'].isin(['주의', '위험']).sum()}개")

    province_options = ["전국", *sorted(national_snapshot["province_name"].unique())]
    selected_province = st.selectbox("시·도", province_options, key="overview_province")
    overview_regions = national_snapshot
    if selected_province != "전국":
        overview_regions = overview_regions[overview_regions["province_name"].eq(selected_province)]
    selected_code = st.selectbox(
        "시·군·구",
        overview_regions["region_code"],
        format_func=lambda code: region_label(overview_regions, code),
        key="overview_region",
    )
    selected_region = overview_regions[overview_regions["region_code"].eq(selected_code)].iloc[0]
    region_metrics(selected_region)
    left, right = st.columns([1, 1])
    with left:
        st.plotly_chart(
            px.bar(
                risk_components(selected_region),
                x="점수",
                y="요인",
                orientation="h",
                range_x=[0, 100],
                color="점수",
                color_continuous_scale=["#16a34a", "#facc15", "#dc2626"],
            ),
            width="stretch",
        )
    with right:
        st.subheader("취약도 상위 지역")
        st.dataframe(
            overview_regions.nlargest(10, "risk_score")[
                ["province_name", "region_name", "risk_score", "aging_rate", "access_distance_km"]
            ].rename(
                columns={
                    "province_name": "시·도",
                    "region_name": "지역",
                    "risk_score": "취약도",
                    "aging_rate": "고령화율(%)",
                    "access_distance_km": "접근거리(km)",
                }
            ),
            hide_index=True,
        )

with tab_map:
    geojson = load_geojson(NATIONAL_DIR)
    map_province = st.selectbox(
        "지도 시·도", ["전국", *sorted(national_snapshot["province_name"].unique())]
    )
    metric_labels = {
        "의료 취약도": "risk_score",
        "고령화율": "aging_rate",
        "병원 접근거리": "access_distance_km",
    }
    selected_metric_label = st.selectbox("색상 지표", metric_labels)
    selected_metric = metric_labels[selected_metric_label]
    map_data = national_snapshot.copy()
    if map_province != "전국":
        map_data = map_data[map_data["province_name"].eq(map_province)]
    map_data["region_code"] = map_data["region_code"].astype(str)
    for feature in geojson["features"]:
        feature["properties"]["region_code"] = str(feature["properties"]["region_code"])
    fig = px.choropleth_map(
        map_data,
        geojson=geojson,
        locations="region_code",
        featureidkey="properties.region_code",
        color=selected_metric,
        hover_name="region_name",
        hover_data={
            "province_name": True,
            "risk_score": ":.1f",
            "aging_rate": ":.1f",
            "access_distance_km": ":.1f",
            "region_code": False,
        },
        color_continuous_scale=["#16a34a", "#facc15", "#f97316", "#dc2626"],
        zoom=5.4 if map_province == "전국" else 7,
        center={"lat": float(map_data["latitude"].mean()), "lon": float(map_data["longitude"].mean())},
        map_style="carto-positron",
        opacity=0.75,
        height=680,
        labels={selected_metric: selected_metric_label},
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    st.plotly_chart(fig, width="stretch")
    st.caption("전국 비교는 행정동 중심점에서 전국 병원급 기관까지의 최근접 직선거리를 사용합니다.")

with tab_detail:
    detail_province = st.selectbox(
        "상세 시·도", sorted(national_snapshot["province_name"].unique()), key="detail_province"
    )
    detail_regions = national_snapshot[
        national_snapshot["province_name"].eq(detail_province)
    ]
    detail_code = st.selectbox(
        "상세 지역",
        detail_regions["region_code"],
        format_func=lambda code: region_label(detail_regions, code),
        key="detail_region",
    )
    detail_region = detail_regions[detail_regions["region_code"].eq(detail_code)].iloc[0]
    region_metrics(detail_region)
    detail_hospitals = national_hospitals[
        national_hospitals["region_code"].eq(detail_code)
        & national_hospitals["closure_candidate"]
    ]
    detail_demand = national_demand[national_demand["region_code"].eq(detail_code)]
    if kakao_detail_map(detail_region, detail_hospitals, detail_demand):
        st.caption("Kakao 지도 · 빨간 점은 병원급 기관, 파란 점은 행정동 수요 중심점입니다.")
    else:
        fallback = pd.concat(
            [
                detail_demand.assign(kind="행정동 수요점", size=5),
                detail_hospitals.assign(kind="병원급 기관", size=12),
            ],
            ignore_index=True,
        )
        fig = px.scatter_map(
            fallback,
            lat="latitude",
            lon="longitude",
            color="kind",
            size="size",
            hover_name="demand_name" if "demand_name" in fallback else None,
            zoom=8,
            center={"lat": detail_region["latitude"], "lon": detail_region["longitude"]},
            map_style="carto-positron",
            height=620,
        )
        st.plotly_chart(fig, width="stretch")
        st.info("`.env`에 `KAKAO_JAVASCRIPT_KEY`를 넣으면 이 자리에 Kakao 상세 지도가 표시됩니다.")

with tab_forecast:
    benchmarks = model_benchmarks(national_population)
    forecast_province = st.selectbox(
        "예측 시·도", sorted(national_snapshot["province_name"].unique()), key="forecast_province"
    )
    forecast_regions = national_snapshot[national_snapshot["province_name"].eq(forecast_province)]
    forecast_code = st.selectbox(
        "예측 지역",
        forecast_regions["region_code"],
        format_func=lambda code: region_label(forecast_regions, code),
    )
    model_name = st.selectbox("모델", benchmarks["model"].tolist(), index=0)
    benchmark_by_model = benchmarks.set_index("model")
    selected_benchmark = benchmark_by_model.loc[model_name]
    metric_columns = st.columns(4)
    metric_columns[0].metric("평가 연도", f"{int(selected_benchmark['test_year'])}년")
    metric_columns[1].metric(
        "작년 값 유지 MAE", f"{benchmark_by_model.loc[LAST_VALUE_BASELINE, 'mae']:,.0f}명"
    )
    metric_columns[2].metric(
        "선형 추세 기준선 MAE",
        f"{benchmark_by_model.loc[LINEAR_TREND_BASELINE, 'mae']:,.0f}명",
    )
    metric_columns[3].metric(
        "선택 모델 MAE",
        f"{selected_benchmark['mae']:,.0f}명",
        f"{selected_benchmark['vs_best_baseline_pct']:+.1f}% vs 최강 기준선",
    )
    st.caption(
        "MAE는 낮을수록 좋습니다. 개선율이 음수이면 선택 모델이 가장 강한 단순 기준선보다 "
        "성능이 나쁘다는 뜻입니다."
    )
    future = forecast_population(national_population, model_name=model_name)
    history = national_population[national_population["region_code"].eq(forecast_code)][
        ["region_code", "region_name", "year", "senior_population"]
    ].copy()
    history["kind"] = "실측"
    chart_data = pd.concat(
        [history, future[future["region_code"].eq(forecast_code)]], ignore_index=True
    )
    st.plotly_chart(
        px.line(
            chart_data,
            x="year",
            y="senior_population",
            color="kind",
            markers=True,
            labels={"year": "연도", "senior_population": "65세 이상 인구", "kind": "구분"},
        ),
        width="stretch",
    )
    st.dataframe(
        benchmarks.rename(
            columns={
                "model": "모델",
                "category": "구분",
                "mae": "홀드아웃 MAE(명)",
                "vs_best_baseline_pct": "최강 기준선 대비 개선율(%)",
                "test_year": "평가 연도",
            }
        ),
        hide_index=True,
        width="stretch",
    )

with tab_simulation:
    simulation_hospitals = national_hospitals[
        national_hospitals["closure_candidate"]
    ].copy()
    counts = simulation_hospitals.groupby("region_code").size()
    available_codes = counts[counts.ge(2)].index
    simulation_regions = national_snapshot[
        national_snapshot["region_code"].isin(available_codes)
    ]
    simulation_province = st.selectbox(
        "시뮬레이션 시·도",
        sorted(simulation_regions["province_name"].unique()),
        key="simulation_province",
    )
    simulation_regions = simulation_regions[
        simulation_regions["province_name"].eq(simulation_province)
    ]
    simulation_code = st.selectbox(
        "시뮬레이션 지역",
        simulation_regions["region_code"],
        format_func=lambda code: region_label(simulation_regions, code),
    )
    simulation_region = simulation_regions[
        simulation_regions["region_code"].eq(simulation_code)
    ].iloc[0]
    candidates = simulation_hospitals[
        simulation_hospitals["region_code"].eq(simulation_code)
    ]
    hospital_id = st.selectbox(
        "폐업 가정 의료기관",
        candidates["hospital_id"],
        format_func=lambda value: candidates.set_index("hospital_id").loc[value, "hospital_name"],
    )
    result = simulate_hospital_closure(
        simulation_region,
        simulation_hospitals,
        hospital_id,
        national_demand,
        national_routes,
    )
    st.warning(f"{result['hospital_name']}이 폐업한다고 가정한 탐색적 시나리오입니다.")
    cols = st.columns(5)
    cols[0].metric("병원급 기관", f"{result['hospital_count_after']}개", "-1개")
    cols[1].metric(
        "평균 접근거리",
        f"{result['access_distance_after']:.1f}km",
        f"{result['access_distance_after'] - result['access_distance_before']:+.1f}km",
        delta_color="inverse",
    )
    cols[2].metric(
        "의료 취약도",
        f"{result['risk_after']:.1f}점",
        f"{result['risk_after'] - result['risk_before']:+.1f}점",
        delta_color="inverse",
    )
    cols[3].metric("영향 인구", f"{result['affected_population']:,}명")
    cols[4].metric("영향 고령자", f"{result['affected_senior_population']:,}명")
    if result["access_duration_after"] is not None:
        st.metric(
            "평균 자동차 이동시간",
            f"{result['access_duration_after']:.1f}분",
            f"{result['access_duration_after'] - result['access_duration_before']:+.1f}분",
            delta_color="inverse",
        )
    if not national_validation.empty:
        st.subheader("실제 폐업 사례 검증")
        metrics = st.columns(3)
        metrics[0].metric("매칭된 실제 폐업", f"{len(national_validation)}건")
        metrics[1].metric(
            "방향 일치율", f"{national_validation['direction_agreement'].mean() * 100:.1f}%"
        )
        metrics[2].metric(
            "접근거리 증가 사례",
            f"{national_validation['observed_direction'].eq('increase').sum()}건",
        )
        st.dataframe(
            national_validation.nlargest(10, "observed_distance_delta_km")[
                [
                    "hospital_name",
                    "hospital_type",
                    "closed_on",
                    "predicted_distance_delta_km",
                    "observed_distance_delta_km",
                    "direction_agreement",
                ]
            ],
            hide_index=True,
        )

st.divider()
st.caption("취약도 = 고령화 25% + 인구감소 20% + 의료공급 부족 25% + 접근거리 30%")

from __future__ import annotations

import argparse
import re
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


PROVINCE_ALIASES = {
    "서울": "서울특별시",
    "서울특별시": "서울특별시",
    "부산": "부산광역시",
    "부산광역시": "부산광역시",
    "대구": "대구광역시",
    "대구광역시": "대구광역시",
    "인천": "인천광역시",
    "인천광역시": "인천광역시",
    "광주": "광주광역시",
    "광주광역시": "광주광역시",
    "대전": "대전광역시",
    "대전광역시": "대전광역시",
    "울산": "울산광역시",
    "울산광역시": "울산광역시",
    "세종": "세종특별자치시",
    "세종시": "세종특별자치시",
    "세종특별자치시": "세종특별자치시",
    "경기": "경기도",
    "경기도": "경기도",
    "강원": "강원특별자치도",
    "강원도": "강원특별자치도",
    "강원특별자치도": "강원특별자치도",
    "충북": "충청북도",
    "충청북도": "충청북도",
    "충남": "충청남도",
    "충청남도": "충청남도",
    "전북": "전북특별자치도",
    "전라북도": "전북특별자치도",
    "전북특별자치도": "전북특별자치도",
    "전남": "전라남도",
    "전라남도": "전라남도",
    "경북": "경상북도",
    "경상북도": "경상북도",
    "경남": "경상남도",
    "경상남도": "경상남도",
    "제주": "제주특별자치도",
    "제주도": "제주특별자치도",
    "제주특별자치도": "제주특별자치도",
}
SGIS_PROVINCES = {
    "11": "서울특별시",
    "21": "부산광역시",
    "22": "대구광역시",
    "23": "인천광역시",
    "24": "광주광역시",
    "25": "대전광역시",
    "26": "울산광역시",
    "29": "세종특별자치시",
    "31": "경기도",
    "32": "강원특별자치도",
    "33": "충청북도",
    "34": "충청남도",
    "35": "전북특별자치도",
    "36": "전라남도",
    "37": "경상북도",
    "38": "경상남도",
    "39": "제주특별자치도",
}
DO_PROVINCES = {
    "경기도",
    "강원특별자치도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
}
REGION_NAME_ALIASES = {
    ("인천광역시", "미추홀구"): "남구",
}
HOSPITAL_TYPES = {
    "상급종합",
    "종합병원",
    "병원",
    "요양병원",
    "정신병원",
    "보건의료원",
}


def _numbers(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def canonical_province(value: object) -> str:
    name = str(value).strip()
    return PROVINCE_ALIASES.get(name, name)


def _population_rows(path: Path, year: int) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="cp949", dtype=str)
    parsed = frame["행정구역"].str.extract(r"^\s*(.*?)\s*\((\d{10})\)\s*$")
    frame["full_name"] = parsed[0].str.strip()
    frame["source_code"] = parsed[1]
    frame = frame.dropna(subset=["full_name", "source_code"]).copy()
    tokens = frame["full_name"].str.split()
    frame["token_count"] = tokens.str.len()
    frame["province_name"] = tokens.str[0].map(canonical_province)
    frame["source_region_name"] = np.where(
        frame["token_count"].eq(1), frame["full_name"], tokens.str[1]
    )
    frame["year"] = year
    return frame


def _current_region_registry(frame: pd.DataFrame) -> pd.DataFrame:
    is_sejong = (
        frame["province_name"].eq("세종특별자치시")
        & frame["token_count"].eq(1)
        & ~frame["source_code"].str[2:].eq("00000000")
    )
    is_municipality = frame["token_count"].eq(2)
    registry = frame[(is_sejong | is_municipality) & ~frame["full_name"].str.endswith("출장소")].copy()
    registry["region_name"] = np.where(
        registry["province_name"].eq("세종특별자치시") & registry["token_count"].eq(1),
        "세종특별자치시",
        registry["source_region_name"],
    )
    registry["region_code"] = registry["source_code"].str[:5].astype(int)
    registry = registry[["region_code", "region_name", "province_name"]].drop_duplicates()
    duplicated = registry.duplicated("region_code", keep=False)
    if duplicated.any():
        raise ValueError(
            "최신 주민등록 자료의 시군구 코드가 중복됩니다: "
            f"{registry.loc[duplicated].to_dict('records')[:5]}"
        )
    return registry.sort_values("region_code").reset_index(drop=True)


def prepare_population(files: list[Path]) -> pd.DataFrame:
    selected: dict[int, Path] = {}
    for path in sorted(files, key=lambda item: (len(item.name), item.name)):
        columns = pd.read_csv(path, encoding="cp949", nrows=0).columns
        total = next((column for column in columns if column.endswith("년_계_총인구수")), None)
        if total:
            selected.setdefault(int(total[:4]), path)

    if not selected:
        raise ValueError("연도별 연령별인구현황 총계 CSV를 찾지 못했습니다.")

    latest_year = max(selected)
    registry = _current_region_registry(_population_rows(selected[latest_year], latest_year))

    rows = []
    for year, path in sorted(selected.items()):
        source = _population_rows(path, year)
        source = source[
            source["token_count"].eq(2)
            | (
                source["province_name"].eq("세종특별자치시")
                & source["token_count"].eq(1)
            )
        ].copy()
        keyed = {
            (row.province_name, row.source_region_name): row.Index
            for row in source.itertuples()
        }
        selected_indexes = []
        missing = []
        for region in registry.itertuples(index=False):
            key = (region.province_name, region.region_name)
            index = keyed.get(key)
            if index is None:
                alias = REGION_NAME_ALIASES.get(key)
                index = keyed.get((region.province_name, alias)) if alias else None
            if index is None and region.region_name == "군위군":
                candidates = source.index[source["source_region_name"].eq("군위군")]
                index = candidates[0] if len(candidates) == 1 else None
            if index is None:
                missing.append(f"{region.province_name} {region.region_name}")
            else:
                selected_indexes.append(index)
        if missing:
            raise ValueError(f"{year}년 현재 기준으로 정합되지 않은 시군구: {missing[:10]}")

        frame = source.loc[selected_indexes].reset_index(drop=True)
        frame[["region_code", "region_name", "province_name"]] = registry[
            ["region_code", "region_name", "province_name"]
        ]
        prefix = f"{year}년_계_"

        population = _numbers(frame[prefix + "총인구수"])
        senior = frame[[prefix + f"{age}세" for age in range(65, 100)] + [prefix + "100세 이상"]]
        youth = frame[[prefix + f"{age}세" for age in range(19, 35)]]
        age_total = frame[[prefix + f"{age}세" for age in range(100)] + [prefix + "100세 이상"]]
        if not np.allclose(age_total.apply(_numbers).sum(axis=1), population):
            raise ValueError(f"{path.name}: 연령별 합계가 총인구수와 일치하지 않습니다.")

        rows.append(
            pd.DataFrame(
                {
                    "region_code": frame["region_code"].astype(int),
                    "region_name": frame["region_name"],
                    "province_name": frame["province_name"],
                    "year": year,
                    "population": population.astype(int),
                    "senior_population": senior.apply(_numbers).sum(axis=1).astype(int),
                    "youth_population": youth.apply(_numbers).sum(axis=1).astype(int),
                }
            )
        )

    result = pd.concat(rows, ignore_index=True).sort_values(["region_code", "year"])
    counts = result.groupby("year")["region_code"].nunique()
    if not counts.eq(len(registry)).all():
        raise ValueError(f"연도별 시군구 수가 {len(registry)}개가 아닙니다: {counts.to_dict()}")
    return result


def _extract(zip_path: Path, destination: Path, suffixes: tuple[str, ...]) -> list[Path]:
    extracted = []
    with zipfile.ZipFile(zip_path) as archive:
        for item in archive.infolist():
            if item.filename.endswith(suffixes):
                target = destination / Path(item.filename).name
                target.write_bytes(archive.read(item))
                extracted.append(target)
    return extracted


def _name_key(value: object) -> str:
    return "".join(character for character in str(value) if character.isalnum())


def _region_maps(regions: pd.DataFrame) -> tuple[dict[tuple[str, str], int], dict[str, int]]:
    current = regions[["region_code", "region_name", "province_name"]].drop_duplicates()
    exact = {
        (canonical_province(row.province_name), _name_key(row.region_name)): int(row.region_code)
        for row in current.itertuples(index=False)
    }
    by_name: dict[str, list[int]] = {}
    for row in current.itertuples(index=False):
        by_name.setdefault(_name_key(row.region_name), []).append(int(row.region_code))
    unique = {name: codes[0] for name, codes in by_name.items() if len(set(codes)) == 1}
    return exact, unique


def _map_hira_regions(frame: pd.DataFrame, regions: pd.DataFrame) -> pd.Series:
    exact, unique = _region_maps(regions)
    current = regions[["region_code", "region_name", "province_name"]].drop_duplicates()
    city_candidates = [
        (
            canonical_province(row.province_name),
            _name_key(row.region_name[:-1]),
            int(row.region_code),
        )
        for row in current.itertuples(index=False)
        if str(row.region_name).endswith("시")
    ]

    mapped = []
    for row in frame[["시도코드명", "시군구코드명"]].itertuples(index=False, name=None):
        province = canonical_province(row[0])
        district = _name_key(row[1])
        code = exact.get((province, district))
        if code is None:
            prefixes = sorted(
                {
                    _name_key(alias)
                    for alias, canonical in PROVINCE_ALIASES.items()
                    if canonical == province and alias != province
                },
                key=len,
                reverse=True,
            )
            for prefix in prefixes:
                if district.startswith(prefix):
                    stripped = district[len(prefix) :]
                    stripped_code = exact.get((province, stripped))
                    if stripped_code is not None:
                        district = stripped
                        code = stripped_code
                        break
        if code is None and province == "세종특별자치시":
            candidates = current[current["province_name"].eq(province)]
            code = int(candidates.iloc[0]["region_code"]) if len(candidates) == 1 else None
        if code is None:
            city_matches = [
                candidate_code
                for candidate_province, prefix, candidate_code in city_candidates
                if candidate_province == province
                and district.startswith(prefix)
                and district.endswith("구")
            ]
            if len(set(city_matches)) == 1:
                code = city_matches[0]
        if code is None:
            code = unique.get(district)
        mapped.append(code)
    return pd.Series(mapped, index=frame.index, dtype="Int64")


def prepare_hospitals(zip_path: Path, regions: pd.DataFrame | None = None) -> pd.DataFrame:
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        with zipfile.ZipFile(zip_path) as archive:
            basis_item = next(item for item in archive.infolist() if Path(item.filename).name.startswith("1."))
            facility_item = next(item for item in archive.infolist() if "_01_" in item.filename)
            basis_path = temp_path / Path(basis_item.filename).name
            facility_path = temp_path / Path(facility_item.filename).name
            basis_path.write_bytes(archive.read(basis_item))
            facility_path.write_bytes(archive.read(facility_item))

        basis_columns = [
            "암호화요양기호",
            "요양기관명",
            "종별코드명",
            "시도코드명",
            "시군구코드명",
            "주소",
            "개설일자",
            "좌표(X)",
            "좌표(Y)",
        ]
        basis = pd.read_excel(basis_path, usecols=basis_columns)

        bed_columns = [
            "일반입원실상급병상수",
            "일반입원실일반병상수",
            "성인중환자병상수",
            "소아중환자병상수",
            "신생아중환자병상수",
            "정신과폐쇄상급병상수",
            "정신과폐쇄일반병상수",
            "정신과개방상급병상수",
            "정신과개방일반병상수",
            "격리병실병상수",
            "무균치료실병상수",
        ]
        facility_columns = pd.read_excel(facility_path, nrows=0).columns
        available_bed_columns = [column for column in bed_columns if column in facility_columns]
        if not available_bed_columns:
            raise ValueError(f"{zip_path.name}: 병상수 열을 찾을 수 없습니다.")
        facilities = pd.read_excel(
            facility_path, usecols=["암호화요양기호", *available_bed_columns]
        )
        facilities = facilities[facilities["암호화요양기호"].isin(basis["암호화요양기호"])]
        facilities["beds"] = (
            facilities[available_bed_columns].apply(_numbers).fillna(0).sum(axis=1)
        )
        facilities = facilities[["암호화요양기호", "beds"]]

    frame = basis.merge(facilities, on="암호화요양기호", how="left", validate="one_to_one")
    if regions is None:
        raise ValueError("전국 의료기관 정합에 사용할 현재 시군구 목록이 필요합니다.")
    current = regions[["region_code", "region_name", "province_name"]].drop_duplicates()
    frame["region_code"] = _map_hira_regions(frame, current)
    if frame["region_code"].isna().any():
        missing = (
            frame.loc[frame["region_code"].isna(), ["시도코드명", "시군구코드명"]]
            .drop_duplicates()
            .to_dict("records")
        )
        raise ValueError(f"매핑되지 않은 전국 시군구가 있습니다: {missing[:10]}")
    frame = frame.merge(current, on="region_code", how="left", validate="many_to_one")
    frame = frame.dropna(subset=["좌표(X)", "좌표(Y)"]).copy()
    if frame.empty:
        raise ValueError("전국 의료기관에 사용할 수 있는 좌표가 없습니다.")

    return pd.DataFrame(
        {
            "hospital_id": frame["암호화요양기호"],
            "hospital_name": frame["요양기관명"],
            "region_code": frame["region_code"].astype(int),
            "region_name": frame["region_name"],
            "province_name": frame["province_name"],
            "hospital_type": frame["종별코드명"],
            "address": frame["주소"],
            "opened_on": pd.to_datetime(frame["개설일자"]).dt.strftime("%Y-%m-%d"),
            "beds": frame["beds"].fillna(0).astype(int),
            "latitude": frame["좌표(Y)"].astype(float),
            "longitude": frame["좌표(X)"].astype(float),
            "closure_candidate": frame["종별코드명"].isin(HOSPITAL_TYPES),
        }
    ).sort_values(["region_code", "hospital_name"])


def prepare_spatial(zip_path: Path, population: pd.DataFrame) -> tuple[pd.DataFrame, gpd.GeoDataFrame]:
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        wanted = (
            "bnd_sigungu_00_2025_2Q.shp",
            "bnd_sigungu_00_2025_2Q.shx",
            "bnd_sigungu_00_2025_2Q.dbf",
            "bnd_sigungu_00_2025_2Q.prj",
            "bnd_sigungu_00_2025_2Q.cpg",
            "bnd_dong_00_2025_2Q.shp",
            "bnd_dong_00_2025_2Q.shx",
            "bnd_dong_00_2025_2Q.dbf",
            "bnd_dong_00_2025_2Q.prj",
            "bnd_dong_00_2025_2Q.cpg",
            "2025년기준_2024년_인구총괄(총인구).csv",
            "2025년기준_2024년_성연령별인구.csv",
        )
        paths = _extract(zip_path, temp_path, wanted)
        by_name = {path.name: path for path in paths}
        sigungu = gpd.read_file(by_name["bnd_sigungu_00_2025_2Q.shp"])
        dong = gpd.read_file(by_name["bnd_dong_00_2025_2Q.shp"])

        sigungu["province_name"] = sigungu["SIGUNGU_CD"].str[:2].map(SGIS_PROVINCES)
        sigungu["region_name"] = sigungu["SIGUNGU_NM"].str.strip()
        parent_city = (
            sigungu["province_name"].isin(DO_PROVINCES)
            & sigungu["region_name"].str.contains(" ")
            & sigungu["region_name"].str.split().str[0].str.endswith("시")
        )
        sigungu.loc[parent_city, "region_name"] = (
            sigungu.loc[parent_city, "region_name"].str.split().str[0]
        )
        current = (
            population.sort_values("year")
            .groupby("region_code", as_index=False)
            .tail(1)[["region_code", "region_name", "province_name"]]
        )
        exact, unique = _region_maps(current)
        sigungu["region_code"] = [
            exact.get((province, _name_key(region)), unique.get(_name_key(region)))
            for province, region in zip(sigungu["province_name"], sigungu["region_name"])
        ]
        sejong_code = current.loc[
            current["province_name"].eq("세종특별자치시"), "region_code"
        ]
        if len(sejong_code) == 1:
            sigungu.loc[
                sigungu["province_name"].eq("세종특별자치시"), "region_code"
            ] = int(sejong_code.iloc[0])
        if sigungu["region_code"].isna().any():
            missing = sigungu.loc[
                sigungu["region_code"].isna(),
                ["SIGUNGU_CD", "SIGUNGU_NM", "province_name"],
            ].to_dict("records")
            raise ValueError(f"SGIS 경계와 정합되지 않은 시군구가 있습니다: {missing[:10]}")
        sigungu["region_code"] = sigungu["region_code"].astype(int)
        sgis_to_region = sigungu.set_index("SIGUNGU_CD")["region_code"].to_dict()

        total = pd.read_csv(
            by_name["2025년기준_2024년_인구총괄(총인구).csv"],
            encoding="cp949",
            dtype={"행정구역코드": str},
        )
        total = total[
            total["통계항목"].eq("to_in_001") & total["행정구역코드"].str.len().eq(8)
        ][["행정구역코드", "통계값"]].rename(columns={"통계값": "population"})
        ages = pd.read_csv(
            by_name["2025년기준_2024년_성연령별인구.csv"],
            encoding="cp949",
            dtype={"행정구역코드": str},
        )
        senior_codes = {f"in_age_{number:03d}" for number in range(14, 22)}
        ages = ages[
            ages["통계항목"].isin(senior_codes) & ages["행정구역코드"].str.len().eq(8)
        ].copy()
        ages["통계값"] = pd.to_numeric(ages["통계값"], errors="coerce").fillna(0)
        senior = ages.groupby("행정구역코드", as_index=False)["통계값"].sum().rename(
            columns={"통계값": "senior_population"}
        )

        dong["region_code"] = dong["ADM_CD"].str[:5].map(sgis_to_region)
        dong = dong.dropna(subset=["region_code"]).copy()
        dong["region_code"] = dong["region_code"].astype(int)
        dong = dong.merge(total, left_on="ADM_CD", right_on="행정구역코드", validate="one_to_one")
        dong = dong.merge(senior, on="행정구역코드", how="left", validate="one_to_one")
        dong[["population", "senior_population"]] = dong[
            ["population", "senior_population"]
        ].apply(_numbers).fillna(0)

        current = population[population["year"].eq(2024)].set_index("region_code")
        for column in ["population", "senior_population"]:
            source_sum = dong.groupby("region_code")[column].transform("sum")
            target = dong["region_code"].map(current[column])
            dong[column] = np.where(source_sum > 0, dong[column] * target / source_sum, 0)

        centroids = dong.geometry.centroid.to_crs(4326)
        demand = pd.DataFrame(
            {
                "region_code": dong["region_code"].astype(int),
                "demand_id": dong["ADM_CD"],
                "demand_name": dong["ADM_NM"],
                "population": dong["population"].round().astype(int),
                "senior_population": dong["senior_population"].round().astype(int),
                "latitude": centroids.y,
                "longitude": centroids.x,
            }
        )

        regions = sigungu[
            ["region_code", "region_name", "province_name", "geometry"]
        ].dissolve(
            by=["region_code", "region_name", "province_name"], as_index=False
        )
        regions["geometry"] = regions.geometry.simplify(100, preserve_topology=True)
    return demand.sort_values(["region_code", "demand_id"]), regions


def _haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    value = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(
        (lon2 - lon1) / 2
    ) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(value))


def build_supply(
    hospitals: pd.DataFrame, demand: pd.DataFrame, regions: gpd.GeoDataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    region_centroids = regions.geometry.centroid.to_crs(4326)
    centroids = regions[["region_code"]].copy()
    centroids["latitude"] = region_centroids.y
    centroids["longitude"] = region_centroids.x
    hospitals = hospitals.merge(centroids, on="region_code", suffixes=("", "_region"))
    hospitals["distance_km"] = _haversine(
        hospitals["latitude_region"],
        hospitals["longitude_region"],
        hospitals["latitude"],
        hospitals["longitude"],
    ).round(2)
    hospitals = hospitals.drop(columns=["latitude_region", "longitude_region"])

    candidate_hospitals = hospitals[hospitals["closure_candidate"]].copy()
    if candidate_hospitals.empty:
        raise ValueError("접근성을 계산할 병원급 의료기관이 없습니다.")

    rows = []
    for region_code, points in demand.groupby("region_code"):
        regional_facilities = candidate_hospitals[
            candidate_hospitals["region_code"].eq(region_code)
        ]
        distances = _haversine(
            points["latitude"].to_numpy()[:, None],
            points["longitude"].to_numpy()[:, None],
            candidate_hospitals["latitude"].to_numpy()[None, :],
            candidate_hospitals["longitude"].to_numpy()[None, :],
        )
        weights = points["population"].to_numpy()
        centroid = centroids[centroids["region_code"].eq(region_code)].iloc[0]
        rows.append(
            {
                "region_code": int(region_code),
                "latitude": centroid["latitude"],
                "longitude": centroid["longitude"],
                "hospital_count": len(regional_facilities),
                "hospital_beds": int(regional_facilities["beds"].sum()),
                "access_distance_km": round(float(np.average(distances.min(axis=1), weights=weights)), 2),
                "access_method": "straight_line_national",
            }
        )
    return pd.DataFrame(rows).sort_values("region_code"), hospitals


def run(population_dir: Path, hira_zip: Path, sgis_zip: Path, output_dir: Path) -> None:
    population = prepare_population(list(population_dir.glob("*연령별인구현황_연간*.csv")))
    demand, regions = prepare_spatial(sgis_zip, population)
    current_regions = (
        population.sort_values("year")
        .groupby("region_code", as_index=False)
        .tail(1)[["region_code", "region_name", "province_name"]]
    )
    hospitals = prepare_hospitals(hira_zip, current_regions)
    supply, hospitals = build_supply(hospitals, demand, regions)

    output_dir.mkdir(parents=True, exist_ok=True)
    population.to_csv(output_dir / "historical_population.csv", index=False, encoding="utf-8")
    hospitals.to_csv(output_dir / "hospitals.csv", index=False, encoding="utf-8")
    demand.to_csv(output_dir / "demand_points.csv", index=False, encoding="utf-8")
    supply.to_csv(output_dir / "medical_supply.csv", index=False, encoding="utf-8")
    current_regions.sort_values("region_code").to_csv(
        output_dir / "region_lookup.csv", index=False, encoding="utf-8"
    )
    regions.to_crs(4326).to_file(output_dir / "regions.geojson", driver="GeoJSON")

    years = sorted(population["year"].unique())
    missing = sorted(set(range(min(years), max(years) + 1)).difference(years))
    print(f"인구: {len(population):,}행, {years[0]}~{years[-1]}년, 누락 연도={missing or '없음'}")
    print(f"의료기관: {len(hospitals):,}개, 폐업 시뮬레이션 후보={hospitals['closure_candidate'].sum():,}개")
    print(f"수요 지점: {len(demand):,}개, 행정구역: {len(regions):,}개")


def main() -> None:
    parser = argparse.ArgumentParser(description="전국 의료 취약도 실데이터 전처리")
    parser.add_argument("--population-dir", type=Path, required=True)
    parser.add_argument("--hira-zip", type=Path, required=True)
    parser.add_argument("--sgis-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    run(args.population_dir, args.hira_zip, args.sgis_zip, args.output_dir)


if __name__ == "__main__":
    main()

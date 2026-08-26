import pandas as pd

from regional_medical_risk.etl import _map_hira_regions


def test_hira_region_mapping_handles_prefixes_parent_cities_and_sejong():
    regions = pd.DataFrame(
        [
            {"region_code": 11140, "region_name": "중구", "province_name": "서울특별시"},
            {"region_code": 26230, "region_name": "부산진구", "province_name": "부산광역시"},
            {"region_code": 41110, "region_name": "수원시", "province_name": "경기도"},
            {
                "region_code": 36110,
                "region_name": "세종특별자치시",
                "province_name": "세종특별자치시",
            },
        ]
    )
    hira = pd.DataFrame(
        [
            {"시도코드명": "서울", "시군구코드명": "서울중구"},
            {"시도코드명": "부산", "시군구코드명": "부산진구"},
            {"시도코드명": "경기", "시군구코드명": "수원장안구"},
            {"시도코드명": "세종", "시군구코드명": "세종시"},
        ]
    )

    assert _map_hira_regions(hira, regions).tolist() == [11140, 26230, 41110, 36110]

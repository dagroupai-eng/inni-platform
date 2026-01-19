from __future__ import annotations

import streamlit as st

# 페이지 설정 (반드시 최상단에 있어야 함)
st.set_page_config(
    page_title="지도 분석",
    page_icon=None,
    layout="wide"
)

import pandas as pd
import requests
from typing import Optional, Dict, Any, List, Tuple
import sys
import os
import re
import glob
import fnmatch
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 상위 디렉토리를 path에 추가하여 모듈 import 가능하게 함
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from geo_data_loader import GeoDataLoader, validate_shapefile_data
    GEO_MODULE_AVAILABLE = True
except ImportError as e:
    GEO_MODULE_AVAILABLE = False
    # 여기서는 st.warning을 사용하지 않고 나중에 처리

# ========================================
# VWorld WMS/WFS API 설정
# ========================================
# Streamlit Cloud secrets 또는 환경 변수에서 API 키 가져오기
def get_vworld_api_key():
    """VWorld API 키를 가져옵니다. Streamlit secrets > 환경변수 > 기본값 순서로 확인"""
    # 1. Streamlit secrets에서 확인
    try:
        if hasattr(st, 'secrets') and 'VWORLD_API_KEY' in st.secrets:
            return st.secrets['VWORLD_API_KEY']
    except Exception:
        pass
    # 2. 환경 변수에서 확인
    env_key = os.getenv("VWORLD_API_KEY")
    if env_key:
        return env_key
    # 3. 기본값 반환 (로컬 개발용)
    return "B490761B-D863-3E97-BCA1-F2F60CEA02AE"

VWORLD_API_KEY = get_vworld_api_key()
VWORLD_WMS_URL = "https://api.vworld.kr/req/wms"
VWORLD_WFS_URL = "https://api.vworld.kr/req/wfs"

# 연속 지적도 레이어 설정
CADASTRAL_LAYERS = {
    'bonbun': {
        'layer': 'lp_pa_cbnd_bonbun',
        'style': 'lp_pa_cbnd_bonbun_line',
        'name': '본번',
        'description': '연속지적도 본번 레이어'
    },
    'bubun': {
        'layer': 'lp_pa_cbnd_bubun',
        'style': 'lp_pa_cbnd_bubun_line',
        'name': '부번',
        'description': '연속지적도 부번 레이어'
    }
}

# 지역지구 레이어 설정 (용도지역/지구 - 면 레이어)
ZONE_LAYERS = {
    # 용도지역
    'urban': {
        'layer': 'lt_c_uq111',
        'style': 'lt_c_uq111',
        'name': '도시지역',
        'category': '용도지역',
        'color': '#FF6B6B'
    },
    'management': {
        'layer': 'lt_c_uq112',
        'style': 'lt_c_uq112',
        'name': '관리지역',
        'category': '용도지역',
        'color': '#4ECDC4'
    },
    'agricultural': {
        'layer': 'lt_c_uq113',
        'style': 'lt_c_uq113',
        'name': '농림지역',
        'category': '용도지역',
        'color': '#95E085'
    },
    'natural': {
        'layer': 'lt_c_uq114',
        'style': 'lt_c_uq114',
        'name': '자연환경보전지역',
        'category': '용도지역',
        'color': '#45B7D1'
    },
    # 용도지구
    'landscape': {
        'layer': 'lt_c_uq121',
        'style': 'lt_c_uq121',
        'name': '경관지구',
        'category': '용도지구',
        'color': '#96CEB4'
    },
    'development_restrict': {
        'layer': 'lt_c_ud801',
        'style': 'lt_c_ud801',
        'name': '개발제한구역',
        'category': '용도지구',
        'color': '#D4A5A5'
    },
    # 도시계획시설
    'urban_road': {
        'layer': 'lt_c_upisuq151',
        'style': 'lt_c_upisuq151',
        'name': '도시계획(도로)',
        'category': '도시계획시설',
        'color': '#A8A8A8'
    },
    'urban_traffic': {
        'layer': 'lt_c_upisuq152',
        'style': 'lt_c_upisuq152',
        'name': '도시계획(교통시설)',
        'category': '도시계획시설',
        'color': '#FFB347'
    },
    'urban_space': {
        'layer': 'lt_c_upisuq153',
        'style': 'lt_c_upisuq153',
        'name': '도시계획(공간시설)',
        'category': '도시계획시설',
        'color': '#87CEEB'
    },
    'urban_culture': {
        'layer': 'lt_c_upisuq155',
        'style': 'lt_c_upisuq155',
        'name': '도시계획(공공문화체육시설)',
        'category': '도시계획시설',
        'color': '#DDA0DD'
    },
    'urban_disaster': {
        'layer': 'lt_c_upisuq156',
        'style': 'lt_c_upisuq156',
        'name': '도시계획(방재시설)',
        'category': '도시계획시설',
        'color': '#F0E68C'
    },
    'urban_environment': {
        'layer': 'lt_c_upisuq158',
        'style': 'lt_c_upisuq158',
        'name': '도시계획(환경기초시설)',
        'category': '도시계획시설',
        'color': '#98D8C8'
    },
    'district_unit': {
        'layer': 'lt_c_upisuq161',
        'style': 'lt_c_upisuq161',
        'name': '지구단위계획',
        'category': '도시계획시설',
        'color': '#F7DC6F'
    }
}

def get_wms_tile_url(layers: str, styles: str, crs: str = "EPSG:900913") -> str:
    """WMS 타일 URL 템플릿 생성 (Folium TileLayer용)"""
    # EPSG:900913(Web Mercator)를 사용하면 일반적인 BBOX 순서 사용 가능
    base_url = (
        f"{VWORLD_WMS_URL}?"
        f"SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0"
        f"&LAYERS={layers}&STYLES={styles}"
        f"&CRS={crs}&BBOX={{bbox-epsg-900913}}"
        f"&WIDTH=256&HEIGHT=256&FORMAT=image/png"
        f"&TRANSPARENT=true&KEY={VWORLD_API_KEY}"
    )
    return base_url

def get_feature_info(lat: float, lon: float, layers: str, styles: str,
                     bbox_size: float = 0.001) -> Optional[Dict[str, Any]]:
    """
    WMS GetFeatureInfo로 특정 위치의 지적 정보 조회

    Args:
        lat: 위도
        lon: 경도
        layers: 조회할 레이어 (쉼표로 구분)
        styles: 레이어 스타일 (쉼표로 구분)
        bbox_size: BBOX 크기 (도 단위)

    Returns:
        지적 정보 딕셔너리 또는 None
    """
    # EPSG:4326 사용 시 BBOX 순서: ymin,xmin,ymax,xmax
    ymin = lat - bbox_size / 2
    ymax = lat + bbox_size / 2
    xmin = lon - bbox_size / 2
    xmax = lon + bbox_size / 2

    # 클릭 위치를 픽셀 좌표로 변환 (256x256 이미지의 중앙)
    i = 128  # X 픽셀 좌표 (중앙)
    j = 128  # Y 픽셀 좌표 (중앙)

    params = {
        'SERVICE': 'WMS',
        'VERSION': '1.3.0',
        'REQUEST': 'GetFeatureInfo',
        'LAYERS': layers,
        'QUERY_LAYERS': layers,
        'STYLES': styles,
        'CRS': 'EPSG:4326',
        'BBOX': f'{ymin},{xmin},{ymax},{xmax}',  # EPSG:4326: ymin,xmin,ymax,xmax
        'WIDTH': '256',
        'HEIGHT': '256',
        'I': str(i),
        'J': str(j),
        'INFO_FORMAT': 'application/json',
        'FEATURE_COUNT': '10',
        'KEY': VWORLD_API_KEY
    }

    try:
        response = requests.get(VWORLD_WMS_URL, params=params, timeout=10)
        response.raise_for_status()

        # JSON 응답 파싱
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        st.error(f"GetFeatureInfo 요청 실패: {str(e)}")
        return None
    except Exception as e:
        # JSON 파싱 실패 시 텍스트 응답 반환
        try:
            return {'raw_response': response.text}
        except:
            return None

def get_wfs_features(bbox: Tuple[float, float, float, float],
                     typename: str = "lp_pa_cbnd_bonbun",
                     max_features: int = 100) -> Optional[Dict[str, Any]]:
    """
    WFS GetFeature로 특정 영역의 지적 데이터 조회

    Args:
        bbox: (minx, miny, maxx, maxy) - EPSG:4326 좌표
        typename: 조회할 레이어명
        max_features: 최대 피처 수

    Returns:
        GeoJSON 형식의 피처 데이터 또는 None
    """
    minx, miny, maxx, maxy = bbox

    params = {
        'SERVICE': 'WFS',
        'VERSION': '1.1.0',
        'REQUEST': 'GetFeature',
        'TYPENAME': typename,
        'BBOX': f'{miny},{minx},{maxy},{maxx}',  # EPSG:4326: ymin,xmin,ymax,xmax
        'OUTPUT': 'application/json',
        'MAXFEATURES': str(max_features),
        'SRSNAME': 'EPSG:4326',
        'KEY': VWORLD_API_KEY
    }

    try:
        response = requests.get(VWORLD_WFS_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"WFS 요청 실패: {str(e)}")
        return None
    except Exception as e:
        return None

def create_cadastral_map(center_lat: float = 37.5665, center_lon: float = 126.9780,
                         zoom: int = 17, show_bonbun: bool = True,
                         show_bubun: bool = True,
                         selected_zone_layers: List[str] = None):
    """
    연속 지적도 및 지역지구 WMS 레이어가 포함된 Folium 지도 생성

    Args:
        center_lat: 중심 위도
        center_lon: 중심 경도
        zoom: 줌 레벨
        show_bonbun: 본번 레이어 표시 여부
        show_bubun: 부번 레이어 표시 여부
        selected_zone_layers: 표시할 지역지구 레이어 키 목록

    Returns:
        Folium Map 객체
    """
    if selected_zone_layers is None:
        selected_zone_layers = []

    try:
        import folium
        from folium.raster_layers import WmsTileLayer

        # 기본 지도 생성
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom,
            tiles='cartodbpositron'
        )

        # VWorld 기본 배경 지도 추가 (선택적)
        folium.TileLayer(
            tiles=f'https://api.vworld.kr/req/wmts/1.0.0/{VWORLD_API_KEY}/Base/{{z}}/{{y}}/{{x}}.png',
            attr='VWorld',
            name='VWorld 기본지도',
            overlay=False,
            control=True
        ).add_to(m)

        # VWorld 위성 지도 추가 (선택적)
        folium.TileLayer(
            tiles=f'https://api.vworld.kr/req/wmts/1.0.0/{VWORLD_API_KEY}/Satellite/{{z}}/{{y}}/{{x}}.jpeg',
            attr='VWorld Satellite',
            name='VWorld 위성지도',
            overlay=False,
            control=True
        ).add_to(m)

        # 지역지구 WMS 레이어 추가 (면 레이어 - 먼저 추가하여 아래에 표시)
        for zone_key in selected_zone_layers:
            if zone_key in ZONE_LAYERS:
                zone_info = ZONE_LAYERS[zone_key]
                WmsTileLayer(
                    url=f"{VWORLD_WMS_URL}?KEY={VWORLD_API_KEY}",
                    layers=zone_info['layer'],
                    styles=zone_info['style'],
                    fmt='image/png',
                    transparent=True,
                    version='1.3.0',
                    name=f"{zone_info['name']} ({zone_info['category']})",
                    overlay=True,
                    control=True,
                    show=True,
                    attr=f"VWorld {zone_info['name']}"
                ).add_to(m)

        # 연속 지적도 WMS 레이어 추가 (선 레이어 - 나중에 추가하여 위에 표시)
        cadastral_layers = []
        cadastral_styles = []

        if show_bonbun:
            cadastral_layers.append(CADASTRAL_LAYERS['bonbun']['layer'])
            cadastral_styles.append(CADASTRAL_LAYERS['bonbun']['style'])

        if show_bubun:
            cadastral_layers.append(CADASTRAL_LAYERS['bubun']['layer'])
            cadastral_styles.append(CADASTRAL_LAYERS['bubun']['style'])

        if cadastral_layers:
            layers_str = ','.join(cadastral_layers)
            styles_str = ','.join(cadastral_styles)

            # WMS 레이어 추가
            WmsTileLayer(
                url=f"{VWORLD_WMS_URL}?KEY={VWORLD_API_KEY}",
                layers=layers_str,
                styles=styles_str,
                fmt='image/png',
                transparent=True,
                version='1.3.0',
                name='연속 지적도',
                overlay=True,
                control=True,
                show=True,
                attr='VWorld 연속지적도'
            ).add_to(m)

        # 레이어 컨트롤 추가
        folium.LayerControl().add_to(m)

        # 범례 추가 (선택된 지역지구 레이어가 있는 경우)
        if selected_zone_layers:
            legend_html = '''
            <div style="
                position: fixed;
                bottom: 50px;
                left: 50px;
                z-index: 1000;
                background-color: white;
                padding: 10px 15px;
                border-radius: 8px;
                border: 2px solid #ccc;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                font-family: 'Malgun Gothic', sans-serif;
                font-size: 12px;
                max-width: 200px;
            ">
                <div style="font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid #ddd; padding-bottom: 5px;">
                    지역지구 레이어
                </div>
            '''
            for zone_key in selected_zone_layers:
                if zone_key in ZONE_LAYERS:
                    zone_info = ZONE_LAYERS[zone_key]
                    color = zone_info.get('color', '#888888')
                    legend_html += f'''
                    <div style="margin: 4px 0; display: flex; align-items: center;">
                        <span style="
                            display: inline-block;
                            width: 16px;
                            height: 16px;
                            background-color: {color};
                            border: 1px solid #333;
                            margin-right: 8px;
                            opacity: 0.7;
                        "></span>
                        <span>{zone_info['name']}</span>
                    </div>
                    '''
            legend_html += '</div>'

            m.get_root().html.add_child(folium.Element(legend_html))

        return m

    except ImportError:
        st.error("folium 패키지가 설치되지 않았습니다. `pip install folium` 명령으로 설치하세요.")
        return None
    except Exception as e:
        st.error(f"지도 생성 중 오류 발생: {str(e)}")
        return None

def format_feature_info(feature_data: Dict[str, Any]) -> str:
    """GetFeatureInfo 결과를 보기 좋게 포맷팅"""
    if not feature_data:
        return "조회된 정보가 없습니다."

    # raw_response가 있는 경우
    if 'raw_response' in feature_data:
        return feature_data['raw_response']

    # GeoJSON FeatureCollection 형식인 경우
    if 'features' in feature_data:
        features = feature_data.get('features', [])
        if not features:
            return "해당 위치에 지적 정보가 없습니다."

        result_lines = []
        for idx, feature in enumerate(features):
            props = feature.get('properties', {})
            if props:
                result_lines.append(f"### 필지 {idx + 1}")
                for key, value in props.items():
                    if value is not None and value != '':
                        # 키 이름을 한글로 변환 (주요 필드)
                        key_name = {
                            # 연속 지적도 필드
                            'pnu': 'PNU (필지고유번호)',
                            'jibun': '지번',
                            'bonbun': '본번',
                            'bubun': '부번',
                            'addr': '주소',
                            'jimok': '지목',
                            'jimok_nm': '지목명',
                            'jiga': '공시지가',
                            'area': '면적(㎡)',
                            'owner_nm': '소유자',
                            'own_type': '소유구분',
                            'land_use': '토지이용',
                            'ld_cpsg_code': '법정동코드',
                            'ld_cpsg': '법정동명',
                            'regstr_se_code': '축척코드',
                            # 지역지구 필드
                            'usg_nm': '용도지역명',
                            'usg_cd': '용도지역코드',
                            'uq_nm': '용도지구명',
                            'uq_cd': '용도지구코드',
                            'gb_nm': '개발제한구역명',
                            'gb_cd': '개발제한구역코드',
                            'dstrct_nm': '지구명',
                            'dstrct_cd': '지구코드',
                            'sido_nm': '시도명',
                            'sgg_nm': '시군구명',
                            'emd_nm': '읍면동명',
                            'li_nm': '리명',
                            'prpos_area_nm': '용도지역명칭',
                            'prpos_area_cd': '용도지역코드',
                            'spfc_area_nm': '특정지역명',
                            'spfc_area_cd': '특정지역코드',
                            'facl_nm': '시설명',
                            'facl_cd': '시설코드',
                            'ar': '면적(㎡)',
                            'cty_nm': '도시명',
                            'signgu_nm': '시군구명',
                            'leg_emd_nm': '법정읍면동명'
                        }.get(key, key)
                        result_lines.append(f"- **{key_name}**: {value}")
                result_lines.append("")

        return '\n'.join(result_lines) if result_lines else "조회된 정보가 없습니다."

    # 기타 형식
    return str(feature_data)

# V-world 레이어 정의 (GIS 기반 지도작성 시 필요 요소)
VWORLD_LAYERS = {
    'land_ownership': {
        'name': '토지소유정보',
        'formats': ['CSV', 'SHP'],
        'file_patterns': ['*토지소유*', '*land*ownership*', '*소유정보*'],
        'category': '',
        'date': '2025-09-26'
    },
    'admin_boundary_sigungu': {
        'name': '행정경계(시군구)',
        'formats': ['SHP'],
        'file_patterns': ['*행정경계*시군구*', '*시군구*', '*sigungu*', '*SIGUNGU*'],
        'category': '국토관리 지역개발',
        'date': '2025-07-31'
    },
    'admin_boundary_sido': {
        'name': '행정경계(시도)',
        'formats': ['SHP'],
        'file_patterns': ['*행정경계*시도*', '*시도*', '*sido*', '*SIDO*'],
        'category': '국토관리 지역개발 > 경계',
        'date': '2025-07-31'
    },
    'admin_boundary_emd': {
        'name': '행정경계(읍면동)',
        'formats': ['SHP'],
        'file_patterns': ['*행정경계*읍면동*', '*읍면동*', '*emd*', '*EMD*'],
        'category': '국토관리 지역개발 > 경계',
        'date': '2025-07-31'
    },
    'building_integrated': {
        'name': 'GIS건물통합정보',
        'formats': ['SHP'],
        'file_patterns': ['*건물통합*', '*building*integrated*', '*건물*통합*'],
        'category': '국토관리 지역개발 > 건물·시설',
        'date': '2025-11-25'
    },
    'road_zoning': {
        'name': '(연속주제)_도로/용도구역',
        'formats': ['SHP'],
        'file_patterns': ['*도로*용도구역*', '*road*zoning*', '*연속주제*도로*'],
        'category': '국토관리 지역개발 > 용도지역지구',
        'date': '2025-11-15'
    },
    'stream_zoning': {
        'name': '(연속주제)_소하천/소하천구역',
        'formats': ['SHP'],
        'file_patterns': ['*소하천*', '*stream*', '*하천*구역*'],
        'category': '국토관리 지역개발 > 용도지역지구',
        'date': '2025-11-15'
    },
    'park_zoning': {
        'name': '(연속주제)_자연공원/용도지구',
        'formats': ['SHP'],
        'file_patterns': ['*자연공원*용도지구*', '*park*zoning*', '*연속주제*자연공원*'],
        'category': '국토관리 지역개발 > 용도지역지구',
        'date': '2025-11-15'
    },
    'cadastral_shape': {
        'name': '연속지적도형정보',
        'formats': ['SHP'],
        'file_patterns': ['*지적도형*', '*cadastral*', '*지적*도형*'],
        'category': '국토관리 지역개발 > 토지',
        'date': '2025-11-25'
    }
}

# 제목
st.title("지도 분석")
st.markdown("**프로젝트 위치 및 지리적 데이터 시각화**")

# 페이지 네비게이션 처리
# (st.switch_page는 사이드바에서 직접 호출하면 오류 발생 가능하므로 제거)

# 샘플 지리적 데이터 생성
@st.cache_data
def generate_geo_data():
    """샘플 지리적 데이터 생성"""
    
    # 서울 지역 좌표 및 프로젝트 데이터
    seoul_projects = [
        {'name': '강남구 주거단지', 'lat': 37.5172, 'lon': 127.0473, 'type': '주거', 'size': '대형', 'status': '완료', 
         'start_date': '2022-01-15', 'end_date': '2023-12-20', 'budget': 150000000000, 'area': 25000},
        {'name': '서초구 상업시설', 'lat': 37.4837, 'lon': 127.0324, 'type': '상업', 'size': '중형', 'status': '진행중',
         'start_date': '2023-03-01', 'end_date': '2024-08-30', 'budget': 80000000000, 'area': 12000},
        {'name': '송파구 교육시설', 'lat': 37.5145, 'lon': 127.1050, 'type': '교육', 'size': '대형', 'status': '계획',
         'start_date': '2024-06-01', 'end_date': '2025-12-31', 'budget': 200000000000, 'area': 30000},
        {'name': '마포구 문화시설', 'lat': 37.5663, 'lon': 126.9019, 'type': '문화', 'size': '소형', 'status': '완료',
         'start_date': '2021-09-01', 'end_date': '2022-11-15', 'budget': 45000000000, 'area': 8000},
        {'name': '영등포구 의료시설', 'lat': 37.5264, 'lon': 126.8962, 'type': '의료', 'size': '대형', 'status': '진행중',
         'start_date': '2023-01-10', 'end_date': '2024-10-15', 'budget': 180000000000, 'area': 22000},
        {'name': '종로구 역사시설', 'lat': 37.5735, 'lon': 126.9788, 'type': '문화', 'size': '중형', 'status': '완료',
         'start_date': '2020-05-01', 'end_date': '2021-12-20', 'budget': 60000000000, 'area': 15000},
        {'name': '중구 상업시설', 'lat': 37.5636, 'lon': 126.9970, 'type': '상업', 'size': '대형', 'status': '계획',
         'start_date': '2024-09-01', 'end_date': '2026-03-31', 'budget': 220000000000, 'area': 28000},
        {'name': '용산구 주거단지', 'lat': 37.5384, 'lon': 126.9654, 'type': '주거', 'size': '중형', 'status': '진행중',
         'start_date': '2023-07-01', 'end_date': '2024-12-31', 'budget': 120000000000, 'area': 18000},
    ]
    
    # 전국 주요 도시 데이터
    cities_data = [
        {'city': '서울', 'lat': 37.5665, 'lon': 126.9780, 'projects': 35, 'population': 9720846, 'gdp': 450000000000000},
        {'city': '부산', 'lat': 35.1796, 'lon': 129.0756, 'projects': 15, 'population': 3448737, 'gdp': 120000000000000},
        {'city': '대구', 'lat': 35.8714, 'lon': 128.6014, 'projects': 12, 'population': 2413076, 'gdp': 80000000000000},
        {'city': '인천', 'lat': 37.4563, 'lon': 126.7052, 'projects': 10, 'population': 2954318, 'gdp': 95000000000000},
        {'city': '광주', 'lat': 35.1595, 'lon': 126.8526, 'projects': 8, 'population': 1441970, 'gdp': 45000000000000},
        {'city': '대전', 'lat': 36.3504, 'lon': 127.3845, 'projects': 6, 'population': 1475220, 'gdp': 55000000000000},
        {'city': '울산', 'lat': 35.5384, 'lon': 129.3114, 'projects': 4, 'population': 1134940, 'gdp': 35000000000000},
    ]
    
    return seoul_projects, cities_data

# V-world 레이어 로더 함수
def find_vworld_file(layer_id: str, vworld_dir: str = "V-world") -> str:
    """
    V-world 폴더에서 레이어에 해당하는 파일을 찾습니다.
    
    Args:
        layer_id: VWORLD_LAYERS의 키
        vworld_dir: V-world 폴더 경로 (프로젝트 루트 기준)
    
    Returns:
        찾은 파일 경로 또는 None
    """
    if layer_id not in VWORLD_LAYERS:
        return None
    
    layer_info = VWORLD_LAYERS[layer_id]
    patterns = layer_info['file_patterns']
    
    # 프로젝트 루트 기준으로 V-world 폴더 경로 구성
    # 현재 파일: system/pages/3_🗺️_Mapping.py
    # 프로젝트 루트: system의 상위 디렉토리
    current_dir = os.path.dirname(os.path.abspath(__file__))  # system/pages
    parent_dir = os.path.dirname(current_dir)  # system
    project_root = os.path.dirname(parent_dir)  # 프로젝트 루트
    vworld_path = os.path.join(project_root, vworld_dir)
    
    if not os.path.exists(vworld_path):
        return None
    
    # 우선순위: 1) 레이어명과 일치하는 폴더 내 .shp, 2) 루트의 .shp, 3) ZIP 파일
    layer_name = layer_info['name']
    
    # 1. 레이어명과 일치하는 폴더 안의 .shp 파일 우선 검색 (가장 빠름)
    layer_folder = os.path.join(vworld_path, layer_name)
    if os.path.exists(layer_folder) and os.path.isdir(layer_folder):
        for file in os.listdir(layer_folder):
            if file.endswith(('.shp', '.SHP')):
                shp_path = os.path.join(layer_folder, file)
                # 관련 파일들이 모두 있는지 확인 (.dbf, .shx 필요)
                base_name = os.path.splitext(shp_path)[0]
                if os.path.exists(f"{base_name}.dbf") and os.path.exists(f"{base_name}.shx"):
                    return shp_path
    
    # 2. 루트 디렉토리의 .shp 파일 검색
    for file in os.listdir(vworld_path):
        if file.endswith(('.shp', '.SHP')):
            file_name_lower = file.lower()
            for pattern in patterns:
                if fnmatch.fnmatch(file_name_lower, pattern.lower()) or pattern.lower() in file_name_lower:
                    shp_path = os.path.join(vworld_path, file)
                    # 관련 파일 확인
                    base_name = os.path.splitext(shp_path)[0]
                    if os.path.exists(f"{base_name}.dbf") and os.path.exists(f"{base_name}.shx"):
                        return shp_path
    
    # 3. ZIP 파일 검색 (폴더 탐색은 최소화)
    matched_zips = []
    for file in os.listdir(vworld_path):
        if file.endswith(('.zip', '.ZIP')):
            file_name_lower = file.lower()
            for pattern in patterns:
                if fnmatch.fnmatch(file_name_lower, pattern.lower()) or pattern.lower() in file_name_lower:
                    matched_zips.append(os.path.join(vworld_path, file))
                    break
    
    # 4. 하위 폴더에서 ZIP 파일 검색 (필요시만)
    if not matched_zips:
        for root, dirs, files in os.walk(vworld_path):
            # 이미 레이어명 폴더는 확인했으므로 스킵
            if os.path.basename(root) == layer_name:
                continue
            for file in files:
                if file.endswith(('.zip', '.ZIP')):
                    file_name_lower = file.lower()
                    for pattern in patterns:
                        if fnmatch.fnmatch(file_name_lower, pattern.lower()) or pattern.lower() in file_name_lower:
                            matched_zips.append(os.path.join(root, file))
                            break
    
    if matched_zips:
        matched_zips.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return matched_zips[0]
    
    return None

def load_vworld_layer(layer_id: str, loader: GeoDataLoader = None) -> dict:
    """
    V-world 폴더에서 레이어를 로드합니다.
    
    Args:
        layer_id: VWORLD_LAYERS의 키
        loader: GeoDataLoader 인스턴스 (없으면 새로 생성)
    
    Returns:
        {'success': bool, 'gdf': GeoDataFrame or None, 'info': dict or None, 'error': str or None}
    """
    if not GEO_MODULE_AVAILABLE:
        return {
            'success': False,
            'error': 'GeoDataLoader 모듈을 사용할 수 없습니다.'
        }
    
    if layer_id not in VWORLD_LAYERS:
        return {
            'success': False,
            'error': f'알 수 없는 레이어 ID: {layer_id}'
        }
    
    if loader is None:
        loader = GeoDataLoader()
    
    layer_info = VWORLD_LAYERS[layer_id]
    
    # 파일 찾기
    file_path = find_vworld_file(layer_id)
    if not file_path:
        return {
            'success': False,
            'error': f"'{layer_info['name']}' 파일을 V-world 폴더에서 찾을 수 없습니다."
        }
    
    try:
        # 파일 형식에 따라 로드
        if file_path.endswith(('.zip', '.ZIP')):
            # ZIP 파일인 경우
            with open(file_path, 'rb') as f:
                zip_data = f.read()
            
            result = loader.load_shapefile_from_zip(zip_data, encoding='cp949')
            
            if result['success']:
                return {
                    'success': True,
                    'gdf': result['gdf'],
                    'info': {
                        **result,
                        'file_path': file_path,
                        'layer_id': layer_id,
                        'layer_name': layer_info['name'],
                        'category': layer_info['category'],
                        'date': layer_info['date']
                    }
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', '알 수 없는 오류')
                }
        
        elif file_path.endswith(('.shp', '.SHP')):
            # Shapefile 직접 로드
            import geopandas as gpd
            gdf = gpd.read_file(file_path, encoding='cp949')
            gdf_transformed = loader._transform_crs(gdf)
            
            return {
                'success': True,
                'gdf': gdf_transformed,
                'info': {
                    'crs': gdf_transformed.crs.to_string() if gdf_transformed.crs else None,
                    'feature_count': len(gdf_transformed),
                    'columns': gdf_transformed.columns.tolist(),
                    'bounds': gdf_transformed.total_bounds.tolist(),
                    'geometry_type': gdf_transformed.geometry.geom_type.value_counts().to_dict(),
                    'file_path': file_path,
                    'layer_id': layer_id,
                    'layer_name': layer_info['name'],
                    'category': layer_info['category'],
                    'date': layer_info['date']
                }
            }
        
        elif file_path.endswith(('.csv', '.CSV')):
            # CSV 파일 (토지소유정보)
            # CSV는 좌표 정보가 있어야 GeoDataFrame으로 변환 가능
            # 일단 DataFrame으로 로드하고, 좌표 컬럼이 있으면 변환
            df = pd.read_csv(file_path, encoding='cp949')
            
            # 좌표 컬럼 찾기 (경도, 위도 또는 X, Y)
            lon_col = None
            lat_col = None
            
            for col in df.columns:
                col_lower = col.lower()
                if any(keyword in col_lower for keyword in ['경도', 'lon', 'x', 'longitude']):
                    lon_col = col
                elif any(keyword in col_lower for keyword in ['위도', 'lat', 'y', 'latitude']):
                    lat_col = col
            
            if lon_col and lat_col:
                import geopandas as gpd
                from shapely.geometry import Point
                
                geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
                gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
                gdf_transformed = loader._transform_crs(gdf)
                
                return {
                    'success': True,
                    'gdf': gdf_transformed,
                    'info': {
                        'crs': gdf_transformed.crs.to_string() if gdf_transformed.crs else None,
                        'feature_count': len(gdf_transformed),
                        'columns': gdf_transformed.columns.tolist(),
                        'bounds': gdf_transformed.total_bounds.tolist(),
                        'geometry_type': gdf_transformed.geometry.geom_type.value_counts().to_dict(),
                        'file_path': file_path,
                        'layer_id': layer_id,
                        'layer_name': layer_info['name'],
                        'category': layer_info['category'],
                        'date': layer_info['date']
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'CSV 파일에 좌표 정보(경도/위도)를 찾을 수 없습니다.'
                }
        
        else:
            return {
                'success': False,
                'error': f'지원하지 않는 파일 형식: {os.path.splitext(file_path)[1]}'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'파일 로드 중 오류 발생: {str(e)}'
        }

# 데이터 로드
seoul_projects, cities_data = generate_geo_data()

# 탭 분리: 연속 지적도, Shapefile 업로드, 후보지 시각화
if GEO_MODULE_AVAILABLE:
    tab_cadastral, tab2, tab3 = st.tabs(["연속 지적도", "Shapefile 업로드", "입지 후보지 시각화"])
else:
    tab_cadastral = st.container()
    tab2 = None
    tab3 = None

# ========================================
# 연속 지적도 탭
# ========================================
with tab_cadastral:
    st.header("연속 지적도 조회")
    st.markdown("**VWorld WMS API를 사용하여 연속 지적도를 표시하고 지적 정보를 조회합니다.**")

    # Session state 초기화
    if 'cadastral_center_lat' not in st.session_state:
        st.session_state.cadastral_center_lat = 37.5665
    if 'cadastral_center_lon' not in st.session_state:
        st.session_state.cadastral_center_lon = 126.9780
    if 'cadastral_zoom' not in st.session_state:
        st.session_state.cadastral_zoom = 12  # 지역지구 레이어가 잘 보이는 줌 레벨
    if 'clicked_location' not in st.session_state:
        st.session_state.clicked_location = None
    if 'feature_info_result' not in st.session_state:
        st.session_state.feature_info_result = None

    # 설정 영역
    col_settings, col_map = st.columns([1, 3])

    with col_settings:
        st.subheader("지도 설정")

        # 위치 검색
        st.markdown("**위치 이동**")
        search_lat = st.number_input(
            "위도",
            value=st.session_state.cadastral_center_lat,
            format="%.6f",
            step=0.001,
            key="search_lat_input"
        )
        search_lon = st.number_input(
            "경도",
            value=st.session_state.cadastral_center_lon,
            format="%.6f",
            step=0.001,
            key="search_lon_input"
        )

        if st.button("위치로 이동", type="primary", use_container_width=True):
            st.session_state.cadastral_center_lat = search_lat
            st.session_state.cadastral_center_lon = search_lon
            st.rerun()

        # 줌 레벨 설정
        st.markdown("**줌 레벨**")
        zoom_level = st.slider(
            "줌 레벨",
            min_value=5,
            max_value=19,
            value=st.session_state.cadastral_zoom,
            help="5~10: 광역, 11~14: 지역지구, 15~19: 필지 상세"
        )
        if zoom_level != st.session_state.cadastral_zoom:
            st.session_state.cadastral_zoom = zoom_level
            st.rerun()

        st.caption(f"현재 줌: {st.session_state.cadastral_zoom} (지역지구는 11~14 권장)")

        # 주요 도시 바로가기
        st.markdown("**주요 도시**")
        city_locations = {
            "서울 (종로구)": (37.5735, 126.9788),
            "서울 (강남구)": (37.5172, 127.0473),
            "부산 (중구)": (35.1028, 129.0325),
            "대구 (중구)": (35.8682, 128.5939),
            "인천 (남동구)": (37.4488, 126.7017),
            "광주 (동구)": (35.1454, 126.9172),
            "대전 (서구)": (36.3551, 127.3837),
        }

        selected_city = st.selectbox("도시 선택", list(city_locations.keys()))
        if st.button("선택 도시로 이동", use_container_width=True):
            lat, lon = city_locations[selected_city]
            st.session_state.cadastral_center_lat = lat
            st.session_state.cadastral_center_lon = lon
            st.rerun()

        st.markdown("---")

        # 레이어 설정
        st.markdown("**연속 지적도 레이어**")
        show_bonbun = st.checkbox("본번 레이어", value=True, help="연속지적도 본번 표시")
        show_bubun = st.checkbox("부번 레이어", value=True, help="연속지적도 부번 표시")

        st.markdown("---")

        # 지역지구 레이어 설정
        st.markdown("**지역지구 레이어 (면)**")

        # 카테고리별로 레이어 그룹화
        zone_categories = {}
        for zone_key, zone_info in ZONE_LAYERS.items():
            category = zone_info['category']
            if category not in zone_categories:
                zone_categories[category] = []
            zone_categories[category].append((zone_key, zone_info))

        # Session state 초기화
        if 'selected_zone_layers' not in st.session_state:
            st.session_state.selected_zone_layers = []

        selected_zones = []

        for category, layers in zone_categories.items():
            with st.expander(f"{category}", expanded=False):
                for zone_key, zone_info in layers:
                    is_selected = st.checkbox(
                        zone_info['name'],
                        value=zone_key in st.session_state.selected_zone_layers,
                        key=f"zone_{zone_key}",
                        help=f"레이어: {zone_info['layer']}"
                    )
                    if is_selected:
                        selected_zones.append(zone_key)

        # 선택된 레이어 저장
        st.session_state.selected_zone_layers = selected_zones

        if selected_zones:
            st.caption(f"선택된 지역지구: {len(selected_zones)}개")

        st.markdown("---")

        # 지적 정보 조회 결과
        st.subheader("지적 정보 조회")

        if st.session_state.clicked_location:
            click_lat, click_lon = st.session_state.clicked_location
            st.info(f"**클릭 위치**\n위도: {click_lat:.6f}\n경도: {click_lon:.6f}")

            if st.button("이 위치의 지적 정보 조회", type="primary", use_container_width=True):
                with st.spinner("지적 정보 조회 중..."):
                    # 조회할 레이어 설정
                    query_layers = []
                    query_styles = []

                    # 연속 지적도 레이어
                    if show_bonbun:
                        query_layers.append(CADASTRAL_LAYERS['bonbun']['layer'])
                        query_styles.append(CADASTRAL_LAYERS['bonbun']['style'])
                    if show_bubun:
                        query_layers.append(CADASTRAL_LAYERS['bubun']['layer'])
                        query_styles.append(CADASTRAL_LAYERS['bubun']['style'])

                    # 지역지구 레이어 (최대 4개까지만 - VWorld API 제한)
                    remaining_slots = 4 - len(query_layers)
                    for zone_key in st.session_state.selected_zone_layers[:remaining_slots]:
                        if zone_key in ZONE_LAYERS:
                            zone_info = ZONE_LAYERS[zone_key]
                            query_layers.append(zone_info['layer'])
                            query_styles.append(zone_info['style'])

                    if query_layers:
                        result = get_feature_info(
                            click_lat, click_lon,
                            ','.join(query_layers),
                            ','.join(query_styles)
                        )
                        st.session_state.feature_info_result = result
                    else:
                        st.warning("조회할 레이어를 선택하세요.")
        else:
            st.info("지도를 클릭하여 위치를 선택하세요.")

        # 조회 결과 표시
        if st.session_state.feature_info_result:
            st.markdown("---")
            st.markdown("**조회 결과**")
            formatted_result = format_feature_info(st.session_state.feature_info_result)
            st.markdown(formatted_result)

    with col_map:
        st.subheader("연속 지적도 지도")

        try:
            import streamlit_folium as st_folium

            # 지도 생성
            cadastral_map = create_cadastral_map(
                center_lat=st.session_state.cadastral_center_lat,
                center_lon=st.session_state.cadastral_center_lon,
                zoom=st.session_state.cadastral_zoom,
                show_bonbun=show_bonbun,
                show_bubun=show_bubun,
                selected_zone_layers=st.session_state.selected_zone_layers
            )

            if cadastral_map:
                # 클릭된 위치가 있으면 마커 추가
                import folium
                if st.session_state.clicked_location:
                    click_lat, click_lon = st.session_state.clicked_location
                    folium.Marker(
                        location=[click_lat, click_lon],
                        popup=f"클릭 위치\n위도: {click_lat:.6f}\n경도: {click_lon:.6f}",
                        icon=folium.Icon(color='red', icon='info-sign')
                    ).add_to(cadastral_map)

                # Folium 지도 표시 (클릭 이벤트 활성화)
                map_output = st_folium.st_folium(
                    cadastral_map,
                    width=900,
                    height=600,
                    returned_objects=["last_clicked"]
                )

                # 클릭 이벤트 처리
                if map_output and map_output.get('last_clicked'):
                    clicked = map_output['last_clicked']
                    new_lat = clicked.get('lat')
                    new_lon = clicked.get('lng')

                    if new_lat and new_lon:
                        # 이전 클릭 위치와 다른 경우에만 업데이트
                        if st.session_state.clicked_location != (new_lat, new_lon):
                            st.session_state.clicked_location = (new_lat, new_lon)
                            st.session_state.feature_info_result = None  # 이전 결과 초기화
                            st.rerun()

                st.info("**사용 방법**: 지도를 클릭하면 해당 위치가 선택됩니다. 왼쪽 패널에서 '지적 정보 조회' 버튼을 클릭하여 선택한 위치의 지적 정보를 확인할 수 있습니다.")

            else:
                st.error("지도를 생성할 수 없습니다.")

        except ImportError:
            st.error("streamlit-folium 패키지가 설치되지 않았습니다.")
            st.code("pip install streamlit-folium folium", language="bash")

    # WFS 데이터 조회 섹션 (고급 기능)
    st.markdown("---")
    with st.expander("고급: WFS로 영역 내 지적 데이터 조회"):
        st.markdown("**특정 영역 내 모든 지적 데이터를 GeoJSON 형식으로 조회합니다.**")

        col_wfs1, col_wfs2 = st.columns(2)

        with col_wfs1:
            st.markdown("**영역 설정 (EPSG:4326)**")
            wfs_min_lat = st.number_input("최소 위도 (ymin)", value=37.565, format="%.6f", key="wfs_min_lat")
            wfs_min_lon = st.number_input("최소 경도 (xmin)", value=126.976, format="%.6f", key="wfs_min_lon")

        with col_wfs2:
            wfs_max_lat = st.number_input("최대 위도 (ymax)", value=37.568, format="%.6f", key="wfs_max_lat")
            wfs_max_lon = st.number_input("최대 경도 (xmax)", value=126.980, format="%.6f", key="wfs_max_lon")

        wfs_layer = st.selectbox(
            "조회 레이어",
            ["lp_pa_cbnd_bonbun", "lp_pa_cbnd_bubun"],
            format_func=lambda x: "본번" if "bonbun" in x else "부번"
        )

        wfs_max_features = st.slider("최대 피처 수", min_value=10, max_value=1000, value=100, step=10)

        if st.button("WFS 데이터 조회", type="primary"):
            with st.spinner("WFS 데이터 조회 중..."):
                bbox = (wfs_min_lon, wfs_min_lat, wfs_max_lon, wfs_max_lat)
                wfs_result = get_wfs_features(bbox, wfs_layer, wfs_max_features)

                if wfs_result:
                    features = wfs_result.get('features', [])
                    st.success(f"총 {len(features)}개의 필지 데이터를 조회했습니다.")

                    if features:
                        # 데이터를 DataFrame으로 변환
                        records = []
                        for feature in features:
                            props = feature.get('properties', {})
                            records.append(props)

                        if records:
                            df_wfs = pd.DataFrame(records)
                            st.dataframe(df_wfs, use_container_width=True)

                            # JSON 다운로드 버튼
                            import json
                            json_str = json.dumps(wfs_result, ensure_ascii=False, indent=2)
                            st.download_button(
                                label="GeoJSON 다운로드",
                                data=json_str,
                                file_name="cadastral_data.geojson",
                                mime="application/json"
                            )
                else:
                    st.warning("조회된 데이터가 없습니다.")

    # API 정보 안내
    st.markdown("---")
    with st.expander("VWorld WMS/WFS API 정보"):
        st.markdown("""
        ### VWorld 연속 지적도 API

        **레이어 정보:**
        - `lp_pa_cbnd_bonbun`: 연속지적도 본번 레이어
        - `lp_pa_cbnd_bubun`: 연속지적도 부번 레이어

        **WMS GetMap 파라미터:**
        ```
        SERVICE=WMS
        REQUEST=GetMap
        VERSION=1.3.0
        LAYERS=lp_pa_cbnd_bonbun,lp_pa_cbnd_bubun
        STYLES=lp_pa_cbnd_bonbun_line,lp_pa_cbnd_bubun_line
        CRS=EPSG:4326
        BBOX=ymin,xmin,ymax,xmax (EPSG:4326 사용 시 순서 주의!)
        WIDTH=256
        HEIGHT=256
        FORMAT=image/png
        TRANSPARENT=true
        ```

        **WMS GetFeatureInfo 파라미터:**
        ```
        SERVICE=WMS
        REQUEST=GetFeatureInfo
        VERSION=1.3.0
        QUERY_LAYERS=lp_pa_cbnd_bonbun,lp_pa_cbnd_bubun
        I=픽셀X좌표 (0-WIDTH)
        J=픽셀Y좌표 (0-HEIGHT)
        INFO_FORMAT=application/json
        FEATURE_COUNT=10
        ```

        **참고 링크:**
        - [VWorld WMS 가이드](https://www.vworld.kr/dev/v4dv_wmsguide_s001.do)
        - [VWorld 개발자센터](https://www.vworld.kr/dev/v4api.do)
        """)

# Shapefile 업로드 탭
if tab2 is not None:
    with tab2:
        st.header("도시공간데이터 Shapefile 업로드")
        st.markdown("**행정구역, 토지소유정보, 개별공시지가, 도로명주소 등 Shapefile을 업로드하여 지도에서 확인하세요.**")
        
        # 개발중 UI 표시
        st.markdown("---")
        st.warning("🚧 **이 기능은 현재 개발 중입니다.**")
        
        # 아래 코드는 개발중이므로 주석 처리
        if False:  # 개발중 - 주석 처리된 코드
            # Session state 초기화
            if 'geo_layers' not in st.session_state:
                st.session_state.geo_layers = {}
            
            # V-world 레이어 상태 초기화
            if 'vworld_layers' not in st.session_state:
                st.session_state.vworld_layers = {}
            
            # 기존 단일 레이어 호환성 유지
            if 'uploaded_gdf' not in st.session_state:
                st.session_state.uploaded_gdf = None
            if 'uploaded_layer_info' not in st.session_state:
                st.session_state.uploaded_layer_info = None
            
            # 기존 레이어가 있으면 geo_layers로 마이그레이션
            if st.session_state.get('uploaded_gdf') is not None and len(st.session_state.geo_layers) == 0:
                st.session_state.geo_layers['기본 레이어'] = {
                    'gdf': st.session_state.uploaded_gdf,
                    'info': st.session_state.uploaded_layer_info
                }
            
            st.subheader("📤 Shapefile 업로드")
            
            # 여러 파일 동시 업로드 지원
            uploaded_files = st.file_uploader(
                "ZIP 파일로 압축된 Shapefile들을 업로드하세요 (여러 파일 선택 가능)",
                type=['zip'],
                accept_multiple_files=True,
                help="도시공간데이터포털에서 다운로드한 ZIP 파일들을 업로드하세요. 여러 파일을 한 번에 선택할 수 있습니다."
            )
            
            if uploaded_files:
                loader = GeoDataLoader()
                
                # 여러 파일 처리
                loaded_count = 0
                error_count = 0
                
                with st.spinner(f"{len(uploaded_files)}개 파일 처리 중..."):
                    for uploaded_file in uploaded_files:
                        # 파일명에서 레이어 이름 추출 (확장자 제거)
                        layer_name = uploaded_file.name.replace('.zip', '').replace('.ZIP', '')
                        
                        # 파일 로드
                        result = loader.load_shapefile_from_zip(
                            uploaded_file.getvalue(),
                            encoding='cp949'
                        )
                        
                        if result['success']:
                            # 데이터 검증
                            validation = validate_shapefile_data(result['gdf'])
                            
                            if validation['valid']:
                                # geo_layers 딕셔너리에 저장
                                st.session_state.geo_layers[layer_name] = {
                                    'gdf': result['gdf'],
                                    'info': result
                                }
                                loaded_count += 1
                            else:
                                error_count += 1
                                st.warning(f"⚠️ '{layer_name}' 검증 실패: {', '.join(validation['issues'])}")
                        else:
                            error_count += 1
                            st.error(f"❌ '{layer_name}' 로드 실패: {result.get('error', '알 수 없는 오류')}")
                
                # 결과 요약
                if loaded_count > 0:
                    st.success(f"✅ {loaded_count}개 레이어 로드 완료!")
                    if error_count > 0:
                        st.warning(f"⚠️ {error_count}개 파일 처리 실패")
                    st.rerun()
                elif error_count > 0:
                    st.error(f"❌ 모든 파일 처리 실패 ({error_count}개)")
        
        # 아래 코드는 개발중이므로 주석 처리
        if False:  # 개발중 - 주석 처리된 코드
            # 레이어 선택 체크박스
            selected_layers = []
            col1, col2, col3 = st.columns(3)
            
            layer_ids = list(VWORLD_LAYERS.keys())
            for idx, layer_id in enumerate(layer_ids):
                layer_info = VWORLD_LAYERS[layer_id]
                col = col1 if idx % 3 == 0 else col2 if idx % 3 == 1 else col3
                
                with col:
                    # 로드 상태 확인
                    is_loaded = layer_id in st.session_state.vworld_layers
                    status_icon = "✅" if is_loaded else "⏳"
                    
                    checkbox_key = f"vworld_checkbox_{layer_id}"
                    checked = st.checkbox(
                        f"{status_icon} {layer_info['name']}",
                        key=checkbox_key,
                        value=is_loaded
                    )
                    
                    if checked:
                        selected_layers.append(layer_id)
                    
                    # 레이어 정보 표시
                    if is_loaded:
                        layer_data = st.session_state.vworld_layers[layer_id]
                        st.caption(f"📊 {layer_data['info']['feature_count']:,}개 피처 | 📅 {layer_info['date']}")
                    else:
                        st.caption(f"📅 {layer_info['date']} | {', '.join(layer_info['formats'])}")
            
            # 선택한 레이어 로드 버튼
            if selected_layers:
                col_btn1, col_btn2 = st.columns([1, 4])
                with col_btn1:
                    if st.button("🔄 선택한 레이어 로드", type="primary", use_container_width=True):
                        loader = GeoDataLoader()
                        loaded_count = 0
                        error_count = 0
                        error_messages = []
                        
                        with st.spinner(f"{len(selected_layers)}개 레이어 로드 중..."):
                            for layer_id in selected_layers:
                                layer_info = VWORLD_LAYERS[layer_id]
                                
                                # 이미 로드된 레이어는 건너뛰기 (다시 로드하려면 먼저 삭제)
                                if layer_id in st.session_state.vworld_layers:
                                    continue
                                
                                result = load_vworld_layer(layer_id, loader)
                                
                                if result['success']:
                                    # 데이터 검증
                                    validation = validate_shapefile_data(result['gdf'])
                                    
                                    if validation['valid']:
                                        st.session_state.vworld_layers[layer_id] = {
                                            'gdf': result['gdf'],
                                            'info': result['info'],
                                            'loaded': True
                                        }
                                        loaded_count += 1
                                    else:
                                        error_count += 1
                                        error_msg = f"'{layer_info['name']}' 검증 실패: {', '.join(validation['issues'])}"
                                        error_messages.append(error_msg)
                                else:
                                    error_count += 1
                                    error_msg = f"'{layer_info['name']}' 로드 실패: {result.get('error', '알 수 없는 오류')}"
                                    error_messages.append(error_msg)
                        
                        # 결과 표시
                        if loaded_count > 0:
                            st.success(f"✅ {loaded_count}개 레이어 로드 완료!")
                            if error_count > 0:
                                for msg in error_messages:
                                    st.warning(f"⚠️ {msg}")
                            st.rerun()
                        elif error_count > 0:
                            for msg in error_messages:
                                st.error(f"❌ {msg}")
                
                with col_btn2:
                    # 로드된 레이어 삭제 버튼
                    loaded_layer_ids = [lid for lid in selected_layers if lid in st.session_state.vworld_layers]
                    if loaded_layer_ids:
                        if st.button("🗑️ 선택한 레이어 삭제", use_container_width=True):
                            for layer_id in loaded_layer_ids:
                                del st.session_state.vworld_layers[layer_id]
                            st.success("✅ 선택한 레이어가 삭제되었습니다.")
                            st.rerun()
            
            # V-world 레이어 목록 표시
            if st.session_state.vworld_layers:
                st.markdown("---")
                st.subheader("📚 로드된 V-world 레이어")
                
                for layer_id, layer_data in st.session_state.vworld_layers.items():
                    layer_info = VWORLD_LAYERS[layer_id]
                    with st.expander(f"📂 {layer_info['name']} ({layer_data['info'].get('layer_name', '')})"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**피처 수**: {layer_data['info']['feature_count']:,}개")
                            st.write(f"**좌표계**: {layer_data['info'].get('crs', 'Unknown')}")
                            st.write(f"**컬럼 수**: {len(layer_data['info']['columns'])}개")
                            if layer_info['category']:
                                st.write(f"**카테고리**: {layer_info['category']}")
                            st.write(f"**날짜**: {layer_info['date']}")
                            if 'file_path' in layer_data['info']:
                                st.caption(f"**파일**: {os.path.basename(layer_data['info']['file_path'])}")
                        with col2:
                            if st.button(f"삭제", key=f"del_vworld_{layer_id}"):
                                del st.session_state.vworld_layers[layer_id]
                                st.rerun()
            else:
                st.warning("⚠️ GeoDataLoader 모듈을 사용할 수 없어 V-world 레이어를 로드할 수 없습니다.")
            
            # 업로드된 레이어 목록 표시
            if st.session_state.geo_layers:
                st.markdown("---")
                st.subheader("📚 업로드된 레이어")
                
                for layer_name, layer_data in st.session_state.geo_layers.items():
                    with st.expander(f"📂 {layer_name}"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**피처 수**: {layer_data['info']['feature_count']:,}개")
                            st.write(f"**좌표계**: {layer_data['info'].get('crs', 'Unknown')}")
                            st.write(f"**컬럼 수**: {len(layer_data['info']['columns'])}개")
                        with col2:
                            if st.button(f"삭제", key=f"del_{layer_name}"):
                                del st.session_state.geo_layers[layer_name]
                                st.rerun()
            
            # 통합 지도 시각화 (업로드된 레이어 + V-world 레이어)
            all_layers = {}
            
            # 업로드된 레이어 추가
            all_layers.update(st.session_state.geo_layers)
            
            # V-world 레이어 추가 (접두사로 구분)
            for layer_id, layer_data in st.session_state.vworld_layers.items():
                layer_name = f"V-world: {VWORLD_LAYERS[layer_id]['name']}"
                all_layers[layer_name] = {
                    'gdf': layer_data['gdf'],
                    'info': layer_data['info']
                }
            
            if all_layers:
                st.markdown("---")
                st.subheader("🗺️ 통합 지도 시각화")
                
                # 지도 표시 방식 선택
                map_style = st.radio(
                    "지도 표시 방식",
                    ["고급 지도 (Polygon 경계 표시)", "간단 지도 (중심점만 표시)"],
                    horizontal=True
                )
                
                loader = GeoDataLoader()
                
                if map_style == "고급 지도 (Polygon 경계 표시)":
                    # Folium을 사용한 고급 지도
                    try:
                        import streamlit_folium as st_folium
                        
                        # 모든 레이어를 하나의 딕셔너리로 구성 (통합된 all_layers 사용)
                        geo_layers_dict = {
                            layer_name: layer_data['gdf'] 
                            for layer_name, layer_data in all_layers.items()
                        }
                        
                        # 대용량 레이어 경고 메시지
                        large_layers = []
                        for layer_name, layer_data in all_layers.items():
                            feature_count = layer_data['info'].get('feature_count', len(layer_data['gdf']))
                            if feature_count > 10000:
                                large_layers.append(f"{layer_name} ({feature_count:,}개 피처)")
                        
                        if large_layers:
                            st.warning(f"⚠️ 대용량 레이어 감지: {', '.join(large_layers)}\n지도 표시를 위해 일부 피처만 샘플링합니다. (최대 10,000개)")
                        
                        # 다중 레이어 Folium 지도 생성
                        with st.spinner("🗺️ 지도를 생성하는 중입니다... (대용량 데이터의 경우 시간이 걸릴 수 있습니다)"):
                            folium_map = loader.create_folium_map_multilayer(geo_layers_dict)
                        
                        if folium_map:
                            # Streamlit에 지도 표시
                            st_folium.st_folium(folium_map, width=1200, height=600)
                            st.info("💡 지도 위의 레이어 컨트롤을 사용하여 레이어를 켜고 끌 수 있습니다.")
                        else:
                            st.warning("⚠️ Folium 지도를 생성할 수 없습니다. 간단 지도를 사용하세요.")
                            map_style = "간단 지도 (중심점만 표시)"
                    
                    except ImportError:
                        st.warning("⚠️ streamlit-folium 패키지가 설치되지 않았습니다. 간단 지도를 사용합니다.")
                        st.info("💡 고급 지도를 사용하려면: `pip install streamlit-folium folium`")
                        map_style = "간단 지도 (중심점만 표시)"
            
            if map_style == "간단 지도 (중심점만 표시)":
                # 기존 방식: 중심점만 표시 (통합된 all_layers 사용)
                with st.spinner("🗺️ 지도를 생성하는 중입니다... (중심점 계산 중)"):
                    all_coords = []
                    MAX_POINTS_PER_LAYER = 1000  # 레이어당 최대 점 수
                    for layer_name, layer_data in all_layers.items():
                        gdf = layer_data['gdf']
                        feature_count = len(gdf)
                        
                        # 대용량 레이어는 샘플링
                        if feature_count > MAX_POINTS_PER_LAYER:
                            gdf = gdf.sample(n=MAX_POINTS_PER_LAYER, random_state=42)
                        
                        df_for_map = loader.gdf_to_dataframe_for_map(gdf)
                        if not df_for_map.empty:
                            df_for_map['layer'] = layer_name
                            all_coords.append(df_for_map)
                    
                if all_coords:
                    combined_df = pd.concat(all_coords, ignore_index=True)
                    st.map(combined_df, size=10)
                    st.info("💡 Polygon 경계를 보려면 '고급 지도' 옵션을 선택하세요.")
                else:
                    st.warning("⚠️ 지도에 표시할 수 있는 좌표 데이터가 없습니다.")
            
            # 원본 데이터 미리보기
            with st.expander("📋 원본 데이터 미리보기"):
                for layer_name, layer_data in list(all_layers.items())[:3]:  # 최대 3개 레이어만
                    st.markdown(f"**{layer_name}**")
                    gdf = layer_data['gdf']
                    feature_count = len(gdf)
                    
                    # 대용량 데이터는 샘플링
                    max_preview_rows = 20  # 미리보기 행 수 제한
                    max_preview_cols = 10  # 컬럼 수 제한
                    
                    if feature_count > max_preview_rows:
                        st.info(f"⚠️ 전체 {feature_count:,}개 피처 중 {max_preview_rows}개만 미리보기합니다.")
                        preview_gdf = gdf.head(max_preview_rows)
                    else:
                        preview_gdf = gdf
                    
                    # 컬럼 선택 (geometry와 geometry 관련 컬럼 제외, 중요 컬럼만)
                    cols_to_show = [col for col in preview_gdf.columns if col != 'geometry'][:max_preview_cols]
                    preview_df = preview_gdf[cols_to_show] if cols_to_show else preview_gdf.iloc[:, :max_preview_cols]
                    
                    st.dataframe(preview_df, use_container_width=True)
                    
                    if feature_count > max_preview_rows:
                        st.caption(f"전체 피처 수: {feature_count:,}개 | 전체 컬럼 수: {len(gdf.columns)}개")
            
            # 참고 안내
            st.markdown("---")
            with st.expander("ℹ️ 도시공간데이터 포털 사용 안내"):
                st.markdown("""
                ### 도시공간데이터 다운로드 방법
                
                1. **도시공간데이터포털** 접속: [https://www.citydata.go.kr](https://www.citydata.go.kr)
                
                2. **원하는 데이터셋 검색** (예: 행정구역, 토지소유정보, 개별공시지가 등)
                
                3. **ZIP 파일 다운로드** (반드시 ZIP 형식으로)
                
                4. **여기에 업로드**하여 지도에서 확인
                
                ### 주요 데이터셋
                
                - **행정구역**: 시군구, 읍면동 경계
                - **토지소유정보**: 토지 소유자 정보
                - **개별공시지가**: 공시지가 정보
                - **도로명주소 건물**: 건물 위치 및 주소 정보
                - **국토계획 시설**: 도시계획 시설 위치
                
                ### 좌표계 안내
                
                - 자동으로 WGS84(EPSG:4326)로 변환되어 지도에 표시됩니다
                - GRS80, Bessel 등 한국 좌표계도 자동 지원됩니다
                """)

# 입지 후보지 시각화 탭
if tab3 is not None:
    with tab3:
        st.header("입지 후보지 시각화")
        st.markdown("**Document Analysis의 '입지 선정 분석' 결과를 지도에서 확인하세요.**")
        
        # 개발중 UI 표시
        st.markdown("---")
        st.warning("🚧 **이 기능은 현재 개발 중입니다.**")

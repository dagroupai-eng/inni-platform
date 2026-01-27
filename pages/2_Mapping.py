from __future__ import annotations

import streamlit as st

# 페이지 설정 (반드시 최상단에 있어야 함)
st.set_page_config(
    page_title="지도 분석",
    page_icon=None,
    layout="wide"
)

# 세션 초기화 (로그인 + 작업 데이터 복원)
try:
    from auth.session_init import init_page_session
    init_page_session()
except Exception as e:
    print(f"세션 초기화 오류: {e}")

# 인증 모듈 import
try:
    from auth.authentication import check_page_access
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False

# 로그인 체크
if AUTH_AVAILABLE:
    check_page_access()

import pandas as pd
import requests
import time
import json
from datetime import datetime

# 클라이언트 사이드 JavaScript API 호출용
try:
    from streamlit_javascript import st_javascript
    JS_AVAILABLE = True
except ImportError:
    JS_AVAILABLE = False
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

def get_vworld_domain():
    """VWorld API 도메인을 가져옵니다. 서버사이드 요청 시 필요"""
    # 1. Streamlit secrets에서 확인
    try:
        if hasattr(st, 'secrets') and 'VWORLD_DOMAIN' in st.secrets:
            domain = st.secrets['VWORLD_DOMAIN']
            if domain and domain != "*.streamlit.app":  # 와일드카드 무시
                return domain
    except Exception:
        pass
    # 2. 환경 변수에서 확인
    env_domain = os.getenv("VWORLD_DOMAIN")
    if env_domain and env_domain != "*.streamlit.app":
        return env_domain
    # 3. 설정되지 않음 - None 반환 (도메인 파라미터 생략)
    return None

VWORLD_DOMAIN = get_vworld_domain()


def add_domain_param(params: dict) -> dict:
    """도메인이 설정된 경우에만 파라미터에 추가"""
    if VWORLD_DOMAIN:
        params['domain'] = VWORLD_DOMAIN
    return params


def get_vworld_headers() -> dict:
    """V-World API 요청용 헤더 (Referer 포함)"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    if VWORLD_DOMAIN:
        headers['Referer'] = f'https://{VWORLD_DOMAIN}/'
    return headers


# ========================================
# 클라이언트 사이드 API 호출 (JavaScript)
# Streamlit Cloud에서 서버사이드 요청이 차단될 때 사용
# ========================================

def fetch_vworld_api_client_side(url: str, timeout_ms: int = 10000) -> Optional[Dict[str, Any]]:
    """
    클라이언트 사이드(브라우저)에서 VWorld API 호출
    Streamlit Cloud 서버가 해외 IP라서 차단될 때 우회용
    """
    if not JS_AVAILABLE:
        return None

    try:
        # JavaScript fetch API로 호출
        js_code = f"""
        await fetch("{url}")
            .then(response => response.json())
            .then(data => data)
            .catch(error => ({{ "error": error.message }}))
        """
        result = st_javascript(js_code, key=f"vworld_fetch_{hash(url)}")

        if result and isinstance(result, dict) and 'error' not in result:
            return result
        return None
    except Exception as e:
        return None


def geocode_address_client_side(address: str, address_type: str = "road") -> Optional[Dict[str, Any]]:
    """클라이언트 사이드에서 지오코딩 (브라우저에서 직접 API 호출)"""
    if not JS_AVAILABLE:
        return None

    import urllib.parse
    encoded_address = urllib.parse.quote(address)

    url = (
        f"https://api.vworld.kr/req/address?"
        f"service=address&request=getcoord&version=2.0&crs=EPSG:4326"
        f"&address={encoded_address}&refine=true&simple=false&format=json"
        f"&type={address_type}&key={VWORLD_API_KEY}"
    )

    data = fetch_vworld_api_client_side(url)

    if data and data.get('response', {}).get('status') == 'OK':
        result = data['response'].get('result')
        if result and 'point' in result:
            point = result['point']
            return {
                'lat': float(point['y']),
                'lon': float(point['x']),
                'address': data['response'].get('refined', {}).get('text', address),
                'road_address': data['response'].get('refined', {}).get('structure', {}).get('level4A', ''),
                'parcel_address': ''
            }
    return None


def get_wfs_layer_data_client_side(layer_code: str, bbox: Tuple[float, float, float, float],
                                    max_features: int = 1000) -> Optional[Dict[str, Any]]:
    """클라이언트 사이드에서 WFS 데이터 조회 (layer_code 기반)"""
    if not JS_AVAILABLE:
        return None

    # WFS typename 매핑
    typename = WFS_LAYER_MAPPING.get(layer_code, layer_code)
    return get_wfs_features_client_side(bbox, typename, max_features)


def get_wfs_features_client_side(bbox: Tuple[float, float, float, float],
                                  typename: str = "lp_pa_cbnd_bonbun",
                                  max_features: int = 100) -> Optional[Dict[str, Any]]:
    """클라이언트 사이드에서 WFS 데이터 조회 (typename 직접 지정)"""
    if not JS_AVAILABLE:
        return None

    minx, miny, maxx, maxy = bbox
    url = (
        f"{VWORLD_WFS_URL}?"
        f"SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature"
        f"&TYPENAME={typename}"
        f"&BBOX={miny},{minx},{maxy},{maxx}"
        f"&OUTPUT=application/json"
        f"&MAXFEATURES={max_features}"
        f"&SRSNAME=EPSG:4326"
        f"&key={VWORLD_API_KEY}"
    )

    return fetch_vworld_api_client_side(url, timeout_ms=30000)


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
    },
    # 행정경계 레이어
    'admin_sido': {
        'layer': 'lt_c_adsido',
        'style': 'lt_c_adsido',
        'name': '행정경계(시도)',
        'category': '행정경계',
        'color': '#8B4513'
    },
    'admin_sigungu': {
        'layer': 'lt_c_adsigg',
        'style': 'lt_c_adsigg',
        'name': '행정경계(시군구)',
        'category': '행정경계',
        'color': '#CD853F'
    },
    'admin_emd': {
        'layer': 'lt_c_ademd',
        'style': 'lt_c_ademd',
        'name': '행정경계(읍면동)',
        'category': '행정경계',
        'color': '#DEB887'
    },
    'admin_ri': {
        'layer': 'lt_c_adri',
        'style': 'lt_c_adri',
        'name': '행정경계(리)',
        'category': '행정경계',
        'color': '#F5DEB3'
    },
    # 용도구역/지구 추가
    'use_zone': {
        'layer': 'lt_c_uq141',
        'style': 'lt_c_uq141',
        'name': '용도구역',
        'category': '용도지역지구',
        'color': '#9370DB'
    },
    'protection_district': {
        'layer': 'lt_c_uq122',
        'style': 'lt_c_uq122',
        'name': '보호지구',
        'category': '용도지구',
        'color': '#7B68EE'
    },
    'disaster_prevention': {
        'layer': 'lt_c_uq125',
        'style': 'lt_c_uq125',
        'name': '방재지구',
        'category': '용도지구',
        'color': '#6A5ACD'
    },
    # 도시계획시설 추가
    'urban_welfare': {
        'layer': 'lt_c_upisuq154',
        'style': 'lt_c_upisuq154',
        'name': '도시계획(보건위생시설)',
        'category': '도시계획시설',
        'color': '#FF69B4'
    },
    'urban_infra': {
        'layer': 'lt_c_upisuq157',
        'style': 'lt_c_upisuq157',
        'name': '도시계획(기타기반시설)',
        'category': '도시계획시설',
        'color': '#DA70D6'
    },
    # 산업/자연환경
    'industrial_complex': {
        'layer': 'lt_c_indunit',
        'style': 'lt_c_indunit',
        'name': '산업단지',
        'category': '산업',
        'color': '#B8860B',
        'file_upload': True,  # API 미지원 - 파일 업로드 필요
    },
    'natural_park': {
        'layer': 'lt_c_npsbd',
        'style': 'lt_c_npsbd',
        'name': '자연공원구역',
        'category': '자연환경',
        'color': '#228B22'
    },
    # 건물/도로 (선형 레이어)
    'building': {
        'layer': 'lt_c_bldginfo',
        'style': 'lt_c_bldginfo',
        'name': 'GIS건물통합정보',
        'category': '건물',
        'color': '#FF6347',
        'file_upload': True,  # 대용량 데이터 - 파일 업로드 권장
    },
    'road_name_building': {
        'layer': 'lt_c_spbd',
        'style': 'lt_c_spbd',
        'name': '도로명주소건물',
        'category': '건물',
        'color': '#FF4500'
    },
    'road': {
        'layer': 'lt_l_sprd',
        'style': 'lt_l_sprd',
        'name': '도로중심선',
        'category': '도로',
        'color': '#696969'
    },
    'road_cadastral': {
        'layer': 'lt_l_n3a0020000',
        'style': 'lt_l_n3a0020000',
        'name': '지적도로중심선',
        'category': '도로',
        'color': '#808080'
    },
    # 수자원
    'small_river': {
        'layer': 'lt_c_wkmbbsn',
        'style': 'lt_c_wkmbbsn',
        'name': '소하천/소하천구역',
        'category': '수자원',
        'color': '#4682B4',
        'file_upload': True,  # API 미지원 - 파일 업로드 필요
    },
    # 토지 정보 (파일 업로드 필요)
    'land_ownership': {
        'layer': 'land_ownership',
        'style': 'land_ownership',
        'name': '토지소유정보',
        'category': '토지',
        'color': '#FFD700',
        'file_upload': True,  # API 미지원 - 파일 업로드 필요
    },
    'individual_land_price': {
        'layer': 'individual_land_price',
        'style': 'individual_land_price',
        'name': '개별공시지가정보',
        'category': '토지',
        'color': '#FFA500',
        'file_upload': True,  # API 미지원 - 파일 업로드 필요
    },
    # 도시화지역
    'urbanization_boundary': {
        'layer': 'urbanization_boundary',
        'style': 'urbanization_boundary',
        'name': '도시화지역 경계',
        'category': '용도지역',
        'color': '#DC143C',
        'file_upload': True,  # API 미지원 - 파일 업로드 필요
    },
}

# WFS 레이어 코드 매핑 (WMS -> WFS typename)
WFS_LAYER_MAPPING = {
    # 연속지적도
    'lp_pa_cbnd_bonbun': 'lp_pa_cbnd_bonbun',
    'lp_pa_cbnd_bubun': 'lp_pa_cbnd_bubun',
    # 행정경계
    'lt_c_adsido': 'lt_c_adsido',
    'lt_c_adsigg': 'lt_c_adsigg',
    'lt_c_ademd': 'lt_c_ademd',
    'lt_c_adri': 'lt_c_adri',
    # 용도지역
    'lt_c_uq111': 'lt_c_uq111',
    'lt_c_uq112': 'lt_c_uq112',
    'lt_c_uq113': 'lt_c_uq113',
    'lt_c_uq114': 'lt_c_uq114',
    # 용도지구
    'lt_c_uq121': 'lt_c_uq121',
    'lt_c_uq122': 'lt_c_uq122',
    'lt_c_uq125': 'lt_c_uq125',
    'lt_c_uq141': 'lt_c_uq141',
    'lt_c_ud801': 'lt_c_ud801',
    # 도시계획시설
    'lt_c_upisuq151': 'lt_c_upisuq151',
    'lt_c_upisuq152': 'lt_c_upisuq152',
    'lt_c_upisuq153': 'lt_c_upisuq153',
    'lt_c_upisuq154': 'lt_c_upisuq154',
    'lt_c_upisuq155': 'lt_c_upisuq155',
    'lt_c_upisuq156': 'lt_c_upisuq156',
    'lt_c_upisuq157': 'lt_c_upisuq157',
    'lt_c_upisuq158': 'lt_c_upisuq158',
    'lt_c_upisuq161': 'lt_c_upisuq161',
    # 산업/자연환경
    'lt_c_indunit': 'lt_c_indunit',
    'lt_c_npsbd': 'lt_c_npsbd',
    # 건물/도로
    'lt_c_bldginfo': 'lt_c_bldginfo',
    'lt_c_spbd': 'lt_c_spbd',
    'lt_l_sprd': 'lt_l_sprd',
    'lt_l_n3a0020000': 'lt_l_n3a0020000',
    # 수자원
    'lt_c_wkmbbsn': 'lt_c_wkmbbsn',
}

def get_wfs_layer_data(layer_code: str, bbox: Tuple[float, float, float, float],
                       max_features: int = 1000) -> Optional[Dict[str, Any]]:
    """
    WFS API로 레이어 데이터 조회 (GeoJSON 반환)

    Args:
        layer_code: WFS 레이어 코드 (예: lt_c_adsigg)
        bbox: (minx, miny, maxx, maxy) EPSG:4326
        max_features: 최대 피처 수

    Returns:
        GeoJSON 형식 데이터 또는 None
    """
    # WFS typename 매핑
    typename = WFS_LAYER_MAPPING.get(layer_code, layer_code)

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
        'key': VWORLD_API_KEY
    }
    # 서버사이드 요청 시 domain 파라미터 생략 (502 에러 방지)
    # params = add_domain_param(params)

    # Retry 로직 (502, 503, 504 오류 시 재시도)
    max_retries = 3
    retry_delay = 1  # 초
    response = None

    for attempt in range(max_retries):
        try:
            response = requests.get(VWORLD_WFS_URL, params=params, headers=get_vworld_headers(), timeout=30)

            # 5xx 서버 오류 시 재시도
            if response.status_code in [502, 503, 504] and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # 점진적 대기
                continue

            response.raise_for_status()
            break  # 성공 시 루프 탈출
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            # 서버사이드 실패 시 클라이언트 사이드로 fallback
            st.info("서버 요청 실패, 클라이언트 측에서 재시도 중...")
            client_result = get_wfs_layer_data_client_side(layer_code, bbox, max_features)
            if client_result:
                return client_result
            st.error(f"WFS 요청 실패: {str(e)}")
            return None

    if response is None:
        # 서버사이드 실패 시 클라이언트 사이드로 fallback
        client_result = get_wfs_layer_data_client_side(layer_code, bbox, max_features)
        if client_result:
            return client_result
        st.error("WFS 요청 실패: 응답 없음")
        return None

    try:
        # JSON 응답 확인
        content_type = response.headers.get('content-type', '')

        # XML 오류 응답 처리
        if 'application/xml' in content_type or 'text/xml' in content_type:
            # V-World API 오류 메시지 파싱
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)

                # ServiceException 찾기
                exception_elem = root.find('.//{http://www.opengis.net/ogc}ServiceException')
                if exception_elem is not None:
                    error_code = exception_elem.get('code', 'UNKNOWN')
                    error_msg = exception_elem.text or '알 수 없는 오류'

                    if error_code == 'INCORRECT_KEY':
                        st.error("**V-World API 키 오류**")
                        st.error(f"오류: {error_msg}")
                        st.info("""
                        **해결 방법:**
                        1. V-World 홈페이지(https://www.vworld.kr)에서 API 키 발급/확인
                        2. 프로젝트 루트의 `.env` 파일 열기
                        3. `VWORLD_API_KEY=발급받은키` 형식으로 저장
                        4. 애플리케이션 재시작

                        현재 사용 중인 키: `{0}...{1}`
                        """.format(VWORLD_API_KEY[:8] if len(VWORLD_API_KEY) > 8 else '***',
                                   VWORLD_API_KEY[-4:] if len(VWORLD_API_KEY) > 4 else ''))
                    else:
                        st.error(f"WFS API 오류: [{error_code}] {error_msg}")
                else:
                    st.error("WFS 요청 실패: XML 오류 응답")
                    st.error(f"응답 내용: {response.text[:500]}")

                return None
            except ET.ParseError:
                st.error("WFS 요청 실패: XML 파싱 오류")
                st.error(f"응답 내용: {response.text[:500]}")
                return None

        # JSON 응답 처리
        if 'application/json' not in content_type and 'text/javascript' not in content_type:
            st.error(f"WFS 요청 실패: 예상치 못한 응답 형식 (Content-Type: {content_type})")
            st.error(f"응답 내용: {response.text[:500]}")
            return None

        # JSON 파싱
        try:
            data = response.json()
            return data
        except ValueError as e:
            st.error(f"WFS 데이터 파싱 오류: JSON 형식이 아닙니다")
            st.error(f"응답 내용: {response.text[:500]}")
            return None

    except Exception as e:
        st.error(f"WFS 처리 중 예상치 못한 오류: {str(e)}")
        return None

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
        'key': VWORLD_API_KEY
    }
    # 서버사이드 요청 시 domain 파라미터 생략
    # params = add_domain_param(params)

    # Retry 로직
    max_retries = 3
    retry_delay = 1
    response = None

    for attempt in range(max_retries):
        try:
            response = requests.get(VWORLD_WMS_URL, params=params, headers=get_vworld_headers(), timeout=15)

            if response.status_code in [502, 503, 504] and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue

            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            st.error(f"GetFeatureInfo 요청 실패: {str(e)}")
            return None

    if response is None:
        return None

    try:
        # JSON 응답 파싱
        data = response.json()
        return data
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
        'key': VWORLD_API_KEY
    }
    # 서버사이드 요청 시 domain 파라미터 생략 (502 에러 방지)
    # params = add_domain_param(params)

    # Retry 로직 (502, 503, 504, Connection 오류 시 재시도)
    max_retries = 3
    retry_delay = 1  # 초
    response = None

    for attempt in range(max_retries):
        try:
            response = requests.get(VWORLD_WFS_URL, params=params, headers=get_vworld_headers(), timeout=30)

            # 5xx 서버 오류 시 재시도
            if response.status_code in [502, 503, 504] and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue

            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            # 서버사이드 실패 시 클라이언트 사이드로 fallback
            st.info("서버 요청 실패, 클라이언트 측에서 재시도 중...")
            client_result = get_wfs_features_client_side(bbox, typename, max_features)
            if client_result:
                return client_result
            st.error(f"WFS 요청 실패: {str(e)}")
            return None

    if response is None:
        # 서버사이드 실패 시 클라이언트 사이드로 fallback
        client_result = get_wfs_features_client_side(bbox, typename, max_features)
        if client_result:
            return client_result
        st.error("WFS 요청 실패: 응답 없음")
        return None

    try:
        # JSON 응답 확인
        content_type = response.headers.get('content-type', '')

        # XML 오류 응답 처리
        if 'application/xml' in content_type or 'text/xml' in content_type:
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                exception_elem = root.find('.//{http://www.opengis.net/ogc}ServiceException')
                if exception_elem is not None:
                    error_code = exception_elem.get('code', 'UNKNOWN')
                    error_msg = exception_elem.text or '알 수 없는 오류'
                    if error_code == 'INCORRECT_KEY':
                        st.error("V-World API 키가 올바르지 않습니다. .env 파일을 확인하세요.")
                    else:
                        st.error(f"WFS API 오류: [{error_code}] {error_msg}")
                return None
            except:
                return None

        # JSON 파싱 시도
        try:
            data = response.json()
            return data
        except ValueError:
            st.warning("WFS 데이터가 JSON 형식이 아닙니다")
            return None

    except Exception as e:
        st.error(f"WFS 처리 중 오류: {str(e)}")
        return None


# ========================================
# V-World Geocoder API (주소 ↔ 좌표 변환)
# ========================================

def geocode_address(address: str, address_type: str = "road") -> Optional[Dict[str, Any]]:
    """
    주소를 좌표로 변환 (지오코딩)

    Args:
        address: 주소 문자열 (예: "서울특별시 강남구 테헤란로 152")
        address_type: 주소 유형 ("road": 도로명주소, "parcel": 지번주소)

    Returns:
        {
            'lat': 위도,
            'lon': 경도,
            'address': 전체주소,
            'road_address': 도로명주소,
            'parcel_address': 지번주소
        } 또는 None
    """
    GEOCODER_URL = "https://api.vworld.kr/req/address"

    params = {
        'service': 'address',
        'request': 'getcoord',
        'version': '2.0',
        'crs': 'EPSG:4326',
        'address': address,
        'refine': 'true',
        'simple': 'false',
        'format': 'json',
        'type': address_type,
        'key': VWORLD_API_KEY
    }
    # 서버사이드 요청 시 domain 파라미터 생략 (502 에러 방지)
    # params = add_domain_param(params)

    # Retry 로직
    max_retries = 3
    retry_delay = 1
    response = None

    for attempt in range(max_retries):
        try:
            response = requests.get(GEOCODER_URL, params=params, headers=get_vworld_headers(), timeout=15)

            if response.status_code in [502, 503, 504] and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue

            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            # 서버사이드 실패 시 클라이언트 사이드로 fallback
            st.info("서버 요청 실패, 클라이언트 측에서 재시도 중...")
            client_result = geocode_address_client_side(address, address_type)
            if client_result:
                return client_result
            st.warning(f"지오코딩 요청 실패: {str(e)}")
            return None

    if response is None:
        # 서버사이드 실패 시 클라이언트 사이드로 fallback
        client_result = geocode_address_client_side(address, address_type)
        if client_result:
            return client_result
        return None

    try:
        data = response.json()

        if data.get('response', {}).get('status') == 'OK':
            result = data['response']['result']
            if result and 'point' in result:
                point = result['point']
                return {
                    'lat': float(point['y']),
                    'lon': float(point['x']),
                    'address': result.get('text', address),
                    'road_address': result.get('structure', {}).get('level4A', ''),
                    'parcel_address': result.get('parcel', '')
                }

        return None

    except Exception as e:
        st.warning(f"지오코딩 처리 오류: {str(e)}")
        return None


def reverse_geocode(lat: float, lon: float, address_type: str = "both") -> Optional[Dict[str, Any]]:
    """
    좌표를 주소로 변환 (역지오코딩)

    Args:
        lat: 위도
        lon: 경도
        address_type: 주소 유형 ("road": 도로명주소, "parcel": 지번주소, "both": 둘 다)

    Returns:
        {
            'road_address': 도로명주소,
            'parcel_address': 지번주소,
            'building': 건물명
        } 또는 None
    """
    REVERSE_GEOCODER_URL = "https://api.vworld.kr/req/address"

    params = {
        'service': 'address',
        'request': 'getaddress',
        'version': '2.0',
        'crs': 'EPSG:4326',
        'point': f'{lon},{lat}',
        'format': 'json',
        'type': address_type,
        'zipcode': 'true',
        'simple': 'false',
        'key': VWORLD_API_KEY
    }
    # 서버사이드 요청 시 domain 파라미터 생략
    # params = add_domain_param(params)

    # Retry 로직
    max_retries = 3
    retry_delay = 1
    response = None

    for attempt in range(max_retries):
        try:
            response = requests.get(REVERSE_GEOCODER_URL, params=params, headers=get_vworld_headers(), timeout=15)

            if response.status_code in [502, 503, 504] and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue

            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            st.warning(f"역지오코딩 요청 실패: {str(e)}")
            return None

    if response is None:
        return None

    try:
        data = response.json()

        if data.get('response', {}).get('status') == 'OK':
            result = data['response']['result']
            if result:
                # 여러 결과가 있을 수 있으므로 첫 번째 결과 사용
                first_result = result[0] if isinstance(result, list) else result

                return {
                    'road_address': first_result.get('text', ''),
                    'parcel_address': first_result.get('structure', {}).get('level4L', ''),
                    'building': first_result.get('structure', {}).get('detail', '')
                }

        return None

    except Exception as e:
        st.warning(f"역지오코딩 처리 오류: {str(e)}")
        return None


# ========================================
# V-World 검색 API (주소/POI 검색)
# ========================================

def search_address_or_poi(query: str, search_type: str = "address",
                          page: int = 1, size: int = 10) -> Optional[List[Dict[str, Any]]]:
    """
    주소 또는 POI(관심지점) 검색

    Args:
        query: 검색 쿼리 (예: "강남역", "서울시청", "테헤란로")
        search_type: 검색 유형 ("address": 주소 검색, "place": POI 검색, "all": 통합 검색)
        page: 페이지 번호 (1부터 시작)
        size: 페이지당 결과 수 (최대 100)

    Returns:
        [
            {
                'title': 장소명,
                'address': 주소,
                'lat': 위도,
                'lon': 경도,
                'category': 카테고리
            },
            ...
        ] 또는 None
    """
    SEARCH_URL = "https://api.vworld.kr/req/search"

    params = {
        'service': 'search',
        'request': 'search',
        'version': '2.0',
        'crs': 'EPSG:4326',
        'query': query,
        'type': search_type,
        'category': 'L4',  # 상세 카테고리
        'format': 'json',
        'errorformat': 'json',
        'page': str(page),
        'size': str(size),
        'key': VWORLD_API_KEY
    }
    # 서버사이드 요청 시 domain 파라미터 생략
    # params = add_domain_param(params)

    # Retry 로직
    max_retries = 3
    retry_delay = 1
    response = None

    for attempt in range(max_retries):
        try:
            response = requests.get(SEARCH_URL, params=params, headers=get_vworld_headers(), timeout=15)

            if response.status_code in [502, 503, 504] and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue

            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            st.warning(f"검색 요청 실패: {str(e)}")
            return None

    if response is None:
        return None

    try:
        data = response.json()

        if data.get('response', {}).get('status') == 'OK':
            items = data['response']['result'].get('items', [])

            results = []
            for item in items:
                result = {
                    'title': item.get('title', ''),
                    'address': item.get('address', ''),
                    'category': item.get('category', ''),
                }

                # 좌표 추출
                if 'point' in item:
                    point = item['point']
                    result['lon'] = float(point.get('x', 0))
                    result['lat'] = float(point.get('y', 0))

                results.append(result)

            return results if results else None

        return None

    except Exception as e:
        st.warning(f"검색 처리 오류: {str(e)}")
        return None


# ========================================
# 부동산 분석 기능
# ========================================

def filter_gdf_by_conditions(gdf, conditions: Dict[str, Any]):
    """
    GeoDataFrame을 여러 조건으로 필터링

    Args:
        gdf: GeoDataFrame
        conditions: 필터링 조건 딕셔너리
            {
                'price_min': 최소 가격,
                'price_max': 최대 가격,
                'area_min': 최소 면적,
                'area_max': 최대 면적,
                'zone_types': 용도지역 리스트,
                'building_usage': 건물 용도 리스트
            }

    Returns:
        필터링된 GeoDataFrame
    """
    try:
        import geopandas as gpd

        filtered = gdf.copy()

        # 가격 필터링
        if 'price_min' in conditions and conditions['price_min'] is not None:
            price_cols = [col for col in gdf.columns if any(k in col.upper() for k in ['공시', 'PRICE', '가격', 'PBLNTF'])]
            if price_cols:
                price_col = price_cols[0]
                filtered = filtered[filtered[price_col] >= conditions['price_min']]

        if 'price_max' in conditions and conditions['price_max'] is not None:
            price_cols = [col for col in gdf.columns if any(k in col.upper() for k in ['공시', 'PRICE', '가격', 'PBLNTF'])]
            if price_cols:
                price_col = price_cols[0]
                filtered = filtered[filtered[price_col] <= conditions['price_max']]

        # 면적 필터링
        if 'area_min' in conditions and conditions['area_min'] is not None:
            area_cols = [col for col in gdf.columns if any(k in col.upper() for k in ['AREA', '면적', 'LNDCGR'])]
            if area_cols:
                area_col = area_cols[0]
                filtered = filtered[filtered[area_col] >= conditions['area_min']]

        if 'area_max' in conditions and conditions['area_max'] is not None:
            area_cols = [col for col in gdf.columns if any(k in col.upper() for k in ['AREA', '면적', 'LNDCGR'])]
            if area_cols:
                area_col = area_cols[0]
                filtered = filtered[filtered[area_col] <= conditions['area_max']]

        # 용도지역 필터링
        if 'zone_types' in conditions and conditions['zone_types']:
            zone_cols = [col for col in gdf.columns if any(k in col.upper() for k in ['UQ_GB', 'PRPOS', '용도', 'ZONE'])]
            if zone_cols:
                zone_col = zone_cols[0]
                filtered = filtered[filtered[zone_col].isin(conditions['zone_types'])]

        # 건물 용도 필터링
        if 'building_usage' in conditions and conditions['building_usage']:
            usage_cols = [col for col in gdf.columns if any(k in col.upper() for k in ['용도', 'USE', 'USAGE', 'MAIN_PURPS'])]
            if usage_cols:
                usage_col = usage_cols[0]
                filtered = filtered[filtered[usage_col].isin(conditions['building_usage'])]

        return filtered

    except Exception as e:
        st.warning(f"필터링 중 오류: {str(e)}")
        return gdf


def calculate_accessibility(point_lat: float, point_lon: float,
                           facilities_gdf, facility_type: str = "시설") -> Dict[str, Any]:
    """
    특정 지점에서 시설까지의 접근성 계산

    Args:
        point_lat: 지점 위도
        point_lon: 지점 경도
        facilities_gdf: 시설 GeoDataFrame
        facility_type: 시설 유형 (표시용)

    Returns:
        {
            'nearest_distance': 가장 가까운 시설까지 거리(m),
            'count_500m': 반경 500m 내 시설 수,
            'count_1km': 반경 1km 내 시설 수,
            'count_2km': 반경 2km 내 시설 수,
            'accessibility_score': 접근성 점수 (0-100)
        }
    """
    try:
        import geopandas as gpd
        from shapely.geometry import Point

        if facilities_gdf is None or len(facilities_gdf) == 0:
            return {
                'nearest_distance': None,
                'count_500m': 0,
                'count_1km': 0,
                'count_2km': 0,
                'accessibility_score': 0
            }

        # 중심점 생성
        center_point = Point(point_lon, point_lat)
        center_gdf = gpd.GeoDataFrame([1], geometry=[center_point], crs='EPSG:4326')

        # 메트릭 좌표계로 변환 (거리 계산)
        facilities_proj = facilities_gdf.to_crs('EPSG:3857')
        center_proj = center_gdf.to_crs('EPSG:3857')

        # 거리 계산
        center_geom = center_proj.geometry.iloc[0]
        facilities_proj['distance'] = facilities_proj.geometry.distance(center_geom)

        # 가장 가까운 시설까지 거리
        nearest_distance = facilities_proj['distance'].min()

        # 반경별 시설 개수
        count_500m = len(facilities_proj[facilities_proj['distance'] <= 500])
        count_1km = len(facilities_proj[facilities_proj['distance'] <= 1000])
        count_2km = len(facilities_proj[facilities_proj['distance'] <= 2000])

        # 접근성 점수 계산 (거리 기반, 가까울수록 높은 점수)
        if nearest_distance < 100:
            accessibility_score = 100
        elif nearest_distance < 500:
            accessibility_score = 90 - (nearest_distance - 100) / 4
        elif nearest_distance < 1000:
            accessibility_score = 80 - (nearest_distance - 500) / 10
        elif nearest_distance < 2000:
            accessibility_score = 50 - (nearest_distance - 1000) / 20
        else:
            accessibility_score = max(0, 30 - (nearest_distance - 2000) / 100)

        return {
            'nearest_distance': round(nearest_distance, 1),
            'count_500m': count_500m,
            'count_1km': count_1km,
            'count_2km': count_2km,
            'accessibility_score': round(accessibility_score, 1)
        }

    except Exception as e:
        st.warning(f"접근성 계산 중 오류: {str(e)}")
        return {
            'nearest_distance': None,
            'count_500m': 0,
            'count_1km': 0,
            'count_2km': 0,
            'accessibility_score': 0
        }


def create_statistics_charts(gdf, layer_name: str = "레이어"):
    """
    GeoDataFrame의 속성 데이터로 통계 차트 생성

    Args:
        gdf: GeoDataFrame
        layer_name: 레이어 이름 (차트 제목용)

    Returns:
        plotly figure 리스트
    """
    try:
        import plotly.express as px
        import plotly.graph_objects as go

        figures = []

        # 1. 공시지가 분포 히스토그램
        price_cols = [col for col in gdf.columns if any(k in col.upper() for k in ['공시', 'PRICE', '가격', 'PBLNTF'])]
        if price_cols and len(gdf) > 0:
            price_col = price_cols[0]
            prices = gdf[price_col].dropna()
            if len(prices) > 0:
                fig = px.histogram(
                    prices,
                    nbins=30,
                    title=f'{layer_name} - 공시지가 분포',
                    labels={'value': '공시지가 (원/㎡)', 'count': '필지 수'}
                )
                fig.update_layout(showlegend=False, height=400)
                figures.append(('공시지가 분포', fig))

        # 2. 면적 분포 히스토그램
        area_cols = [col for col in gdf.columns if any(k in col.upper() for k in ['AREA', '면적', 'LNDCGR'])]
        if area_cols and len(gdf) > 0:
            area_col = area_cols[0]
            areas = gdf[area_col].dropna()
            if len(areas) > 0:
                fig = px.histogram(
                    areas,
                    nbins=30,
                    title=f'{layer_name} - 면적 분포',
                    labels={'value': '면적 (㎡)', 'count': '필지 수'}
                )
                fig.update_layout(showlegend=False, height=400)
                figures.append(('면적 분포', fig))

        # 3. 건물 층수 분포
        floor_cols = [col for col in gdf.columns if any(k in col.upper() for k in ['층', 'FLOOR', 'GRND_FLR'])]
        if floor_cols and len(gdf) > 0:
            floor_col = floor_cols[0]
            floors = gdf[floor_col].dropna()
            if len(floors) > 0:
                fig = px.histogram(
                    floors,
                    nbins=20,
                    title=f'{layer_name} - 층수 분포',
                    labels={'value': '층수', 'count': '건물 수'}
                )
                fig.update_layout(showlegend=False, height=400)
                figures.append(('층수 분포', fig))

        # 4. 용도지역 파이 차트
        zone_cols = [col for col in gdf.columns if any(k in col.upper() for k in ['UQ_GB', 'PRPOS', '용도', 'ZONE'])]
        if zone_cols and len(gdf) > 0:
            zone_col = zone_cols[0]
            zone_counts = gdf[zone_col].value_counts()
            if len(zone_counts) > 0:
                fig = px.pie(
                    values=zone_counts.values,
                    names=zone_counts.index,
                    title=f'{layer_name} - 용도지역 분포'
                )
                fig.update_layout(height=400)
                figures.append(('용도지역 분포', fig))

        # 5. 건물 용도 파이 차트
        usage_cols = [col for col in gdf.columns if any(k in col.upper() for k in ['용도', 'USE', 'USAGE', 'MAIN_PURPS'])]
        if usage_cols and len(gdf) > 0:
            usage_col = usage_cols[0]
            usage_counts = gdf[usage_col].value_counts().head(10)  # 상위 10개만
            if len(usage_counts) > 0:
                fig = px.pie(
                    values=usage_counts.values,
                    names=usage_counts.index,
                    title=f'{layer_name} - 건물 용도 분포 (상위 10개)'
                )
                fig.update_layout(height=400)
                figures.append(('건물 용도 분포', fig))

        return figures

    except Exception as e:
        st.warning(f"차트 생성 중 오류: {str(e)}")
        return []


def calculate_radius_statistics(center_lat: float, center_lon: float,
                                layers_dict: Dict[str, Any],
                                radius_m: float = 1000) -> Dict[str, Any]:
    """
    반경 내 레이어별 통계 계산

    Args:
        center_lat: 중심점 위도
        center_lon: 중심점 경도
        layers_dict: {'레이어명': GeoDataFrame} 딕셔너리
        radius_m: 반경 (미터)

    Returns:
        레이어별 통계 딕셔너리
    """
    try:
        import geopandas as gpd
        from shapely.geometry import Point

        # 중심점 생성
        center_point = Point(center_lon, center_lat)
        center_gdf = gpd.GeoDataFrame([1], geometry=[center_point], crs='EPSG:4326')
        center_proj = center_gdf.to_crs('EPSG:3857')
        center_geom = center_proj.geometry.iloc[0]

        statistics = {}

        for layer_name, gdf in layers_dict.items():
            if gdf is None or len(gdf) == 0:
                continue

            # 메트릭 좌표계로 변환
            gdf_proj = gdf.to_crs('EPSG:3857')

            # 거리 계산
            gdf_proj['distance'] = gdf_proj.geometry.distance(center_geom)

            # 반경 내 필터링
            within_radius = gdf_proj[gdf_proj['distance'] <= radius_m]

            if len(within_radius) == 0:
                continue

            # 통계 계산
            stats = {
                'count': len(within_radius),
                'avg_distance': round(within_radius['distance'].mean(), 1),
                'min_distance': round(within_radius['distance'].min(), 1),
                'density': round(len(within_radius) / (3.14159 * (radius_m/1000)**2), 2)  # 개/km²
            }

            # 공시지가 통계 (있는 경우)
            price_cols = [col for col in within_radius.columns if any(k in col.upper() for k in ['공시', 'PRICE', '가격'])]
            if price_cols:
                price_col = price_cols[0]
                prices = within_radius[price_col].dropna()
                if len(prices) > 0:
                    stats['avg_price'] = int(prices.mean())
                    stats['min_price'] = int(prices.min())
                    stats['max_price'] = int(prices.max())

            # 면적 통계 (있는 경우)
            area_cols = [col for col in within_radius.columns if any(k in col.upper() for k in ['AREA', '면적'])]
            if area_cols:
                area_col = area_cols[0]
                areas = within_radius[area_col].dropna()
                if len(areas) > 0:
                    stats['avg_area'] = round(areas.mean(), 1)
                    stats['total_area'] = round(areas.sum(), 1)

            statistics[layer_name] = stats

        return statistics

    except Exception as e:
        st.warning(f"반경 통계 계산 중 오류: {str(e)}")
        return {}


def filter_and_export_radius_data(center_lat: float, center_lon: float,
                                   radius_m: float, layers_dict: Dict[str, Any],
                                   export_format: str = 'geojson') -> Tuple[Any, str]:
    """
    반경 내 데이터 필터링 후 GeoJSON/CSV 반환

    Args:
        center_lat: 중심점 위도
        center_lon: 중심점 경도
        radius_m: 반경 (미터)
        layers_dict: {'레이어명': geojson dict} 딕셔너리
        export_format: 'geojson', 'csv', 'combined_geojson'

    Returns:
        (data, filename): 필터링된 데이터와 파일명
    """
    try:
        import geopandas as gpd
        from shapely.geometry import Point
        import json
        from datetime import datetime

        # 중심점 생성
        center_point = Point(center_lon, center_lat)
        center_gdf = gpd.GeoDataFrame([1], geometry=[center_point], crs='EPSG:4326')
        center_proj = center_gdf.to_crs('EPSG:3857')
        center_geom = center_proj.geometry.iloc[0]

        filtered_features = []
        csv_records = []

        for layer_name, data in layers_dict.items():
            geojson = data.get('geojson', data) if isinstance(data, dict) else data
            features = geojson.get('features', []) if isinstance(geojson, dict) else []

            if not features:
                continue

            gdf = gpd.GeoDataFrame.from_features(features, crs='EPSG:4326')
            gdf_proj = gdf.to_crs('EPSG:3857')
            gdf_proj['distance'] = gdf_proj.geometry.distance(center_geom)

            # 반경 내 필터링
            within_radius = gdf_proj[gdf_proj['distance'] <= radius_m].copy()

            if len(within_radius) == 0:
                continue

            # 원래 좌표계로 복원
            within_radius_wgs = within_radius.to_crs('EPSG:4326')

            for idx, row in within_radius_wgs.iterrows():
                # GeoJSON feature 생성
                feature = {
                    'type': 'Feature',
                    'geometry': row.geometry.__geo_interface__,
                    'properties': {k: v for k, v in row.items() if k not in ['geometry', 'distance']}
                }
                feature['properties']['_layer'] = layer_name
                feature['properties']['_distance_m'] = round(within_radius.loc[idx, 'distance'], 1)
                filtered_features.append(feature)

                # CSV 레코드
                csv_record = {k: v for k, v in row.items() if k not in ['geometry']}
                csv_record['_layer'] = layer_name
                csv_record['_distance_m'] = round(within_radius.loc[idx, 'distance'], 1)
                csv_records.append(csv_record)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if export_format == 'csv':
            if csv_records:
                df = pd.DataFrame(csv_records)
                return df.to_csv(index=False, encoding='utf-8-sig'), f"radius_{int(radius_m)}m_{timestamp}.csv"
            return "", f"empty_{timestamp}.csv"

        # GeoJSON 형식
        combined_geojson = {
            'type': 'FeatureCollection',
            'metadata': {
                'center': [center_lat, center_lon],
                'radius_m': radius_m,
                'total_features': len(filtered_features),
                'exported_at': datetime.now().isoformat()
            },
            'features': filtered_features
        }

        return json.dumps(combined_geojson, ensure_ascii=False, indent=2), f"radius_{int(radius_m)}m_{timestamp}.geojson"

    except Exception as e:
        return json.dumps({'error': str(e)}), 'error.json'


def calculate_radius_statistics_extended(center_lat: float, center_lon: float,
                                         layers_dict: Dict[str, Any],
                                         radius_m: float = 1000) -> Dict[str, Any]:
    """
    반경 내 확장 통계 계산 (시각화용)

    Args:
        center_lat: 중심점 위도
        center_lon: 중심점 경도
        layers_dict: {'레이어명': geojson dict} 딕셔너리
        radius_m: 반경 (미터)

    Returns:
        시각화용 확장 통계 딕셔너리
    """
    try:
        import geopandas as gpd
        from shapely.geometry import Point
        from collections import Counter

        # 중심점 생성
        center_point = Point(center_lon, center_lat)
        center_gdf = gpd.GeoDataFrame([1], geometry=[center_point], crs='EPSG:4326')
        center_proj = center_gdf.to_crs('EPSG:3857')
        center_geom = center_proj.geometry.iloc[0]

        stats = {
            'zoning': Counter(),  # 용도지역 분포
            'prices': [],  # 공시지가 분포
            'areas': [],  # 면적 분포
            'building_uses': Counter(),  # 건물용도 분포
            'floors': [],  # 층수 분포
            'by_layer': {}  # 레이어별 통계
        }

        for layer_name, data in layers_dict.items():
            geojson = data.get('geojson', data) if isinstance(data, dict) else data
            features = geojson.get('features', []) if isinstance(geojson, dict) else []

            if not features:
                continue

            gdf = gpd.GeoDataFrame.from_features(features, crs='EPSG:4326')
            gdf_proj = gdf.to_crs('EPSG:3857')
            gdf_proj['distance'] = gdf_proj.geometry.distance(center_geom)

            within_radius = gdf_proj[gdf_proj['distance'] <= radius_m]

            if len(within_radius) == 0:
                continue

            layer_stats = {'count': len(within_radius)}

            # 용도지역 카운트
            zone_cols = [col for col in within_radius.columns
                        if any(k in col.upper() for k in ['용도', 'ZONE', 'USE', 'JIJIMOK'])]
            for col in zone_cols:
                for val in within_radius[col].dropna():
                    stats['zoning'][str(val)] += 1

            # 공시지가 수집
            price_cols = [col for col in within_radius.columns
                         if any(k in col.upper() for k in ['공시', 'PRICE', '가격', 'PBLNTF'])]
            for col in price_cols:
                prices = within_radius[col].dropna().tolist()
                stats['prices'].extend([p for p in prices if isinstance(p, (int, float)) and p > 0])
                if prices:
                    layer_stats['avg_price'] = sum(prices) / len(prices)

            # 면적 수집
            area_cols = [col for col in within_radius.columns
                        if any(k in col.upper() for k in ['AREA', '면적', 'LNDPCLR'])]
            for col in area_cols:
                areas = within_radius[col].dropna().tolist()
                stats['areas'].extend([a for a in areas if isinstance(a, (int, float)) and a > 0])
                if areas:
                    layer_stats['total_area'] = sum(areas)

            # 건물용도 카운트
            bldg_cols = [col for col in within_radius.columns
                        if any(k in col.upper() for k in ['PURPS', '용도', 'USE', '주용도'])]
            for col in bldg_cols:
                for val in within_radius[col].dropna():
                    stats['building_uses'][str(val)] += 1

            # 층수 수집
            floor_cols = [col for col in within_radius.columns
                         if any(k in col.upper() for k in ['FLOOR', '층', 'GRND', 'UGRND'])]
            for col in floor_cols:
                floors = within_radius[col].dropna().tolist()
                stats['floors'].extend([f for f in floors if isinstance(f, (int, float)) and f > 0])

            stats['by_layer'][layer_name] = layer_stats

        return stats

    except Exception as e:
        return {'error': str(e)}


def calculate_site_score(site_info: Dict[str, Any], weights: Dict[str, float] = None) -> Dict[str, Any]:
    """
    후보지 종합 점수 계산

    Args:
        site_info: 후보지 정보
            {
                'accessibility_scores': {'지하철': {...}, '학교': {...}, ...},
                'price_score': 지가 적정성 점수,
                'zone_score': 용도 적합성 점수,
                'area_score': 면적 적정성 점수
            }
        weights: 가중치 딕셔너리 (기본값: 동일 가중치)

    Returns:
        {
            'total_score': 종합 점수,
            'detailed_scores': 세부 점수,
            'grade': 등급 (S/A/B/C/D)
        }
    """
    try:
        if weights is None:
            weights = {
                'accessibility': 0.35,
                'price': 0.25,
                'zone': 0.25,
                'area': 0.15
            }

        detailed_scores = {}

        # 1. 접근성 점수 (여러 시설의 평균)
        accessibility_scores = site_info.get('accessibility_scores', {})
        if accessibility_scores:
            avg_accessibility = sum(s.get('accessibility_score', 0) for s in accessibility_scores.values()) / len(accessibility_scores)
            detailed_scores['accessibility'] = round(avg_accessibility, 1)
        else:
            detailed_scores['accessibility'] = 50  # 기본값

        # 2. 지가 적정성 점수
        detailed_scores['price'] = site_info.get('price_score', 50)

        # 3. 용도 적합성 점수
        detailed_scores['zone'] = site_info.get('zone_score', 50)

        # 4. 면적 적정성 점수
        detailed_scores['area'] = site_info.get('area_score', 50)

        # 종합 점수 계산 (가중평균)
        total_score = (
            detailed_scores['accessibility'] * weights['accessibility'] +
            detailed_scores['price'] * weights['price'] +
            detailed_scores['zone'] * weights['zone'] +
            detailed_scores['area'] * weights['area']
        )

        # 등급 산정
        if total_score >= 90:
            grade = 'S'
        elif total_score >= 80:
            grade = 'A'
        elif total_score >= 70:
            grade = 'B'
        elif total_score >= 60:
            grade = 'C'
        else:
            grade = 'D'

        return {
            'total_score': round(total_score, 1),
            'detailed_scores': detailed_scores,
            'grade': grade,
            'weights': weights
        }

    except Exception as e:
        st.warning(f"점수 계산 중 오류: {str(e)}")
        return {
            'total_score': 0,
            'detailed_scores': {},
            'grade': 'N/A',
            'weights': weights or {}
        }


def create_cadastral_map(center_lat: float = 37.5665, center_lon: float = 126.9780,
                         zoom: int = 17, show_bonbun: bool = True,
                         show_bubun: bool = True,
                         selected_zone_layers: List[str] = None,
                         show_radius: bool = False,
                         radius_meters: int = 1000):
    """
    연속 지적도 및 지역지구 WMS 레이어가 포함된 Folium 지도 생성

    Args:
        center_lat: 중심 위도
        center_lon: 중심 경도
        zoom: 줌 레벨
        show_bonbun: 본번 레이어 표시 여부
        show_bubun: 부번 레이어 표시 여부
        selected_zone_layers: 표시할 지역지구 레이어 키 목록
        show_radius: 반경 원 표시 여부
        radius_meters: 반경 크기 (미터)

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

        # 반경 원 표시
        if show_radius:
            # 중심점 마커
            folium.Marker(
                location=[center_lat, center_lon],
                popup=f"중심점<br>위도: {center_lat:.6f}<br>경도: {center_lon:.6f}",
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

            # 반경 원
            folium.Circle(
                location=[center_lat, center_lon],
                radius=radius_meters,
                popup=f"반경 {radius_meters}m ({radius_meters/1000:.1f}km)",
                color='#FF6B6B',
                fill=True,
                fillColor='#FF6B6B',
                fillOpacity=0.15,
                weight=2,
                dash_array='5, 10'
            ).add_to(m)

            # 추가 반경들 (500m, 1km, 2km)
            if radius_meters >= 500:
                folium.Circle(
                    location=[center_lat, center_lon],
                    radius=500,
                    popup="반경 500m",
                    color='#4ECDC4',
                    fill=False,
                    weight=1.5,
                    dash_array='3, 6',
                    opacity=0.5
                ).add_to(m)

            if radius_meters >= 1000:
                folium.Circle(
                    location=[center_lat, center_lon],
                    radius=1000,
                    popup="반경 1km",
                    color='#45B7D1',
                    fill=False,
                    weight=1.5,
                    dash_array='3, 6',
                    opacity=0.5
                ).add_to(m)

            if radius_meters >= 2000:
                folium.Circle(
                    location=[center_lat, center_lon],
                    radius=2000,
                    popup="반경 2km",
                    color='#95E085',
                    fill=False,
                    weight=1.5,
                    dash_array='3, 6',
                    opacity=0.4
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

# ========================================
# 통합 지도 페이지 (탭 없음)
# ========================================
st.header("연속 지적도 및 공간데이터 조회")
st.markdown("**VWorld WMS API와 Shapefile 업로드를 통해 지적도 및 공간 데이터를 조회합니다.**")

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

# 설정 영역 (위에 배치)
st.subheader("설정")

# 위치 검색 - Expander로 접기
with st.expander("위치 검색 및 설정", expanded=False):
    st.markdown("**주소/장소 통합 검색**")
    search_query = st.text_input(
        "주소 또는 장소명을 입력하세요",
        placeholder="예: 강남역, 서울시청, 테헤란로 152",
        help="주소, 건물명, 랜드마크 등을 검색할 수 있습니다"
    )

    if search_query:
        if st.button("🔍 검색", type="primary", use_container_width=True):
            with st.spinner("검색 중..."):
                import time
                results = []

                # 주소 검색만 시도 (V-World 연속 요청 제한 회피)
                address_result = geocode_address(search_query, address_type="road")

                if address_result:
                    results.append({
                        'title': search_query,
                        'address': address_result['address'],
                        'lat': address_result['lat'],
                        'lon': address_result['lon'],
                        'category': '주소'
                    })
                    # 첫 결과 성공 시 바로 지도 이동
                    st.session_state.cadastral_center_lat = address_result['lat']
                    st.session_state.cadastral_center_lon = address_result['lon']
                    st.session_state.selected_location_info = {
                        'title': search_query,
                        'address': address_result['address'],
                        'lat': address_result['lat'],
                        'lon': address_result['lon']
                    }
                    st.success(f"✅ '{address_result['address']}'로 이동합니다")
                    st.rerun()
                else:
                    st.error("검색 결과가 없습니다. 정확한 주소나 장소명을 입력해보세요.")

    # 검색 결과 표시
    if 'search_results' in st.session_state and st.session_state.search_results:
        st.markdown("**검색 결과 선택** (클릭하면 지도가 이동합니다)")

        for idx, result in enumerate(st.session_state.search_results):
            title = result.get('title', '제목 없음')
            address = result.get('address', '주소 없음')
            category = result.get('category', '')

            result_text = f"📍 {title}"
            if category:
                result_text += f" ({category})"
            if address:
                result_text += f"\n   {address}"

            if st.button(result_text, key=f"search_result_{idx}", use_container_width=True):
                if 'lat' in result and 'lon' in result:
                    st.session_state.cadastral_center_lat = result['lat']
                    st.session_state.cadastral_center_lon = result['lon']
                    st.session_state.selected_location_info = {
                        'title': title,
                        'address': address,
                        'lat': result['lat'],
                        'lon': result['lon']
                    }
                    st.session_state.search_results = None
                    st.rerun()

        # 검색 결과 초기화 버튼
        if st.button("검색 결과 지우기", use_container_width=True):
            st.session_state.search_results = None
            st.rerun()

    # 선택된 위치 정보 표시 및 확정 버튼
    if 'selected_location_info' in st.session_state and st.session_state.selected_location_info:
        loc_info = st.session_state.selected_location_info
        st.success(f"**선택된 위치**: {loc_info['title']}\n{loc_info['address']}")

        col_confirm, col_clear = st.columns(2)
        with col_confirm:
            if st.button("✅ 이 위치로 확정", type="primary", use_container_width=True):
                st.toast(f"'{loc_info['title']}' 위치가 확정되었습니다!")
        with col_clear:
            if st.button("❌ 선택 취소", use_container_width=True):
                st.session_state.selected_location_info = None
                st.rerun()

    st.markdown("---")
    st.markdown("**좌표 직접 입력**")

    # 좌표 입력을 위한 임시 변수 초기화
    if 'temp_input_lat' not in st.session_state:
        st.session_state.temp_input_lat = st.session_state.cadastral_center_lat
    if 'temp_input_lon' not in st.session_state:
        st.session_state.temp_input_lon = st.session_state.cadastral_center_lon

    # 주소 검색 후 업데이트 확인
    if st.session_state.temp_input_lat != st.session_state.cadastral_center_lat:
        st.session_state.temp_input_lat = st.session_state.cadastral_center_lat
    if st.session_state.temp_input_lon != st.session_state.cadastral_center_lon:
        st.session_state.temp_input_lon = st.session_state.cadastral_center_lon

    search_lat = st.number_input(
        "위도",
        value=st.session_state.cadastral_center_lat,
        format="%.6f",
        step=0.001
    )
    search_lon = st.number_input(
        "경도",
        value=st.session_state.cadastral_center_lon,
        format="%.6f",
        step=0.001
    )

    if st.button("좌표로 이동", type="primary", use_container_width=True):
        st.session_state.cadastral_center_lat = search_lat
        st.session_state.cadastral_center_lon = search_lon
        st.session_state.temp_input_lat = search_lat
        st.session_state.temp_input_lon = search_lon
        st.rerun()

    st.markdown("---")
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

    st.markdown("---")

    # 레이어 설정
    st.markdown("**연속 지적도 레이어**")
    show_bonbun = st.checkbox("본번 레이어", value=True, help="연속지적도 본번 표시")
    show_bubun = st.checkbox("부번 레이어", value=True, help="연속지적도 부번 표시")

    st.markdown("---")

    # 반경 표시 설정
    st.markdown("**반경 표시**")
    show_radius = st.checkbox("반경 원 표시", value=False, help="중심점으로부터 반경 원을 지도에 표시합니다")

    if show_radius:
        radius_meters = st.select_slider(
            "반경 크기",
            options=[500, 1000, 1500, 2000, 3000, 5000],
            value=1000,
            format_func=lambda x: f"{x}m ({x/1000:.1f}km)",
            help="500m, 1km, 2km 기준선도 함께 표시됩니다"
        )
    else:
        radius_meters = 1000

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

    # 전체 선택/해제 버튼
    col_sel_all, col_desel_all = st.columns(2)
    with col_sel_all:
        if st.button("전체 선택", key="select_all_zones", use_container_width=True):
            st.session_state.selected_zone_layers = list(ZONE_LAYERS.keys())
            st.rerun()
    with col_desel_all:
        if st.button("전체 해제", key="deselect_all_zones", use_container_width=True):
            st.session_state.selected_zone_layers = []
            st.rerun()

    selected_zones = []

    for category, layers in zone_categories.items():
        with st.expander(f"{category} ({len(layers)}개)", expanded=False):
            for zone_key, zone_info in layers:
                # 색상 미리보기 포함
                color = zone_info.get('color', '#888888')
                file_upload_required = zone_info.get('file_upload', False)

                # 레이어명 구성
                layer_label = f"🔲 {zone_info['name']}"
                if file_upload_required:
                    layer_label = f"📂 {zone_info['name']} (파일 업로드 필요)"

                help_text = f"레이어: {zone_info['layer']} | 색상: {color}"
                if file_upload_required:
                    help_text += "\n[주의] 이 레이어는 V-World API에서 직접 다운로드할 수 없습니다. Shapefile을 직접 업로드해주세요."

                is_selected = st.checkbox(
                    layer_label,
                    value=zone_key in st.session_state.selected_zone_layers,
                    key=f"zone_{zone_key}",
                    help=help_text,
                    disabled=file_upload_required  # 파일 업로드 필요한 레이어는 비활성화
                )
                if is_selected and not file_upload_required:
                    selected_zones.append(zone_key)

    # 선택된 레이어 저장
    st.session_state.selected_zone_layers = selected_zones

    # 선택된 레이어 수 표시
    total_layers = len(ZONE_LAYERS)
    api_available_layers = len([k for k, v in ZONE_LAYERS.items() if not v.get('file_upload', False)])

    if selected_zones:
        st.success(f"선택됨: {len(selected_zones)}/{api_available_layers}개 레이어")
    else:
        st.caption(f"레이어: 0/{api_available_layers}개 선택됨")

    st.markdown("---")

    # Shapefile 업로드 섹션 (사이드바에 통합)
    with st.expander("📂 Shapefile 업로드", expanded=False):
        # 파일 업로드가 필요한 레이어 안내
        file_upload_layers = [(k, v) for k, v in ZONE_LAYERS.items() if v.get('file_upload', False)]
        if file_upload_layers:
            st.info("다음 레이어들은 API로 다운로드할 수 없습니다:")
            for layer_key, layer_info in file_upload_layers:
                st.markdown(f"- {layer_info['name']}")

        # Shapefile 업로드
        if GEO_MODULE_AVAILABLE:
            # Session state 초기화 (레이어 저장용)
            if 'geo_layers' not in st.session_state:
                st.session_state.geo_layers = {}
            if 'uploaded_layers' not in st.session_state:
                st.session_state.uploaded_layers = {}

            uploaded_files = st.file_uploader(
                "ZIP 파일 업로드",
                type=['zip'],
                accept_multiple_files=True,
                help="Shapefile이 포함된 ZIP 파일을 업로드하세요"
            )

            if uploaded_files:
                loader = GeoDataLoader()

                for uploaded_file in uploaded_files:
                    layer_name = uploaded_file.name.replace('.zip', '').replace('.ZIP', '')

                    # 중복 체크
                    if layer_name in st.session_state.uploaded_layers:
                        st.warning(f"[주의] {layer_name}은 이미 업로드되었습니다.")
                        continue

                    result = loader.load_shapefile_from_zip(
                        uploaded_file.getvalue(),
                        encoding='cp949'
                    )

                    if result['success']:
                        st.session_state.uploaded_layers[layer_name] = {
                            'gdf': result['gdf'],
                            'info': {
                                'feature_count': result['feature_count'],
                                'columns': result['columns'],
                                'crs': result['crs']
                            }
                        }
                        st.success(f" {layer_name} 업로드 완료")
                    else:
                        st.error(f"[실패] {layer_name} 업로드 실패: {result.get('error', '알 수 없는 오류')}")

            # 업로드된 레이어 목록
            if st.session_state.uploaded_layers:
                st.markdown("**업로드된 레이어:**")
                for layer_name in st.session_state.uploaded_layers.keys():
                    st.caption(f"- {layer_name}")
        else:
            st.warning("GeoPandas가 설치되지 않아 Shapefile 업로드를 사용할 수 없습니다.")

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

# 지도 영역 (아래에 배치)
st.markdown("---")
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
        selected_zone_layers=st.session_state.selected_zone_layers,
        show_radius=show_radius,
        radius_meters=radius_meters
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
            width=None,  # 자동으로 컨테이너 너비에 맞춤
            height=700,
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

# WFS 데이터 조회 및 다운로드
st.markdown("---")
with st.expander("📥 공간 데이터 조회 및 다운로드", expanded=False):
    st.markdown("**현재 설정된 영역과 레이어의 데이터를 조회하여 Document Analysis에서 활용하거나 다운로드할 수 있습니다.**")

    # 세션 초기화 (다운로드된 데이터 저장용)
    if 'downloaded_geo_data' not in st.session_state:
        st.session_state.downloaded_geo_data = {}

    # 현재 설정 확인 및 표시
    st.markdown("### 현재 설정")
    col_info1, col_info2 = st.columns(2)

    with col_info1:
        st.info(f"""
        **중심 좌표**: ({st.session_state.cadastral_center_lat:.6f}, {st.session_state.cadastral_center_lon:.6f})
        **반경**: {radius_meters}m ({radius_meters/1000:.1f}km)
        """)

    with col_info2:
        selected_layers_info = st.session_state.selected_zone_layers if st.session_state.selected_zone_layers else []
        if selected_layers_info:
            layer_names = ', '.join([ZONE_LAYERS[k]['name'] for k in selected_layers_info[:3]])
            layer_names += '...' if len(selected_layers_info) > 3 else ''
        else:
            layer_names = '없음'
        st.info(f"""
        **선택된 레이어**: {len(selected_layers_info)}개
        {layer_names}
        """)

    # BBOX 계산 (반경 기반)
    import math
    center_lat = st.session_state.cadastral_center_lat
    center_lon = st.session_state.cadastral_center_lon
    lat_offset = radius_meters / 111000  # 위도 오프셋 (도 단위)
    lon_offset = radius_meters / (111000 * math.cos(math.radians(center_lat)))  # 경도 오프셋

    wfs_min_lat = center_lat - lat_offset
    wfs_max_lat = center_lat + lat_offset
    wfs_min_lon = center_lon - lon_offset
    wfs_max_lon = center_lon + lon_offset

    st.caption(f"조회 영역 (BBOX): ({wfs_min_lat:.6f}, {wfs_min_lon:.6f}) ~ ({wfs_max_lat:.6f}, {wfs_max_lon:.6f})")

    st.markdown("---")

    # Document Analysis 블록 연동 설정
    st.markdown("### Document Analysis 연동")
    save_for_analysis = st.checkbox(
        "조회 결과를 Document Analysis에 저장",
        value=True,
        help="조회한 데이터를 Document Analysis 페이지에서 활용할 수 있도록 저장합니다."
    )

    if save_for_analysis:
        st.caption("저장된 데이터는 Document Analysis에서 프로젝트 컨텍스트로 활용됩니다.")

    st.markdown("---")

    # 최대 피처 수 (고정값)
    wfs_max_features = 1000

    # 데이터 조회 버튼
    query_btn = st.button("선택된 레이어 데이터 조회", type="primary", use_container_width=True)

    if query_btn:
        if not st.session_state.selected_zone_layers:
            st.warning("[주의] 레이어를 선택해주세요.")
        else:
            bbox = (wfs_min_lon, wfs_min_lat, wfs_max_lon, wfs_max_lat)

            # 선택된 레이어들을 조회
            with st.spinner(f"{len(st.session_state.selected_zone_layers)}개 레이어 조회 중..."):
                from datetime import datetime
                success_count = 0
                fail_count = 0

                for zone_key in st.session_state.selected_zone_layers:
                    zone_info = ZONE_LAYERS[zone_key]
                    layer_code = zone_info['layer']
                    layer_name = f"{zone_info['name']} ({zone_info['category']})"

                    wfs_result = get_wfs_layer_data(layer_code, bbox, wfs_max_features)

                    if wfs_result:
                        features = wfs_result.get('features', [])

                        if features:
                            # Document Analysis에 저장
                            if save_for_analysis:
                                st.session_state.downloaded_geo_data[layer_name] = {
                                    'geojson': wfs_result,
                                    'layer_code': layer_code,
                                    'feature_count': len(features),
                                    'bbox': bbox,
                                    'downloaded_at': datetime.now().isoformat()
                                }
                            success_count += 1
                        else:
                            fail_count += 1
                    else:
                        fail_count += 1

                # 결과 표시
                if success_count > 0:
                    st.success(f" {success_count}개 레이어 조회 완료")
                    if save_for_analysis:
                        st.info("📁 Document Analysis에 저장되었습니다.")
                if fail_count > 0:
                    st.warning(f"[주의] {fail_count}개 레이어 조회 실패 또는 데이터 없음")


    # 저장된 데이터 목록 및 다운로드
    if st.session_state.downloaded_geo_data:
        st.markdown("---")
        st.markdown("### 저장된 공간 데이터")

        # 블록 연동 상태 초기화
        if 'block_spatial_data' not in st.session_state:
            st.session_state.block_spatial_data = {}

        linked_count = sum(1 for data in st.session_state.downloaded_geo_data.values() if data.get('linked_block'))
        total_features = sum(data.get('feature_count', 0) for data in st.session_state.downloaded_geo_data.values())
        st.caption(f"총 {len(st.session_state.downloaded_geo_data)}개 레이어 | {total_features}개 객체 | 블록 연동: {linked_count}개")

        # 전체 데이터 통합 다운로드
        st.markdown("**전체 데이터 다운로드**")
        st.info(f"""
        **다운로드 내용:**
        - 조회된 모든 레이어 데이터 ({len(st.session_state.downloaded_geo_data)}개 레이어)
        - 총 {total_features}개 공간 객체 (필지, 건물, 용도지역 등)
        - GeoJSON 형식 (좌표 정보 포함)
        - 각 객체의 속성 정보 (면적, 용도, 지가 등)
        """)

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            # 전체 GeoJSON 다운로드
            import json
            combined_data = {
                'type': 'FeatureCollection',
                'metadata': {
                    'bbox': bbox if 'bbox' in locals() else None,
                    'layers': list(st.session_state.downloaded_geo_data.keys()),
                    'downloaded_at': datetime.now().isoformat()
                },
                'features': []
            }
            for layer_name, data in st.session_state.downloaded_geo_data.items():
                geojson = data['geojson']
                for feature in geojson.get('features', []):
                    feature['properties']['_layer'] = layer_name
                    combined_data['features'].append(feature)

            json_str = json.dumps(combined_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 전체 GeoJSON 다운로드",
                data=json_str,
                file_name=f"spatial_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.geojson",
                mime="application/json",
                use_container_width=True
            )

        with col_dl2:
            # 전체 데이터 초기화
            if st.button("🗑️ 전체 삭제", use_container_width=True):
                st.session_state.downloaded_geo_data = {}
                st.rerun()

        # 데이터 통계 시각화
        with st.expander("📊 조회된 데이터 통계", expanded=False):
            st.caption("조회된 공간 데이터의 통계를 차트로 시각화합니다.")

            if st.button("📈 통계 분석 실행", use_container_width=True, key="run_viz_stats"):
                with st.spinner("통계 계산 중..."):
                    # 현재 지도 중심 좌표 사용
                    viz_lat = st.session_state.cadastral_center_lat
                    viz_lon = st.session_state.cadastral_center_lon
                    viz_radius = radius_meters  # 현재 설정된 반경 사용

                    extended_stats = calculate_radius_statistics_extended(
                        viz_lat, viz_lon,
                        st.session_state.downloaded_geo_data,
                        viz_radius
                    )
                    # 결과를 세션에 저장
                    st.session_state.geo_stats_result = extended_stats
                    st.session_state.geo_stats_radius = viz_radius

            # 저장된 통계 결과 표시
            if 'geo_stats_result' in st.session_state and st.session_state.geo_stats_result:
                extended_stats = st.session_state.geo_stats_result
                viz_radius = st.session_state.get('geo_stats_radius', 1000)

                if 'error' in extended_stats:
                    st.error(f"통계 계산 오류: {extended_stats['error']}")
                else:
                    # 레이어별 요약 먼저 표시
                    if extended_stats.get('by_layer'):
                        st.markdown("**레이어별 객체 수**")
                        layer_summary = []
                        for layer_name, layer_stat in extended_stats['by_layer'].items():
                            layer_summary.append({
                                '레이어': layer_name,
                                '객체 수': layer_stat.get('count', 0)
                            })
                        if layer_summary:
                            st.dataframe(pd.DataFrame(layer_summary), use_container_width=True, hide_index=True)

                    # 탭으로 시각화 분리
                    viz_tabs = st.tabs(["용도지역", "공시지가", "면적분포", "건물용도"])

                    with viz_tabs[0]:  # 용도지역 파이 차트
                        if extended_stats.get('zoning'):
                            try:
                                import plotly.express as px
                                zoning_data = list(extended_stats['zoning'].items())[:10]
                                if zoning_data:
                                    zoning_df = pd.DataFrame(zoning_data, columns=['용도', '개수'])
                                    fig = px.pie(zoning_df, names='용도', values='개수',
                                                title=f"반경 {viz_radius}m 내 용도지역 분포")
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.info("용도지역 데이터가 없습니다.")
                            except Exception as e:
                                st.warning(f"차트 생성 오류: {e}")
                        else:
                            st.info("용도지역 데이터가 없습니다.")

                    with viz_tabs[1]:  # 공시지가 히스토그램
                        if extended_stats.get('prices'):
                            try:
                                import plotly.express as px
                                fig = px.histogram(
                                    x=extended_stats['prices'],
                                    nbins=20,
                                    title=f"반경 {viz_radius}m 내 공시지가 분포",
                                    labels={'x': '공시지가 (원/㎡)', 'y': '필지 수'}
                                )
                                st.plotly_chart(fig, use_container_width=True)
                                col_stat1, col_stat2, col_stat3 = st.columns(3)
                                prices = extended_stats['prices']
                                with col_stat1:
                                    st.metric("평균", f"{int(sum(prices)/len(prices)):,}원")
                                with col_stat2:
                                    st.metric("최소", f"{int(min(prices)):,}원")
                                with col_stat3:
                                    st.metric("최대", f"{int(max(prices)):,}원")
                            except Exception as e:
                                st.warning(f"차트 생성 오류: {e}")
                        else:
                            st.info("공시지가 데이터가 없습니다.")

                    with viz_tabs[2]:  # 면적 분포
                        if extended_stats.get('areas'):
                            try:
                                import plotly.express as px
                                fig = px.histogram(
                                    x=extended_stats['areas'],
                                    nbins=20,
                                    title=f"반경 {viz_radius}m 내 면적 분포",
                                    labels={'x': '면적 (㎡)', 'y': '필지 수'}
                                )
                                st.plotly_chart(fig, use_container_width=True)
                                st.metric("총 면적", f"{sum(extended_stats['areas']):,.1f}㎡")
                            except Exception as e:
                                st.warning(f"차트 생성 오류: {e}")
                        else:
                            st.info("면적 데이터가 없습니다.")

                    with viz_tabs[3]:  # 건물용도 분포
                        if extended_stats.get('building_uses'):
                            try:
                                import plotly.express as px
                                bldg_data = list(extended_stats['building_uses'].items())[:10]
                                if bldg_data:
                                    bldg_df = pd.DataFrame(bldg_data, columns=['용도', '개수'])
                                    fig = px.bar(bldg_df, x='용도', y='개수',
                                                title=f"반경 {viz_radius}m 내 건물용도 분포 (상위 10개)")
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.info("건물용도 데이터가 없습니다.")
                            except Exception as e:
                                st.warning(f"차트 생성 오류: {e}")
                        else:
                            st.info("건물용도 데이터가 없습니다.")

                    # 통계 초기화 버튼
                    if st.button("통계 결과 지우기", key="clear_stats"):
                        st.session_state.geo_stats_result = None
                        st.rerun()
            else:
                st.info("'통계 분석 실행' 버튼을 클릭하여 데이터를 분석하세요.")

        # 다중 레이어 일괄 블록 연동
        with st.expander("🔗 다중 레이어 블록 일괄 연동", expanded=False):
            st.caption("여러 레이어를 한 번에 분석 블록에 연동합니다.")

            selected_blocks = st.session_state.get('selected_blocks', [])
            if not selected_blocks:
                st.warning("Document Analysis에서 먼저 분석 블록을 선택해주세요.")
            else:
                # 블록 이름 조회를 위한 lookup 생성
                try:
                    from prompt_processor import load_blocks, load_custom_blocks
                    example_blocks = load_blocks()
                    custom_blocks = load_custom_blocks()
                    all_blocks = example_blocks + custom_blocks
                    block_lookup = {
                        block.get('id'): block.get('name', block.get('id'))
                        for block in all_blocks
                        if isinstance(block, dict) and block.get('id')
                    }
                except Exception:
                    block_lookup = {}

                # 레이어 다중 선택
                layer_names = list(st.session_state.downloaded_geo_data.keys())
                selected_layers = st.multiselect(
                    "연동할 레이어 선택",
                    options=layer_names,
                    default=[],
                    key="batch_link_layers"
                )

                # 블록 선택 (한국어 이름 표시)
                def get_block_display_name(block_id):
                    name = block_lookup.get(block_id, block_id)
                    return f"{name}" if name != block_id else block_id

                target_block = st.selectbox(
                    "연동할 블록 선택",
                    options=selected_blocks,
                    format_func=get_block_display_name,
                    key="batch_link_block"
                )

                if selected_layers and target_block:
                    target_block_name = get_block_display_name(target_block)
                    if st.button("🔗 선택 레이어 일괄 연동", use_container_width=True, key="batch_link_btn"):
                        # 선택된 레이어들을 블록에 연동
                        combined_features = []
                        total_count = 0

                        for layer_name in selected_layers:
                            data = st.session_state.downloaded_geo_data[layer_name]
                            geojson = data['geojson']
                            for feature in geojson.get('features', []):
                                feature['properties']['_layer'] = layer_name
                                combined_features.append(feature)
                            total_count += data['feature_count']
                            data['linked_block'] = target_block
                            data['linked_block_name'] = target_block_name

                        # 블록에 통합 데이터 저장
                        st.session_state.block_spatial_data[target_block] = {
                            'layer_name': ', '.join(selected_layers),
                            'geojson': {
                                'type': 'FeatureCollection',
                                'features': combined_features
                            },
                            'feature_count': total_count,
                            'layers': selected_layers
                        }

                        st.success(f"'{target_block_name}' 블록에 {len(selected_layers)}개 레이어 ({total_count}개 객체) 연동 완료!")
                        st.rerun()

        st.markdown("---")

        # 레이어별 목록
        for layer_name, data in st.session_state.downloaded_geo_data.items():
            # 블록 연동 상태 표시
            linked_block = data.get('linked_block')
            linked_block_name = data.get('linked_block_name', linked_block)  # 한국어 이름 사용
            expander_label = f"{layer_name}"
            if linked_block:
                expander_label = f"✓ {layer_name} → {linked_block_name}"

            with st.expander(expander_label):
                col_info, col_actions = st.columns([2, 1])

                with col_info:
                    st.write(f"**객체 수**: {data['feature_count']}개")
                    st.caption(f"조회 시간: {data['downloaded_at'][:19]}")

                    # 블록 연동 상태
                    if linked_block:
                        st.success(f"연동: {linked_block_name}")

                with col_actions:
                    # 블록 연동 버튼
                    if st.button("블록 연동", key=f"link_{layer_name}", use_container_width=True):
                        st.session_state[f'show_block_selector_{layer_name}'] = True
                        st.rerun()

                    # 개별 다운로드
                    json_str = json.dumps(data['geojson'], ensure_ascii=False, indent=2)
                    st.download_button(
                        label="📥 다운로드",
                        data=json_str,
                        file_name=f"{layer_name.replace('/', '_')}.geojson",
                        mime="application/json",
                        key=f"dl_{layer_name}",
                        use_container_width=True
                    )

                    # 개별 삭제
                    if st.button("삭제", key=f"del_{layer_name}", use_container_width=True):
                        # 연동 해제
                        if linked_block and linked_block in st.session_state.block_spatial_data:
                            del st.session_state.block_spatial_data[linked_block]
                        del st.session_state.downloaded_geo_data[layer_name]
                        st.rerun()

                # 블록 선택 UI
                if st.session_state.get(f'show_block_selector_{layer_name}'):
                    st.markdown("---")
                    st.markdown("**연동할 블록 선택**")

                    # 선택된 블록 가져오기
                    selected_blocks_for_link = st.session_state.get('selected_blocks', [])

                    if not selected_blocks_for_link:
                        st.warning("Document Analysis에서 먼저 블록을 선택해주세요.")
                        if st.button("닫기", key=f"close_selector_{layer_name}"):
                            del st.session_state[f'show_block_selector_{layer_name}']
                            st.rerun()
                    else:
                        # 블록 이름 lookup (이미 위에서 정의됨)
                        try:
                            if 'block_lookup' not in locals():
                                from prompt_processor import load_blocks, load_custom_blocks
                                example_blocks = load_blocks()
                                custom_blocks = load_custom_blocks()
                                all_blocks = example_blocks + custom_blocks
                                block_lookup = {
                                    block.get('id'): block.get('name', block.get('id'))
                                    for block in all_blocks
                                    if isinstance(block, dict) and block.get('id')
                                }
                        except Exception:
                            block_lookup = {}

                        # 블록 옵션 (한국어 이름으로 표시)
                        block_display_options = {
                            "(연동 해제)": "(연동 해제)"
                        }
                        for bid in selected_blocks_for_link:
                            block_display_options[bid] = block_lookup.get(bid, bid)

                        selected_block = st.selectbox(
                            "블록 선택",
                            options=list(block_display_options.keys()),
                            format_func=lambda x: block_display_options.get(x, x),
                            key=f"block_select_{layer_name}",
                            help="이 공간 데이터를 특정 분석 블록과 연동합니다."
                        )

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("✅ 연동 확인", key=f"confirm_{layer_name}", use_container_width=True):
                                if selected_block == "(연동 해제)":
                                    # 연동 해제
                                    if linked_block and linked_block in st.session_state.block_spatial_data:
                                        del st.session_state.block_spatial_data[linked_block]
                                    data['linked_block'] = None
                                    data['linked_block_name'] = None
                                    st.success("연동이 해제되었습니다.")
                                else:
                                    # 블록 연동
                                    selected_block_name = block_display_options.get(selected_block, selected_block)
                                    st.session_state.block_spatial_data[selected_block] = {
                                        'layer_name': layer_name,
                                        'geojson': data['geojson'],
                                        'feature_count': data['feature_count']
                                    }
                                    data['linked_block'] = selected_block
                                    data['linked_block_name'] = selected_block_name
                                    st.success(f"'{selected_block_name}' 블록에 연동되었습니다!")

                                del st.session_state[f'show_block_selector_{layer_name}']
                                st.rerun()

                        with col_btn2:
                            if st.button("❌ 취소", key=f"cancel_{layer_name}", use_container_width=True):
                                del st.session_state[f'show_block_selector_{layer_name}']
                                st.rerun()

                # 데이터 미리보기
                records = []
                for feature in data['geojson'].get('features', [])[:10]:
                    props = feature.get('properties', {})
                    records.append(props)

                if records:
                    df_preview = pd.DataFrame(records)
                    st.dataframe(df_preview, use_container_width=True)
                    st.caption(f"(최대 10개 객체만 미리보기)")
    else:
        st.info("위에서 레이어를 선택하고 '데이터 조회' 버튼을 눌러주세요.")

    # 블록 연동 안내
    if st.session_state.get('block_spatial_data'):
        st.markdown("---")
        st.markdown("### 📌 Document Analysis 블록 연동 안내")
        st.info("""
        **연동된 공간 데이터를 Document Analysis에서 사용하는 방법:**

        1. **자동 컨텍스트 제공**: 연동된 블록이 실행될 때 공간 데이터가 자동으로 추가 컨텍스트로 제공됩니다.

        2. **데이터 접근**: `st.session_state.block_spatial_data[블록ID]` 로 접근 가능

        3. **포함 정보**:
           - `layer_name`: 레이어 이름
           - `geojson`: GeoJSON 형식 데이터
           - `feature_count`: 객체 개수

        현재 연동된 블록: {blocks}
        """.format(blocks=', '.join([f"**{k}**" for k in st.session_state.block_spatial_data.keys()])))

        # 연동 상태 테이블
        st.markdown("**연동 상태**")
        link_data = []
        for block_id, spatial_data in st.session_state.block_spatial_data.items():
            # 블록 이름 가져오기
            try:
                if 'block_lookup' not in locals():
                    from prompt_processor import load_blocks, load_custom_blocks
                    example_blocks = load_blocks()
                    custom_blocks = load_custom_blocks()
                    all_blocks = example_blocks + custom_blocks
                    block_lookup = {
                        block.get('id'): block.get('name', block.get('id'))
                        for block in all_blocks
                        if isinstance(block, dict) and block.get('id')
                    }
            except Exception:
                block_lookup = {}

            block_name = block_lookup.get(block_id, block_id)
            link_data.append({
                "블록": block_name,
                "레이어": spatial_data['layer_name'],
                "객체 수": spatial_data['feature_count']
            })
        st.dataframe(link_data, use_container_width=True)

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


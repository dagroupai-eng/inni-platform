from __future__ import annotations

import streamlit as st

# 페이지 설정 (반드시 최상단에 있어야 함)
st.set_page_config(
    page_title="지도 분석",
    page_icon=None,
    layout="wide"
)

# 개발 중 - 접근 차단
st.title("🚧 개발 중")
st.warning("**이 페이지는 현재 개발 중입니다.**")
st.info("""
이 기능은 아직 개발 중이며, 곧 사용할 수 있게 될 예정입니다.

**예정된 기능:**
- Shapefile 업로드 및 시각화
- V-world 레이어 로드
- 입지 후보지 시각화

곧 만나요! 🚀
""")
st.stop()

import pandas as pd
import sys
import os
import re
import glob
import fnmatch
from pathlib import Path

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

# 탭 분리: 샘플 데이터 vs Shapefile 업로드 vs 후보지 시각화
if GEO_MODULE_AVAILABLE:
    tab1, tab2, tab3 = st.tabs(["샘플 데이터 지도", "Shapefile 업로드", "입지 후보지 시각화"])
else:
    tab1 = st.container()
    tab2 = None
    tab3 = None

with tab1:
    # 지도 시각화 기능
    st.subheader("프로젝트 위치 지도")
    
    # 지도 타입 선택
    map_type = st.selectbox(
        "지도 타입 선택",
        ["서울 상세 지도", "전국 프로젝트 분포", "히트맵", "타임라인 지도"]
    )

    if map_type == "서울 상세 지도":
        # 서울 프로젝트 지도
        df_seoul = pd.DataFrame(seoul_projects)
        
        st.subheader("서울 지역 프로젝트 분포")
        st.map(df_seoul, size=20)
        
        # 프로젝트 정보 테이블
        st.subheader("프로젝트 상세 정보")
        st.dataframe(df_seoul[['name', 'type', 'size', 'status', 'budget', 'area']], use_container_width=True)

    elif map_type == "전국 프로젝트 분포":
        # 전국 도시별 프로젝트 분포
        df_cities = pd.DataFrame(cities_data)
        
        st.subheader("전국 도시별 프로젝트 분포")
        st.map(df_cities, size=30)
        
        # 도시 정보 테이블
        st.subheader("도시별 상세 정보")
        st.dataframe(df_cities, use_container_width=True)

    elif map_type == "히트맵":
        # 히트맵 생성 (예산 기준으로 크기 조정)
        df_seoul = pd.DataFrame(seoul_projects)
        
        # 예산에 따른 크기 계산 (최소 10, 최대 50)
        df_seoul['budget_size'] = ((df_seoul['budget'] - df_seoul['budget'].min()) / 
                                  (df_seoul['budget'].max() - df_seoul['budget'].min()) * 40 + 10)
        
        st.subheader("서울 지역 프로젝트 예산 히트맵")
        st.map(df_seoul, size='budget_size')
        
        # 예산 정보 테이블
        st.subheader("예산별 프로젝트 정보")
        st.dataframe(df_seoul[['name', 'budget', 'area', 'type']], use_container_width=True)

    elif map_type == "타임라인 지도":
        # 타임라인 지도 (진행 상태별)
        df_seoul = pd.DataFrame(seoul_projects)
        
        st.subheader("프로젝트 진행 상태별 분포")
        st.map(df_seoul, size=20)
        
        # 진행 상태별 통계
        st.subheader("진행 상태별 통계")
        status_counts = df_seoul['status'].value_counts()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("완료", len(df_seoul[df_seoul['status'] == '완료']))
        with col2:
            st.metric("진행중", len(df_seoul[df_seoul['status'] == '진행중']))
        with col3:
            st.metric("계획", len(df_seoul[df_seoul['status'] == '계획']))
        
        # 진행 상태 데이터 테이블
        st.subheader("진행 상태별 프로젝트 정보")
        st.dataframe(df_seoul[['name', 'status', 'start_date', 'end_date', 'type']], use_container_width=True)

# Shapefile 업로드 탭
if tab2 is not None:
    with tab2:
        st.header("도시공간데이터 Shapefile 업로드")
        st.markdown("**행정구역, 토지소유정보, 개별공시지가, 도로명주소 등 Shapefile을 업로드하여 지도에서 확인하세요.**")
        
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
        
        # 개발중 UI 표시
        st.markdown("---")
        st.warning("🚧 **이 기능은 현재 개발 중입니다.**")
        st.info("""
        Shapefile 업로드 후 레이어 관리 및 지도 시각화 기능은 곧 사용할 수 있게 될 예정입니다.
        
        **예정된 기능:**
        - V-world 레이어 로드
        - 업로드된 레이어 목록 표시
        - 통합 지도 시각화
        - 원본 데이터 미리보기
        
        곧 만나요! 🚀
        """)
        
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
        
        # 분석 결과에서 후보지 좌표 추출
        if st.session_state.get('analysis_results'):
            analysis_results = st.session_state.analysis_results
            
            # 입지 선정 분석 블록 찾기
            site_analysis = None
            for block_id, result in analysis_results.items():
                if 'site_selection' in block_id or '입지 선정' in str(result)[:200]:
                    site_analysis = result
                    break
            
            if site_analysis:
                st.success("✅ 입지 선정 분석 결과가 있습니다!")
                
                # 좌표를 추출하는 함수
                def extract_coordinates_from_text(text):
                    """텍스트에서 위경도 좌표를 추출"""
                    import re
                    coordinates = []
                    
                    # 다양한 패턴 시도
                    patterns = [
                        r'위도[:\s]*([\d.]+)[\s,]*,?[\s]*경도[:\s]*([\d.]+)',
                        r'경도[:\s]*([\d.]+)[\s,]*,?[\s]*위도[:\s]*([\d.]+)',
                        r'([\d.]+)[°\s]*N[,\s]+([\d.]+)[°\s]*E',
                        r'([\d.]+)[°\s]*북[,\s]+([\d.]+)[°\s]*동',
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        for match in matches:
                            try:
                                lat = float(match[0])
                                lon = float(match[1])
                                # 한국 좌표 범위 체크
                                if 33 <= lat <= 43 and 124 <= lon <= 132:
                                    coordinates.append({'lat': lat, 'lon': lon})
                            except:
                                continue
                    
                    return coordinates
                
                # 좌표 추출
                coordinates = extract_coordinates_from_text(site_analysis)
                
                if coordinates:
                    st.info(f"🎯 {len(coordinates)}개의 후보지가 발견되었습니다.")
                    
                    # 지도 표시 방식 선택
                    map_style = st.radio(
                        "지도 표시 방식",
                        ["고급 지도 (반경 5km 시설 표시)", "간단 지도 (후보지만 표시)"],
                        horizontal=True
                    )
                    
                    loader = GeoDataLoader()
                    
                    if map_style == "고급 지도 (반경 5km 시설 표시)":
                        try:
                            import streamlit_folium as st_folium
                            from geo_data_loader import create_candidate_map_with_facilities, filter_facilities_within_radius
                            
                            # 후보지 정보 구성 (점수 추출 시도)
                            candidate_sites = []
                            for idx, coord in enumerate(coordinates):
                                # 분석 결과에서 점수 추출 시도
                                score = 0
                                score_pattern = rf'후보지\s*{idx+1}[^0-9]*(\d+)점'
                                score_match = re.search(score_pattern, site_analysis)
                                if score_match:
                                    try:
                                        score = int(score_match.group(1))
                                    except:
                                        pass
                                
                                candidate_sites.append({
                                    'name': f'후보지 {idx+1}',
                                    'lat': coord['lat'],
                                    'lon': coord['lon'],
                                    'score': score
                                })
                            
                            # 시설 데이터 준비 (업로드된 레이어 중 시설 관련 레이어 사용)
                            facilities_gdf = None
                            if st.session_state.get('geo_layers'):
                                # 시설 관련 레이어 찾기
                                for layer_name, layer_data in st.session_state.geo_layers.items():
                                    if any(keyword in layer_name for keyword in ['시설', '건물', 'facility', 'building']):
                                        facilities_gdf = layer_data['gdf']
                                        st.info(f"💡 '{layer_name}' 레이어를 시설 데이터로 사용합니다.")
                                        break
                            
                            # 반경 설정
                            radius_km = st.slider("반경 설정 (km)", min_value=1.0, max_value=10.0, value=5.0, step=0.5)
                            
                            # 고급 지도 생성
                            folium_map = create_candidate_map_with_facilities(
                                candidate_sites, 
                                facilities_gdf, 
                                radius_km=radius_km
                            )
                            
                            if folium_map:
                                st_folium.st_folium(folium_map, width=1200, height=600)
                                
                                # 반경 내 시설 통계
                                if facilities_gdf is not None:
                                    st.subheader("📊 반경 내 시설 통계")
                                    col1, col2, col3 = st.columns(3)
                                    
                                    for idx, site in enumerate(candidate_sites):
                                        nearby = filter_facilities_within_radius(
                                            site['lat'], site['lon'], radius_km, facilities_gdf
                                        )
                                        with col1 if idx % 3 == 0 else col2 if idx % 3 == 1 else col3:
                                            st.metric(f"{site['name']}", f"{len(nearby)}개 시설")
                            else:
                                st.warning("⚠️ 고급 지도를 생성할 수 없습니다. 간단 지도를 사용하세요.")
                                map_style = "간단 지도 (후보지만 표시)"
                        
                        except ImportError:
                            st.warning("⚠️ streamlit-folium 패키지가 설치되지 않았습니다. 간단 지도를 사용합니다.")
                            st.info("💡 고급 지도를 사용하려면: `pip install streamlit-folium folium`")
                            map_style = "간단 지도 (후보지만 표시)"
                    
                    if map_style == "간단 지도 (후보지만 표시)":
                        # 기존 방식: 간단한 지도
                        df_candidates = pd.DataFrame(coordinates)
                        df_candidates['name'] = [f'후보지 {i+1}' for i in range(len(coordinates))]
                        
                        st.map(df_candidates, size=20)
                        st.info("💡 반경 5km 시설을 보려면 '고급 지도' 옵션을 선택하세요.")
                    
                    # 좌표 정보 표시
                    st.subheader("📍 후보지 좌표 정보")
                    for idx, coord in enumerate(coordinates):
                        st.write(f"**후보지 {idx+1}**: 위도 {coord['lat']:.6f}, 경도 {coord['lon']:.6f}")
                    
                    # 지형 정보 안내
                    st.subheader("🗻 지형 정보")
                    st.info("""
                    **지형 정보 활용 방법:**
                    - 도시공간데이터포털에서 'DEM(수치지형도)' 또는 '고도 정보' 레이어를 다운로드하여 Shapefile 업로드 탭에 업로드하세요.
                    - 업로드된 지형 데이터는 후보지 주변의 고도 정보를 제공합니다.
                    - 고급 지도에서 지형 레이어를 활성화하여 확인할 수 있습니다.
                    """)
                    
                    # 원본 분석 결과 표시
                    st.subheader("📊 전체 분석 결과")
                    st.markdown(site_analysis)
                else:
                    st.warning("⚠️ 분석 결과에서 좌표를 찾을 수 없습니다.")
                    st.info("💡 AI 분석 결과가 위경도 좌표를 포함하고 있는지 확인하세요.")
                    st.markdown("**예시 형식:** 위도 37.1234, 경도 129.5678")
                    
                    # 전체 분석 결과 표시
                    st.subheader("📊 전체 분석 결과")
                    with st.expander("분석 결과 보기"):
                        st.markdown(site_analysis)
            else:
                st.warning("⚠️ 입지 선정 분석 결과가 없습니다.")
                st.info("Document Analysis 페이지에서 '입지 선정 분석' 블록을 실행해주세요.")
                st.info("💡 왼쪽 사이드바에서 '1_📄_Document_Analysis'를 클릭하여 이동하세요")
        else:
            st.warning("⚠️ 분석 결과가 없습니다.")
            st.info("Document Analysis 페이지에서 분석을 먼저 실행해주세요.")
            st.info("💡 왼쪽 사이드바에서 '1_📄_Document_Analysis'를 클릭하여 이동하세요")

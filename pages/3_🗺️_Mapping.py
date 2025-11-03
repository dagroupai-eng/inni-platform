import streamlit as st

# 페이지 설정 (반드시 최상단에 있어야 함)
st.set_page_config(
    page_title="지도 분석",
    page_icon=None,
    layout="wide"
)

import pandas as pd
import sys
import os

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
        
        # 통합 지도 시각화
        if st.session_state.geo_layers:
            st.markdown("---")
            st.subheader("🗺️ 통합 지도 시각화")
            
            # 모든 레이어의 중심점을 하나의 데이터프레임으로 합침
            loader = GeoDataLoader()
            all_coords = []
            for layer_name, layer_data in st.session_state.geo_layers.items():
                df_for_map = loader.gdf_to_dataframe_for_map(layer_data['gdf'])
                if not df_for_map.empty:
                    df_for_map['layer'] = layer_name
                    all_coords.append(df_for_map.head(500))  # 최대 500개만 표시
            
            if all_coords:
                combined_df = pd.concat(all_coords, ignore_index=True)
                st.map(combined_df, size=10)
                
                # 원본 데이터 미리보기
                with st.expander("📋 원본 데이터 미리보기"):
                    for layer_name, layer_data in list(st.session_state.geo_layers.items())[:3]:  # 최대 3개 레이어만
                        st.markdown(f"**{layer_name}**")
                        st.dataframe(layer_data['gdf'].head(50), use_container_width=True)
            else:
                st.warning("⚠️ 지도에 표시할 수 있는 좌표 데이터가 없습니다.")
        
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
            site_analysis = st.session_state.analysis_results.get('site_selection_analysis')
            
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
                    
                    # 지도에 표시
                    loader = GeoDataLoader()
                    df_candidates = pd.DataFrame(coordinates)
                    df_candidates['name'] = [f'후보지 {i+1}' for i in range(len(coordinates))]
                    
                    st.map(df_candidates, size=20)
                    
                    # 좌표 정보 표시
                    st.subheader("📍 후보지 좌표 정보")
                    for idx, coord in enumerate(coordinates):
                        st.write(f"**후보지 {idx+1}**: 위도 {coord['lat']:.6f}, 경도 {coord['lon']:.6f}")
                    
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

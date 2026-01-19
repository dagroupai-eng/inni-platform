#확인수정
#확인수정

import streamlit as st
import pandas as pd
try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    gpd = None

try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    folium = None
try:
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
import os
import tempfile
try:
    from urban_data_collector import UrbanDataCollector
    URBAN_DATA_COLLECTOR_AVAILABLE = True
except ImportError:
    URBAN_DATA_COLLECTOR_AVAILABLE = False
import json

# 페이지 설정
st.set_page_config(
    page_title="사이트 데이터 수집",
    page_icon="🏙️",
    layout="wide"
)

# 제목
st.title("🏙️ 사이트 데이터 자동 수집")
st.markdown("**좌표 입력으로 주변 도시 데이터 자동 수집**")

# geopandas 체크
if not GEOPANDAS_AVAILABLE:
    st.error("⚠️ geopandas가 설치되지 않았습니다.")
    st.info("""
    **설치 방법:**
    
    1. **conda 사용 (권장):**
       ```
       conda install -c conda-forge geopandas
       ```
    
    2. **pip 사용:**
       ```
       pip install geopandas shapely pyproj
       ```
    
    3. **install.bat 실행:**
       프로젝트 루트에서 `install.bat`을 실행하면 자동으로 설치됩니다.
    """)
    st.stop()

# Session state 초기화
if 'collected_data' not in st.session_state:
    st.session_state.collected_data = None
if 'collection_status' not in st.session_state:
    st.session_state.collection_status = ""

# 사이드바 - 좌표 입력
with st.sidebar:
    st.header("📍 좌표 입력")
    
    # 좌표 직접 입력
    st.subheader("좌표 직접 입력")
    lat = st.number_input("위도 (Latitude)", value=37.5665, format="%.6f")
    lon = st.number_input("경도 (Longitude)", value=126.9780, format="%.6f")
    radius = st.number_input("수집 반경 (미터)", value=1000, min_value=100, max_value=5000)
    site_id = st.text_input("사이트 ID", value="S001")
    
    coordinates = [{"lat": lat, "lon": lon, "radius": radius, "site_id": site_id}]
    
    # 데이터 수집 설정
    st.header("⚙️ 수집 설정")
    
    collect_osm = st.checkbox("OSM POI 수집", value=True)

# 메인 컨텐츠
if coordinates:
    st.header("🚀 데이터 수집 실행")
    
    if st.button("데이터 수집 시작", type="primary"):
        # 데이터 수집기 초기화
        if not URBAN_DATA_COLLECTOR_AVAILABLE:
            st.error("⚠️ UrbanDataCollector 모듈이 설치되지 않았습니다.")
            st.info("이 기능을 사용하려면 urban_data_collector.py 파일이 필요합니다.")
            st.stop()
        
        collector = UrbanDataCollector()
        
        # 진행 상황 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_collected_data = {}
        
        for i, coord in enumerate(coordinates):
            status_text.text(f"수집 중: {coord['site_id']} ({i+1}/{len(coordinates)})")
            
            try:
                # 데이터 수집 실행
                collected_data = collector.collect_site_data(
                    lat=coord['lat'],
                    lon=coord['lon'],
                    radius_m=coord['radius'],
                    site_id=coord['site_id']
                )
                
                all_collected_data[coord['site_id']] = collected_data
                st.success(f"✅ {coord['site_id']} 수집 완료")
                
            except Exception as e:
                st.error(f"❌ {coord['site_id']} 수집 실패: {e}")
                continue
            
            # 진행률 업데이트
            progress_bar.progress((i + 1) / len(coordinates))
        
        # 수집 완료
        status_text.text("✅ 모든 데이터 수집이 완료되었습니다!")
        progress_bar.empty()
        
        # 결과를 세션에 저장
        st.session_state.collected_data = all_collected_data
        
        # 결과 요약 표시
        st.subheader("📊 수집 결과 요약")
        
        summary_data = []
        for site_id, data in all_collected_data.items():
            summary_data.append({
                "사이트 ID": site_id,
                "위치": f"({data['site_info']['lat']:.4f}, {data['site_info']['lon']:.4f})",
                "OSM POI": len(data.get('osm_poi', [])),
                "V-World 용도지역": len(data.get('vworld_zoning', [])),
                "KOSIS 통계": len(data.get('kosis_stats', [])),
                "공공시설": len(data.get('public_facilities', []))
            })
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)

# 필터링 함수 정의
MAX_DISPLAY_ROWS = 500  # 최대 표시 행 수 (더 작게 조정)
MAX_MAP_FEATURES = 100  # 지도에 표시할 최대 피처 수 (더 작게 조정)
MAX_MAP_POIS = 100  # 지도에 표시할 최대 POI 수 (더 작게 조정)

# V-World 레이어 한국어 이름 매핑 (상수로 한 번만 정의)
VWORLD_KOREAN_NAMES = {
    'LT_C_UQ112': '관리지역',
    'LT_C_UQ113': '농림지역',
    'LT_C_UQ111': '도시지역',
    'LT_C_UQ114': '자연환경보전지역',
    'LT_C_UQ129': '개발진흥지구',
    'LT_C_UQ121': '경관지구',
    'LT_C_UQ123': '고도지구',
    'LT_C_UQ122': '미관지구',
    'LT_C_UQ125': '방재지구',
    'LT_C_UQ124': '방화지구',
    'LT_C_UQ126': '보존지구',
    'LT_C_UQ127': '시설보호지구',
    'LT_C_UQ128': '취락지구',
    'LT_C_UQ130': '특정용도제한지구',
    'LT_C_UD801': '개발제한구역',
    'LT_C_UQ141': '국토계획구역',
    'LT_C_UQ162': '도시자연공원구역',
    'LT_C_UM000': '가축사육제한구역',
    'LT_C_UO601': '관광지',
    'LT_C_UD610': '국민임대주택',
    'LT_C_UP401': '급경사재해예방지역',
    'LT_C_UM301': '대기환경규제지역',
    'LT_C_UF901': '백두대간보호지역',
    'LT_C_UH701': '벤처기업육성지역',
    'LT_C_UD620': '보금자리주택',
    'LT_C_UF151': '산림보호구역',
    'LT_C_UM901': '습지보호지역',
    'LT_C_UB901': '시장정비구역',
    'LT_C_UM221': '야생동식물보호',
    'LT_C_UJ401': '온천지구',
    'LT_C_UH501': '유통단지',
    'LT_C_UH402': '자유무역지역지정및운영',
    'LT_C_UD601': '주거환경개선지구도',
    'LT_C_UO101': '학교환경위생정화구역',
    'LT_C_LHZONE': '사업지구경계도',
    'LT_C_LHBLPN': '토지이용계획도',
    'LT_C_UPISUQ153': '도시계획(공간시설)',
    'LT_C_UPISUQ155': '도시계획(공공문화체육시설)',
    'LT_C_UPISUQ152': '도시계획(교통시설)',
    'LT_C_UPISUQ159': '도시계획(기타기반시설)',
    'LT_C_UPISUQ151': '도시계획(도로)',
    'LT_C_UPISUQ156': '도시계획(방재시설)',
    'LT_C_UPISUQ157': '도시계획(보건위생시설)',
    'LT_C_UPISUQ154': '도시계획(유통공급시설)',
    'LT_C_UPISUQ158': '도시계획(환경기초시설)',
    'LT_C_UPISUQ161': '지구단위계획',
    'LT_C_UPISUQ171': '개발행위허가제한지역',
    'LT_C_UPISUQ174': '개발행위허가필지',
    'LT_C_UPISUQ173': '기반시설부담구역',
    'LT_C_UPISUQ175': '토지거래계약에관한허가구역',
    'LT_C_SPBD': '도로명주소건물',
    'LT_L_SPRD': '도로명주소도로',
    'LT_C_ADSIDO': '광역시도',
    'LT_C_ADRI': '리',
    'LT_C_ADSIGG': '시군구',
    'LT_C_ADEMD': '읍면동',
    'LT_P_NSNMSSITENM': '국가지명',
    'LP_PA_CBND_BUBUN': '연속지적도(부분)',
    'LP_PA_CBND_BONBUN': '연속지적도(본번)',
    'LT_C_KFDRSSIGUGRADE': '산불위험예측지도',
    'LT_C_UP201': '재해위험지구',
    'LT_P_EDRSE002': '지진대피소',
    'LT_P_ETQSHELTER': '지진해일대피소',
    'LT_P_MGPRTFD': '기타보호시설',
    'LT_P_MGPRTFB': '노인복지시설',
    'LT_P_MGPRTFC': '아동복지시설',
    'LT_P_MGPRTFA': '아동안전지킴이집',
    'LT_C_TDWAREA': '보행우선구역',
    'LT_C_USFSFFB': '소방서관할구역',
    'LT_C_UO301': '문화재보호도',
    'LT_C_UO501': '전통사찰보존',
    'LT_L_FRSTCLIMB': '등산로',
    'LT_P_CLIMBALL': '등산로(포인트)',
    'LT_L_TRKROAD': '산책로',
    'LT_P_TRKROAD': '산책로(포인트)',
    'LT_L_BYCLINK': '자전거길',
    'LT_P_BYCRACKS': '자전거보관소',
    'LT_P_MOCTNODE': '교통노드',
    'LT_L_MOCTLINK': '교통링크',
    'LT_L_AISROUTEU': '제한고도',
    'LT_L_AISPATH': '항공로',
    'LT_C_AISALTC': '경계구역',
    'LT_C_AISRFLC': '공중급유구역',
    'LT_C_AISACMC': '공중전투기동훈련장',
    'LT_C_AISCTRC': '관제권',
    'LT_C_AISMOAC': '군작전구역',
    'LT_C_AISADZC': '방공식별구역',
    'LT_C_AISPRHC': '비행금지구역',
    'LT_C_AISATZC': '비행장교통구역',
    'LT_C_AISFIRC': '비행정보구역',
    'LT_C_AISRESC': '비행제한구역',
    'LT_C_AISDNGC': '위험구역',
    'LT_C_AISTMAC': '접근관제구역',
    'LT_C_AISCATC': '훈련구역',
    'LT_L_AISSEARCHL': '수색비행장비행구역(라인)',
    'LT_P_AISSEARCHP': '수색비행장비행구역(포인트)',
    'LT_L_AISVFRPATH': '시계비행로',
    'LT_P_AISVFRPATH': '시계비행로(포인트)',
    'LT_L_AISCORRID_YS': '한강회랑(여의도)',
    'LT_L_AISCORRID_GJ': '한강회랑(광진)',
    'LT_P_AISCORRID_YS': '한강회랑(여의도 포인트)',
    'LT_P_AISCORRID_GJ': '한강회랑(광진 포인트)',
    'LT_P_AISHCSTRIP': '헬기장',
    'LT_P_UTISCCTV': '교통CCTV',
    'LT_C_DAMDAN': '단지경계',
    'LT_C_DAMYOJ': '단지시설용지',
    'LT_C_DAMYOD': '단지용도지역',
    'LT_C_DAMYUCH': '단지유치업종',
    'LT_C_ASITSOILDRA': '배수등급',
    'LT_C_ASITDEEPSOIL': '심토토성',
    'LT_C_ASITSOILDEP': '유효토심',
    'LT_C_ASITSURSTON': '자갈함량',
    'LT_P_SGISGOLF': '골프장현황도',
    'LT_P_SGISGWCHG': '지하수측정망(오염우려지역)',
    'LT_C_WKMBBSN': '대권역',
    'LT_C_WKMMBSN': '중권역',
    'LT_C_WKMSBSN': '표준권역',
    'LT_C_WKMSTRM': '하천망',
    'LT_P_WEISPLAFACE': '기타공동처리시설',
    'LT_P_WEISPLAFACA': '농공단지처리시설',
    'LT_P_WEISPLAFACV': '마을하수도',
    'LT_P_WEISPLAFACL': '매립장침출수처리시설',
    'LT_C_UM710': '상수원보호',
    'LT_P_WEISTACCON': '수생태계조사지점',
    'LT_P_WEISSITETB': '수질자동측정망측정지점',
    'LT_P_WEISSITEME': '수질측정망공단배수지점',
    'LT_P_WEISSITEMD': '수질측정망농업용수지점',
    'LT_P_WEISSITEMF': '수질측정망도시관류지점',
    'LT_P_WEISSITEMA': '수질측정망하천수지점',
    'LT_P_WEISSITEMB': '수질측정망호소수지점',
    'LT_P_WEISPLAFACS': '축산폐수공공처리시설',
    'LT_P_WEISPLAFACW': '하수종말처리시설',
    'LT_L_GIMSFAULT': '단층',
    'LT_C_GIMSHYDRO': '수문지질단위',
    'LT_C_GIMSSTIFF': '수질다이어그램',
    'LT_L_GIMSEC': '전기전도도',
    'LT_C_GIMSLINEA': '지질구조밀도',
    'LT_L_GIMSLINEA': '지질구조선',
    'LT_L_GIMSDEPTH': '지하수등수심선',
    'LT_L_GIMSPOTEN': '지하수등수위선',
    'LT_L_GIMSDIREC': '지하수유동방향',
    'LT_C_GIMSSCS': '토양도',
    'LT_P_RIFCT': '수리시설',
    'LT_C_RIRSV': '저수지',
    'LT_C_AGRIXUE101': '농업진흥지역도',
    'LT_C_AGRIXUE102': '영농여건불리농지도',
    'LT_C_FLISFK300': '산지(보안림)',
    'LT_C_FLISFK100': '산지(자연휴양림)',
    'LT_C_FLISFK200': '산지(채종림)',
    'LT_C_UF602': '임업 및 산촌 진흥권역',
    'LT_C_FSDIFRSTS': '산림입지도',
    'LT_C_WGISPLTALK': '개발유도연안',
    'LT_C_WGISPLROW': '개발조정연안',
    'LT_C_WGISPLUSE': '이용연안',
    'LT_C_WGISPLABS': '절대보전연안',
    'LT_C_WGISPLJUN': '준보전연안',
    'LT_C_WGISRERESH': '공유수면매립3차수요조사',
    'LT_C_WGISREPLAN': '공유수면매립기본계획',
    'LT_C_WGISRECOMP': '공유수면매립준공',
    'LT_C_WGISIEGUG': '국가산업단지',
    'LT_C_WGISIENONG': '농공단지',
    'LT_C_WGISIEILBAN': '일반산업단지',
    'LT_C_WGISIEDOSI': '첨단산업단지',
    'LT_C_WGISFMGUL': '굴양식장',
    'LT_C_WGISFMKIM': '김양식장',
    'LT_C_WGISFMDSM': '다시마양식장',
    'LT_C_WGISFMMYK': '미역양식장',
    'LT_C_WGISFMFISH': '어류양식장',
    'LT_C_WGISFMJBOK': '전복양식장',
    'LT_C_WGISTPNEWP': '무역신항만',
    'LT_C_WGISTPLAND': '무역항육상구역',
    'LT_C_WGISTPSEA': '무역항해상구역',
    'LT_C_WGISCPLAND': '연안항육상구역',
    'LT_C_WGISCPSEA': '연안항해상구역',
    'LT_C_WGISARECO': '생태계경관보전지역',
    'LT_C_WGISARFISHER': '수산자원보호구역',
    'LT_C_WGISARWET': '습지보호구역',
    'LT_C_UMA100': '국립공원용도지구',
    'LT_C_WGISNPGUG': '국립자연공원',
    'LT_C_WGISNPGUN': '군립자연공원',
    'LT_C_WGISNPDO': '도립자연공원',
    'LT_C_CDFRS100FRQ': '해안침수(100년빈도)',
    'LT_C_CDFRS150FRQ': '해안침수(150년빈도)',
    'LT_C_CDFRS200FRQ': '해안침수(200년빈도)',
    'LT_C_CDFRS050FRQ': '해안침수(50년빈도)',
    'LT_C_CDFRSMAXFRQ': '해안침수(최대범람)',
    'LT_C_TFISTIDAF': '갯벌정보',
    'LT_P_TFISTIDAFP': '갯벌정보(포인트)',
    'LT_C_TFISMPA': '해양보호구역',
    'LT_L_TOISDEPCNTAH': '해안선',
    # 기존 용도지역 관련
    'LT_C_UDPG': '용도구역',
    'LT_C_UDDI': '용도지구',
    'LT_C_UPISU': '용도지역',
    # 구체적인 용도지역 코드들
    'LT_P_DGMUSEUMART': '박물관/미술관지역',
    'LT_P_DGPARK': '공원지역',
    'LT_P_DGCOMMERCIAL': '상업지역',
    'LT_P_DGRESIDENTIAL': '주거지역',
    'LT_P_DGINDUSTRIAL': '공업지역',
    'LT_P_DGGREEN': '녹지지역',
    'LT_P_DGAGRICULTURAL': '농업지역',
    'LT_P_DGFOREST': '산림지역',
    'LT_P_DGWATER': '수역지역',
    'LT_P_DGROAD': '도로지역',
    'LT_P_DGPUBLIC': '공공시설지역',
    'LT_P_DGRELIGIOUS': '종교지역',
    'LT_P_DGEDUCATIONAL': '교육지역',
    'LT_P_DGMEDICAL': '의료지역',
    'LT_P_DGTRANSPORT': '교통지역',
    'LT_P_DGWAREHOUSE': '창고지역',
    'LT_P_DGUTILITY': '공용시설지역',
    'LT_P_DGCEMETERY': '묘지지역',
    'LT_P_DGOTHER': '기타지역'
}

# POI 한국어 이름 매핑 (상수로 한 번만 정의)
KOREAN_POI_NAMES = {
    'amenity:hospital': '병원',
    'amenity:school': '학교', 
    'amenity:university': '대학교',
    'amenity:pharmacy': '약국',
    'amenity:clinic': '의원',
    'public_transport:station': '대중교통역',
    'highway:bus_stop': '버스정류장',
    'shop:supermarket': '대형마트',
    'shop:convenience': '편의점',
    'leisure:park': '공원',
    'tourism:hotel': '호텔',
    'amenity:restaurant': '식당',
    'amenity:cafe': '카페'
}

def estimate_data_size_mb(data):
    """데이터 크기를 대략적으로 추정 (MB)"""
    try:
        import sys
        if hasattr(data, '__sizeof__'):
            size_bytes = sys.getsizeof(data)
            # DataFrame이나 GeoDataFrame의 경우 내부 데이터도 포함
            if hasattr(data, 'memory_usage'):
                size_bytes += data.memory_usage(deep=True).sum()
            return size_bytes / (1024 * 1024)  # MB로 변환
        return 0
    except:
        return 0

def filter_geodataframe_by_coordinate(gdf, center_lat, center_lon, radius_meters):
    """좌표와 반경을 기준으로 GeoDataFrame 필터링"""
    if gdf.empty or 'geometry' not in gdf.columns:
        return gdf
    
    try:
        from shapely.geometry import Point
        # 미터를 도 단위로 변환 (대략적인 변환: 1도 ≈ 111,320m)
        radius_degrees = radius_meters / 111320.0
        center_point = Point(center_lon, center_lat)
        buffer = center_point.buffer(radius_degrees)
        
        # 반경 내에 있는 피처만 필터링
        filtered_gdf = gdf[gdf.geometry.within(buffer) | gdf.geometry.intersects(buffer)]
        
        # 대용량 데이터는 샘플링
        if len(filtered_gdf) > MAX_DISPLAY_ROWS:
            filtered_gdf = filtered_gdf.sample(n=MAX_DISPLAY_ROWS, random_state=42)
        
        return filtered_gdf
    except Exception as e:
        st.warning(f"필터링 중 오류 발생: {e}. 전체 데이터를 표시합니다.")
        return gdf

def filter_dataframe_by_distance(df, center_lat, center_lon, radius_meters, lat_col='lat', lon_col='lon'):
    """DataFrame에서 좌표 기반으로 반경 내 데이터만 필터링"""
    if df.empty:
        return df
    
    try:
        import math
        # lat, lon 컬럼이 있는 경우만 필터링
        if lat_col in df.columns and lon_col in df.columns:
            def calculate_distance(row):
                try:
                    lat1, lon1 = math.radians(center_lat), math.radians(center_lon)
                    lat2, lon2 = math.radians(row[lat_col]), math.radians(row[lon_col])
                    dlat, dlon = lat2 - lat1, lon2 - lon1
                    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                    c = 2 * math.asin(math.sqrt(a))
                    distance = 6371000 * c  # 지구 반지름(미터)
                    return distance <= radius_meters
                except:
                    return False
            
            filtered_df = df[df.apply(calculate_distance, axis=1)]
            
            # 대용량 데이터는 샘플링
            if len(filtered_df) > MAX_DISPLAY_ROWS:
                filtered_df = filtered_df.sample(n=MAX_DISPLAY_ROWS, random_state=42)
            
            return filtered_df
        else:
            # 좌표 컬럼이 없으면 샘플링만 적용
            if len(df) > MAX_DISPLAY_ROWS:
                return df.sample(n=MAX_DISPLAY_ROWS, random_state=42)
            return df
    except Exception as e:
        st.warning(f"필터링 중 오류 발생: {e}. 전체 데이터를 표시합니다.")
        return df

# 수집 결과 표시
if st.session_state.collected_data:
    st.header("📋 수집 결과")
    
    # 사이트 선택
    site_ids = list(st.session_state.collected_data.keys())
    selected_site = st.selectbox("📍 지역 선택", ["전체 보기"] + site_ids)
    
    if selected_site and selected_site != "전체 보기":
        # 지역 선택 후에만 데이터 로드
        data = st.session_state.collected_data[selected_site]
        
        # 선택한 사이트의 좌표 정보
        site_info = data.get('site_info', {})
        center_lat = site_info.get('lat', 0)
        center_lon = site_info.get('lon', 0)
        radius_m = site_info.get('radius_m', 1000)
        
        # 좌표 정보 표시
        st.info(f"📍 선택 지역: {selected_site} | 위치: ({center_lat:.6f}, {center_lon:.6f}) | 반경: {radius_m}m")
        
        # 데이터 크기 사전 체크 및 경고
        total_size = 0
        for key in ['osm_poi', 'vworld_zoning', 'kosis_stats', 'public_facilities']:
            if key in data and not (isinstance(data[key], pd.DataFrame) and data[key].empty):
                if isinstance(data[key], gpd.GeoDataFrame):
                    total_size += estimate_data_size_mb(data[key])
                elif isinstance(data[key], pd.DataFrame):
                    total_size += estimate_data_size_mb(data[key])
        
        if total_size > 50:
            st.warning(f"⚠️ 선택한 지역의 데이터 크기가 큽니다 ({total_size:.1f} MB). 성능을 위해 데이터가 자동으로 샘플링됩니다.")
        
        # OSM POI 결과 표시
        st.subheader("🏥 OSM POI")
        osm_df = data.get('osm_poi', pd.DataFrame())
        if not osm_df.empty:
            # 반경 내 데이터만 필터링
            filtered_osm = filter_dataframe_by_distance(
                osm_df, center_lat, center_lon, radius_m
            )
            
            # 필터링 결과 정보 표시
            total_count = len(osm_df)
            filtered_count = len(filtered_osm)
            if total_count > filtered_count:
                if filtered_count > MAX_DISPLAY_ROWS:
                    st.warning(f"⚠️ 전체 {total_count:,}개 중 반경 내 {filtered_count:,}개 발견. 성능을 위해 {MAX_DISPLAY_ROWS:,}개만 표시합니다.")
                else:
                    st.success(f"✅ 전체 {total_count:,}개 중 반경 내 {filtered_count:,}개 표시 중")
            else:
                if filtered_count > MAX_DISPLAY_ROWS:
                    st.warning(f"⚠️ 총 {total_count:,}개 데이터 중 성능을 위해 {MAX_DISPLAY_ROWS:,}개만 표시합니다.")
                else:
                    st.info(f"📊 총 {total_count:,}개 데이터 표시 중")
            # POI 타입별 통계 (한국어 포함)
            if 'poi_type' in filtered_osm.columns:
                poi_stats = filtered_osm['poi_type'].value_counts()
                poi_stats_korean = {}
                for poi_type, count in poi_stats.items():
                    korean_name = KOREAN_POI_NAMES.get(poi_type, poi_type)
                    poi_stats_korean[f"{korean_name} ({poi_type})"] = count
                
                st.bar_chart(poi_stats_korean)
            
            # POI 데이터 표시 (한국어 용어 추가)
            display_df = filtered_osm.copy()
            if 'poi_type' in display_df.columns:
                display_df['한국어_타입'] = display_df['poi_type'].map(KOREAN_POI_NAMES).fillna(display_df['poi_type'])
            st.dataframe(display_df, use_container_width=True)
            
            # OSM POI 지도 표시 (선택적)
            show_poi_map = st.checkbox("🗺️ POI 지도 표시 (대용량 데이터의 경우 느릴 수 있음)", value=False, key="show_poi_map")
            
            if show_poi_map:
                st.subheader("🗺️ OSM POI 지도")
                try:
                    # Folium 지도 생성
                    m = folium.Map(
                        location=[data['site_info']['lat'], data['site_info']['lon']],
                        zoom_start=15
                    )
                    
                    # 사이트 마커
                    folium.Marker(
                        [data['site_info']['lat'], data['site_info']['lon']],
                        popup=f"사이트: {selected_site}",
                        icon=folium.Icon(color='red', icon='star')
                    ).add_to(m)
                    
                    # 반경 원
                    folium.Circle(
                        [data['site_info']['lat'], data['site_info']['lon']],
                        radius=data['site_info']['radius_m'],
                        popup=f"수집 반경: {data['site_info']['radius_m']}m",
                        color='blue',
                        fill=False,
                        weight=2
                    ).add_to(m)
                    
                    # POI 타입별 색상 설정 (확장된 버전)
                    poi_colors = {
                        'amenity:hospital': 'red',
                        'amenity:school': 'blue',
                        'amenity:university': 'darkblue',
                        'amenity:pharmacy': 'lightred',
                        'amenity:clinic': 'pink',
                        'public_transport:station': 'green',
                        'highway:bus_stop': 'lightgreen',
                        'shop:supermarket': 'orange',
                        'shop:convenience': 'yellow',
                        'leisure:park': 'darkgreen',
                        'tourism:hotel': 'purple',
                        'amenity:restaurant': 'beige',
                        'amenity:cafe': 'brown'
                    }
                    
                    # 지도 표시용으로 추가 샘플링 (지도 성능 최적화)
                    if len(filtered_osm) > MAX_MAP_POIS:
                        map_osm = filtered_osm.sample(n=MAX_MAP_POIS, random_state=42)
                        st.warning(f"⚠️ 지도 성능을 위해 {len(filtered_osm):,}개 POI 중 {MAX_MAP_POIS:,}개만 지도에 표시합니다.")
                    else:
                        map_osm = filtered_osm
                    
                    # POI 타입별로 그룹화
                    poi_groups = {}
                    for idx, row in map_osm.iterrows():
                        poi_type = row.get('poi_type', 'unknown')
                        if poi_type not in poi_groups:
                            poi_groups[poi_type] = []
                        poi_groups[poi_type].append(row)
                    
                    # POI 마커 추가
                    for idx, row in map_osm.iterrows():
                        poi_type = row.get('poi_type', 'unknown')
                        color = poi_colors.get(poi_type, 'gray')
                        korean_name = KOREAN_POI_NAMES.get(poi_type, poi_type)
                        
                        folium.CircleMarker(
                            [row['lat'], row['lon']],
                            radius=5,
                            popup=f"""
                            <b>{row.get('name', '이름 없음')}</b><br>
                            타입: {korean_name} ({poi_type})<br>
                            거리: {row.get('distance_m', 0):.0f}m
                            """,
                            color='black',
                            fillColor=color,
                            fillOpacity=0.7,
                            weight=1
                        ).add_to(m)
                    
                    # 범례를 Streamlit 사이드바로 이동
                    with st.sidebar:
                        st.markdown("### 📍 POI 범례")
                        st.markdown("*반경 내 주요 시설물*")
                        
                        for poi_type, color in poi_colors.items():
                            if poi_type in poi_groups:
                                korean_name = KOREAN_POI_NAMES.get(poi_type, poi_type)
                                count = len(poi_groups[poi_type])
                                st.markdown(f"🔴 **{korean_name}** ({poi_type}) - {count}개")
                        st.markdown("---")
                    
                    # 지도 표시 (크기 증가)
                    map_html = m._repr_html_()
                    st.components.v1.html(map_html, width=1000, height=700)
                    
                except Exception as e:
                    st.error(f"POI 지도 표시 오류: {e}")
            else:
                st.info("💡 POI 지도를 보려면 위의 체크박스를 선택하세요.")
        else:
            st.info("OSM POI 데이터가 없습니다.")
    
    elif selected_site == "전체 보기":
        # 전체 보기 모드: 모든 사이트의 요약 정보만 표시
        st.subheader("📊 전체 사이트 요약")
        
        summary_data = []
        for site_id, site_data in st.session_state.collected_data.items():
            site_info = site_data.get('site_info', {})
            summary_data.append({
                "사이트 ID": site_id,
                "위치": f"({site_info.get('lat', 0):.4f}, {site_info.get('lon', 0):.4f})",
                "반경": f"{site_info.get('radius_m', 0)}m",
                "OSM POI": len(site_data.get('osm_poi', []))
            })
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
        st.info("💡 특정 지역의 상세 데이터를 보려면 위에서 지역을 선택하세요.")
    

# 사용법 안내
with st.expander("📖 사용법 안내"):
    st.markdown("""
    ## 🎯 사용 방법
    
    ### 1. 좌표 입력
    - **직접 입력**: 위도, 경도를 직접 입력
    - **CSV 업로드**: lat, lon, radius, site_id 컬럼이 포함된 CSV 파일
    - **Felo 결과**: Felo에서 생성된 후보지 리스트 파일
    
    ### 2. 수집 설정
    - **OSM POI**: 병원, 학교, 상점 등 주변 시설
    - **V-World 용도지역**: 토지이용계획, 용도지역 정보
    - **KOSIS 통계**: 행정구역별 인구, 가구 통계
    - **공공시설**: 공공데이터포털의 시설 정보
    
    ### 3. 결과 확인
    - 수집된 데이터를 탭별로 확인
    - 지도에서 위치 및 반경 확인
    - CSV, GeoJSON, XLSX 형식으로 다운로드
    
    ### 4. API 키 설정 (선택사항)
    ```bash
    # .env 파일에 추가
    VWORLD_API_KEY=your_vworld_key
    KOSIS_API_KEY=your_kosis_key
    PUBLIC_DATA_API_KEY=your_public_data_key
    ```
    """)

# 푸터
st.markdown("---")
st.markdown("**사이트 데이터 수집** - 좌표 기반 자동 도시 데이터 수집 시스템")
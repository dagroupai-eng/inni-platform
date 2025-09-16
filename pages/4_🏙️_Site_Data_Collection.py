import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
try:
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
import os
import tempfile
from urban_data_collector import UrbanDataCollector
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

# Session state 초기화
if 'collected_data' not in st.session_state:
    st.session_state.collected_data = None
if 'collection_status' not in st.session_state:
    st.session_state.collection_status = ""

# 사이드바 - 좌표 입력
with st.sidebar:
    st.header("📍 좌표 입력")
    
    # 좌표 입력 방식 선택
    input_method = st.radio(
        "입력 방식 선택",
        ["직접 입력", "CSV 파일 업로드", "Felo 결과 업로드"]
    )
    
    if input_method == "직접 입력":
        st.subheader("좌표 직접 입력")
        lat = st.number_input("위도 (Latitude)", value=37.5665, format="%.6f")
        lon = st.number_input("경도 (Longitude)", value=126.9780, format="%.6f")
        radius = st.number_input("수집 반경 (미터)", value=1000, min_value=100, max_value=5000)
        site_id = st.text_input("사이트 ID", value="S001")
        
        coordinates = [{"lat": lat, "lon": lon, "radius": radius, "site_id": site_id}]
    
    elif input_method == "CSV 파일 업로드":
        st.subheader("CSV 파일 업로드")
        uploaded_file = st.file_uploader(
            "CSV 파일 업로드",
            type=['csv'],
            help="lat, lon, radius, site_id 컬럼이 포함된 CSV 파일"
        )
        
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df.head())
            
            # 필수 컬럼 확인
            required_cols = ['lat', 'lon']
            if all(col in df.columns for col in required_cols):
                coordinates = df.to_dict('records')
                st.success(f"✅ {len(coordinates)}개 좌표 로드 완료")
            else:
                st.error("❌ 필수 컬럼 (lat, lon)이 없습니다.")
                coordinates = []
        else:
            coordinates = []
    
    else:  # Felo 결과 업로드
        st.subheader("Felo 결과 업로드")
        uploaded_file = st.file_uploader(
            "Felo 결과 파일 업로드",
            type=['csv', 'xlsx'],
            help="Felo에서 생성된 후보지 리스트 파일"
        )
        
        if uploaded_file:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.dataframe(df.head())
            
            # Felo 결과에서 좌표 추출 (컬럼명은 실제 Felo 결과에 맞게 수정)
            coord_cols = ['latitude', 'lat', 'y', '위도']
            lon_cols = ['longitude', 'lon', 'x', '경도']
            
            lat_col = None
            lon_col = None
            
            for col in coord_cols:
                if col in df.columns:
                    lat_col = col
                    break
            
            for col in lon_cols:
                if col in df.columns:
                    lon_col = col
                    break
            
            if lat_col and lon_col:
                coordinates = []
                for idx, row in df.iterrows():
                    coordinates.append({
                        "lat": row[lat_col],
                        "lon": row[lon_col],
                        "radius": 1000,  # 기본값
                        "site_id": f"Felo_{idx+1}"
                    })
                st.success(f"✅ {len(coordinates)}개 Felo 후보지 로드 완료")
            else:
                st.error("❌ 좌표 컬럼을 찾을 수 없습니다.")
                coordinates = []
        else:
            coordinates = []
    
    # 데이터 수집 설정
    st.header("⚙️ 수집 설정")
    
    collect_osm = st.checkbox("OSM POI 수집", value=True)
    collect_vworld = st.checkbox("V-World 용도지역", value=True)
    collect_kosis = st.checkbox("KOSIS 통계", value=True)
    collect_public = st.checkbox("공공시설 데이터", value=True)
    
    # API 키 상태 확인
    st.header("🔑 API 키 상태")
    
    api_keys = {
        "V-World": os.getenv("VWORLD_API_KEY"),
        "KOSIS": os.getenv("KOSIS_API_KEY"),
        "공공데이터": os.getenv("PUBLIC_DATA_API_KEY")
    }
    
    for api_name, api_key in api_keys.items():
        if api_key:
            st.success(f"✅ {api_name}")
        else:
            st.warning(f"⚠️ {api_name} (선택사항)")

# 메인 컨텐츠
if coordinates:
    st.header("🚀 데이터 수집 실행")
    
    if st.button("데이터 수집 시작", type="primary"):
        # 데이터 수집기 초기화
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

# 수집 결과 표시
if st.session_state.collected_data:
    st.header("📋 수집 결과")
    
    # 사이트 선택
    site_ids = list(st.session_state.collected_data.keys())
    selected_site = st.selectbox("사이트 선택", site_ids)
    
    if selected_site:
        data = st.session_state.collected_data[selected_site]
        
        # 탭으로 결과 표시
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 사이트 정보", "🏥 OSM POI", "🏘️ V-World 용도지역", "📊 KOSIS 통계", "🏛️ 공공시설"])
        
        with tab1:
            st.subheader("📍 사이트 정보")
            st.json(data['site_info'])
            
            # 지도 표시
            if 'lat' in data['site_info'] and 'lon' in data['site_info']:
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
                    fill=False
                ).add_to(m)
                
                # 지도를 HTML로 표시 (streamlit-folium 대신)
                try:
                    map_html = m._repr_html_()
                    st.components.v1.html(map_html, width=700, height=500)
                except Exception as e:
                    st.error(f"지도 표시 오류: {e}")
                    st.info("지도 대신 좌표 정보를 표시합니다:")
                    st.write(f"📍 위치: 위도 {data['site_info']['lat']}, 경도 {data['site_info']['lon']}")
                    st.write(f"📏 수집 반경: {data['site_info']['radius_m']}m")
        
        with tab2:
            st.subheader("🏥 OSM POI")
            if not data.get('osm_poi', pd.DataFrame()).empty:
                # 한국어 용어 치환
                korean_poi_names = {
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
                
                # POI 타입별 통계 (한국어 포함)
                if 'poi_type' in data['osm_poi'].columns:
                    poi_stats = data['osm_poi']['poi_type'].value_counts()
                    poi_stats_korean = {}
                    for poi_type, count in poi_stats.items():
                        korean_name = korean_poi_names.get(poi_type, poi_type)
                        poi_stats_korean[f"{korean_name} ({poi_type})"] = count
                    
                    st.bar_chart(poi_stats_korean)
                
                # POI 데이터 표시 (한국어 용어 추가)
                display_df = data['osm_poi'].copy()
                if 'poi_type' in display_df.columns:
                    display_df['한국어_타입'] = display_df['poi_type'].map(korean_poi_names).fillna(display_df['poi_type'])
                st.dataframe(display_df, use_container_width=True)
                
                # OSM POI 지도 표시
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
                    
                    # 한국어 용어 치환
                    korean_poi_names = {
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
                    
                    # POI 타입별로 그룹화
                    poi_groups = {}
                    for idx, row in data['osm_poi'].iterrows():
                        poi_type = row.get('poi_type', 'unknown')
                        if poi_type not in poi_groups:
                            poi_groups[poi_type] = []
                        poi_groups[poi_type].append(row)
                    
                    # POI 마커 추가
                    for idx, row in data['osm_poi'].iterrows():
                        poi_type = row.get('poi_type', 'unknown')
                        color = poi_colors.get(poi_type, 'gray')
                        korean_name = korean_poi_names.get(poi_type, poi_type)
                        
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
                                korean_name = korean_poi_names.get(poi_type, poi_type)
                                count = len(poi_groups[poi_type])
                                st.markdown(f"🔴 **{korean_name}** ({poi_type}) - {count}개")
                        st.markdown("---")
                    
                    # 지도 표시 (크기 증가)
                    map_html = m._repr_html_()
                    st.components.v1.html(map_html, width=1000, height=700)
                    
                except Exception as e:
                    st.error(f"POI 지도 표시 오류: {e}")
            else:
                st.info("OSM POI 데이터가 없습니다.")
        
        with tab3:
            st.subheader("🏘️ V-World 용도지역")
            if not data.get('vworld_zoning', gpd.GeoDataFrame()).empty:
                # V-World 레이어 한국어 이름 매핑 (전체 매핑 사용)
                vworld_korean_names = {
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
                
                # GeoDataFrame을 일반 DataFrame으로 변환 (geometry 컬럼 제외)
                vworld_df = data['vworld_zoning'].drop(columns=['geometry'], errors='ignore')
                
                # 한국어 레이어명 추가 (대소문자 구분 없이)
                if 'layer_name' in vworld_df.columns:
                    # 대소문자 구분 없이 매핑하는 함수
                    def get_korean_name(layer_name):
                        # 정확한 매칭 먼저 시도
                        if layer_name in vworld_korean_names:
                            return vworld_korean_names[layer_name]
                        # 대소문자 구분 없이 매칭 시도
                        for key, value in vworld_korean_names.items():
                            if key.lower() == layer_name.lower():
                                return value
                        return layer_name
                    
                    vworld_df['한국어_레이어'] = vworld_df['layer_name'].apply(get_korean_name)
                
                st.dataframe(vworld_df, use_container_width=True)
                
                # 지도에 용도지역 표시
                if 'geometry' in data['vworld_zoning'].columns:
                    st.subheader("🗺️ 용도지역 지도")
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
                        
                        # 용도지역 폴리곤 표시 (레이어 토글 기능 포함)
                        if len(data['vworld_zoning']) > 0:
                            # 레이어별로 그룹화
                            layer_groups = {}
                            for idx, row in data['vworld_zoning'].iterrows():
                                if row.geometry and hasattr(row.geometry, '__geo_interface__'):
                                    layer_name = row.get('layer_name', 'Unknown')
                                    if layer_name not in layer_groups:
                                        layer_groups[layer_name] = []
                                    layer_groups[layer_name].append(row)
                            
                            # V-World 레이어 한국어 이름 매핑 (HTML에서 추출)
                            vworld_korean_names = {
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
                            
                            # 레이어 우선순위 설정 (가장 작은 단위부터)
                            layer_priority = {
                                'LT_C_UDPG': 1,    # 용도구역 (가장 작은 단위)
                                'LT_C_UDDI': 2,    # 용도지구
                                'LT_C_UPISU': 3,   # 용도지역 (가장 큰 단위)
                                # 구체적인 용도지역 코드들 (우선순위 4-23)
                                'LT_P_DGMUSEUMART': 4,
                                'LT_P_DGPARK': 5,
                                'LT_P_DGCOMMERCIAL': 6,
                                'LT_P_DGRESIDENTIAL': 7,
                                'LT_P_DGINDUSTRIAL': 8,
                                'LT_P_DGGREEN': 9,
                                'LT_P_DGAGRICULTURAL': 10,
                                'LT_P_DGFOREST': 11,
                                'LT_P_DGWATER': 12,
                                'LT_P_DGROAD': 13,
                                'LT_P_DGPUBLIC': 14,
                                'LT_P_DGRELIGIOUS': 15,
                                'LT_P_DGEDUCATIONAL': 16,
                                'LT_P_DGMEDICAL': 17,
                                'LT_P_DGTRANSPORT': 18,
                                'LT_P_DGWAREHOUSE': 19,
                                'LT_P_DGUTILITY': 20,
                                'LT_P_DGCEMETERY': 21,
                                'LT_P_DGOTHER': 22
                            }
                            
                            # 레이어를 우선순위별로 정렬
                            sorted_layers = sorted(layer_groups.items(), 
                                                 key=lambda x: layer_priority.get(x[0], 999))
                            
                            # 색상 팔레트
                            colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
                            
                            # Folium 레이어 그룹 생성
                            from folium import FeatureGroup
                            
                            # 각 레이어별 FeatureGroup 생성
                            layer_groups_folium = {}
                            for i, (layer_name, rows) in enumerate(sorted_layers):
                                color = colors[i % len(colors)]
                                priority = layer_priority.get(layer_name, 999)
                                
                                # FeatureGroup 생성 (한국어 이름 사용)
                                korean_layer_name = vworld_korean_names.get(layer_name, layer_name)
                                fg = FeatureGroup(name=f"{korean_layer_name} (우선순위: {priority})", show=True if priority == 1 else False)
                                
                                for row in rows:
                                    # 폴리곤 스타일 설정
                                    style = {
                                        'fillColor': color,
                                        'color': 'black',
                                        'weight': 2,
                                        'fillOpacity': 0.4 if priority == 1 else 0.2,  # 우선순위 높은 것 더 진하게
                                        'opacity': 0.8
                                    }
                                    
                                    # 팝업 정보 생성 (한국어 이름 포함)
                                    korean_layer_name = vworld_korean_names.get(layer_name, layer_name)
                                    popup_info = f"""
                                    <b>용도지역 정보</b><br>
                                    레이어: {korean_layer_name} ({layer_name})<br>
                                    우선순위: {priority}<br>
                                    """
                                    
                                    # 속성 정보 추가
                                    if hasattr(row, 'properties') and row.properties:
                                        for key, value in row.properties.items():
                                            if key not in ['geometry']:
                                                popup_info += f"{key}: {value}<br>"
                                    
                                    folium.GeoJson(
                                        row.geometry.__geo_interface__,
                                        style_function=lambda x, color=color: style,
                                        popup=folium.Popup(popup_info, max_width=300)
                                    ).add_to(fg)
                                
                                fg.add_to(m)
                                layer_groups_folium[layer_name] = fg
                            
                            # 레이어 컨트롤 추가
                            folium.LayerControl().add_to(m)
                            
                            # 범례를 Streamlit 사이드바로 이동
                            with st.sidebar:
                                st.markdown("### 🗺️ 용도지역 범례")
                                st.markdown("*왼쪽 상단의 레이어 컨트롤로 켜고 끌 수 있습니다*")
                                
                                for i, (layer_name, rows) in enumerate(sorted_layers):
                                    color = colors[i % len(colors)]
                                    priority = layer_priority.get(layer_name, 999)
                                    priority_text = "가장 작은 단위" if priority == 1 else "중간 단위" if priority == 2 else "가장 큰 단위"
                                    
                                    # 한국어 용어 치환 (대소문자 구분 없이)
                                    def get_korean_name_for_legend(layer_name):
                                        # 정확한 매칭 먼저 시도
                                        if layer_name in vworld_korean_names:
                                            return vworld_korean_names[layer_name]
                                        # 대소문자 구분 없이 매칭 시도
                                        for key, value in vworld_korean_names.items():
                                            if key.lower() == layer_name.lower():
                                                return value
                                        return layer_name
                                    
                                    korean_layer_name = get_korean_name_for_legend(layer_name)
                                    
                                    # 한국어 용어가 있으면 한국어만 표시, 없으면 원본 표시
                                    if korean_layer_name != layer_name:
                                        st.markdown(f"🟦 **{korean_layer_name}**")
                                    else:
                                        st.markdown(f"🟦 **{layer_name}**")
                                    st.markdown(f"   *{priority_text}*")
                                    st.markdown("---")
                        
                        # 지도 표시 (크기 증가)
                        map_html = m._repr_html_()
                        st.components.v1.html(map_html, width=1000, height=700)
                        
                    except Exception as e:
                        st.error(f"지도 표시 오류: {e}")
            else:
                st.info("V-World 용도지역 데이터가 없습니다.")
        
        with tab4:
            st.subheader("📊 KOSIS 통계")
            if not data.get('kosis_stats', pd.DataFrame()).empty:
                st.dataframe(data['kosis_stats'], use_container_width=True)
            else:
                st.info("KOSIS 통계 데이터가 없습니다.")
        
        with tab5:
            st.subheader("🏛️ 공공시설")
            if not data.get('public_facilities', pd.DataFrame()).empty:
                st.dataframe(data['public_facilities'], use_container_width=True)
            else:
                st.info("공공시설 데이터가 없습니다.")
        
        # 다운로드 버튼
        st.subheader("📥 데이터 다운로드")
        
        if st.button("전체 데이터 다운로드", type="primary"):
            # 임시 디렉토리에 저장
            with tempfile.TemporaryDirectory() as temp_dir:
                collector = UrbanDataCollector()
                saved_files = collector.save_collected_data(data, temp_dir)
                
                # ZIP 파일 생성
                import zipfile
                zip_path = f"{temp_dir}/collected_data.zip"
                
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for file_type, file_path in saved_files.items():
                        if os.path.exists(file_path):
                            zipf.write(file_path, os.path.basename(file_path))
                
                # ZIP 파일 다운로드
                with open(zip_path, 'rb') as f:
                    st.download_button(
                        label="📦 ZIP 파일 다운로드",
                        data=f.read(),
                        file_name=f"{selected_site}_collected_data.zip",
                        mime="application/zip"
                    )

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

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import random
import numpy as np

# 페이지 설정
st.set_page_config(
    page_title="지도 분석",
    page_icon="🗺️",
    layout="wide"
)

# 제목
st.title("🗺️ 지도 분석")
st.markdown("**프로젝트 위치 및 지리적 데이터 시각화**")

# 샘플 지리적 데이터 생성
@st.cache_data
def generate_geo_data():
    """샘플 지리적 데이터 생성"""
    
    # 서울 지역 좌표 및 프로젝트 데이터
    seoul_projects = [
        {'name': '강남구 주거단지', 'lat': 37.5172, 'lon': 127.0473, 'type': '주거', 'size': '대형', 'status': '완료'},
        {'name': '서초구 상업시설', 'lat': 37.4837, 'lon': 127.0324, 'type': '상업', 'size': '중형', 'status': '진행중'},
        {'name': '송파구 교육시설', 'lat': 37.5145, 'lon': 127.1050, 'type': '교육', 'size': '대형', 'status': '계획'},
        {'name': '마포구 문화시설', 'lat': 37.5663, 'lon': 126.9019, 'type': '문화', 'size': '소형', 'status': '완료'},
        {'name': '영등포구 의료시설', 'lat': 37.5264, 'lon': 126.8962, 'type': '의료', 'size': '대형', 'status': '진행중'},
        {'name': '종로구 역사시설', 'lat': 37.5735, 'lon': 126.9788, 'type': '문화', 'size': '중형', 'status': '완료'},
        {'name': '중구 상업시설', 'lat': 37.5636, 'lon': 126.9970, 'type': '상업', 'size': '대형', 'status': '계획'},
        {'name': '용산구 주거단지', 'lat': 37.5384, 'lon': 126.9654, 'type': '주거', 'size': '중형', 'status': '진행중'},
    ]
    
    # 전국 주요 도시 데이터
    cities_data = [
        {'city': '서울', 'lat': 37.5665, 'lon': 126.9780, 'projects': 35, 'population': 9720846},
        {'city': '부산', 'lat': 35.1796, 'lon': 129.0756, 'projects': 15, 'population': 3448737},
        {'city': '대구', 'lat': 35.8714, 'lon': 128.6014, 'projects': 12, 'population': 2413076},
        {'city': '인천', 'lat': 37.4563, 'lon': 126.7052, 'projects': 10, 'population': 2954318},
        {'city': '광주', 'lat': 35.1595, 'lon': 126.8526, 'projects': 8, 'population': 1441970},
        {'city': '대전', 'lat': 36.3504, 'lon': 127.3845, 'projects': 6, 'population': 1475220},
        {'city': '울산', 'lat': 35.5384, 'lon': 129.3114, 'projects': 4, 'population': 1134940},
    ]
    
    return seoul_projects, cities_data

# 데이터 로드
seoul_projects, cities_data = generate_geo_data()

# 메인 지도 섹션
st.subheader("📍 프로젝트 위치 지도")

# 지도 타입 선택
map_type = st.selectbox(
    "지도 타입 선택",
    ["서울 상세 지도", "전국 프로젝트 분포"]
)

if map_type == "서울 상세 지도":
    # 서울 프로젝트 지도
    df_seoul = pd.DataFrame(seoul_projects)
    
    # size 컬럼을 숫자로 변환
    size_map = {'소형': 8, '중형': 12, '대형': 16}
    df_seoul['size_num'] = df_seoul['size'].map(size_map)
    
    # 프로젝트 유형별 색상 설정
    color_map = {
        '주거': 'red',
        '상업': 'blue', 
        '교육': 'green',
        '문화': 'purple',
        '의료': 'orange'
    }
    
    fig_seoul = px.scatter_mapbox(
        df_seoul,
        lat='lat',
        lon='lon',
        hover_name='name',
        hover_data=['type', 'size', 'status'],
        color='type',
        color_discrete_map=color_map,
        size='size_num',
        size_max=20,
        zoom=10,
        height=600,
        title="서울 지역 프로젝트 분포"
    )
    
    fig_seoul.update_layout(
        mapbox_style="open-street-map",
        mapbox_center_lat=37.5665,
        mapbox_center_lon=126.9780,
        margin={"r":0,"t":0,"l":0,"b":0}
    )
    
    st.plotly_chart(fig_seoul, use_container_width=True)

elif map_type == "전국 프로젝트 분포":
    # 전국 도시별 프로젝트 분포
    df_cities = pd.DataFrame(cities_data)
    
    fig_cities = px.scatter_mapbox(
        df_cities,
        lat='lat',
        lon='lon',
        hover_name='city',
        hover_data=['projects', 'population'],
        size='projects',
        size_max=30,
        color='projects',
        color_continuous_scale='Blues',
        zoom=5,
        height=600,
        title="전국 도시별 프로젝트 분포"
    )
    
    fig_cities.update_layout(
        mapbox_style="open-street-map",
        mapbox_center_lat=36.5,
        mapbox_center_lon=127.5,
        margin={"r":0,"t":0,"l":0,"b":0}
    )
    
    st.plotly_chart(fig_cities, use_container_width=True)


# st.markdown("---")

# 통계 섹션 - 주석 처리
# col1, col2 = st.columns(2)

# with col1:
#     st.subheader("📊 지역별 프로젝트 통계")
#     
#     # 지역별 프로젝트 수
#     region_stats = pd.DataFrame({
#         '지역': ['서울', '부산', '대구', '인천', '광주', '대전', '울산'],
#         '프로젝트 수': [35, 15, 12, 10, 8, 6, 4],
#         '인구 (만명)': [972, 345, 241, 295, 144, 148, 113]
#     })
#     
#     fig_region = px.bar(
#         region_stats,
#         x='지역',
#         y='프로젝트 수',
#         title="지역별 프로젝트 수",
#         color='프로젝트 수',
#         color_continuous_scale='Blues'
#     )
#     st.plotly_chart(fig_region, use_container_width=True)

# with col2:
#     st.subheader("🏗️ 프로젝트 유형별 분포")
#     
#     # 프로젝트 유형별 통계
#     type_stats = pd.DataFrame({
#         '유형': ['주거', '상업', '교육', '문화', '의료'],
#         '개수': [25, 18, 12, 8, 7],
#         '비율': [35.7, 25.7, 17.1, 11.4, 10.0]
#     })
#     
#     fig_type = px.pie(
#         type_stats,
#         values='개수',
#         names='유형',
#         title="프로젝트 유형별 분포"
#     )
#     st.plotly_chart(fig_type, use_container_width=True)

# st.markdown("---")

# 상세 데이터 테이블 - 주석 처리
# st.subheader("📋 프로젝트 상세 정보")

# 필터 옵션
# col1, col2, col3 = st.columns(3)

# with col1:
#     type_filter = st.multiselect(
#         "프로젝트 유형",
#         options=['주거', '상업', '교육', '문화', '의료'],
#         default=['주거', '상업', '교육', '문화', '의료']
#     )

# with col2:
#     size_filter = st.multiselect(
#         "프로젝트 규모",
#         options=['소형', '중형', '대형'],
#         default=['소형', '중형', '대형']
#     )

# with col3:
#     status_filter = st.multiselect(
#         "진행 상태",
#         options=['계획', '진행중', '완료'],
#         default=['계획', '진행중', '완료']
#     )

# 필터 적용
# df_filtered = pd.DataFrame(seoul_projects)
# df_filtered = df_filtered[
#     (df_filtered['type'].isin(type_filter)) &
#     (df_filtered['size'].isin(size_filter)) &
#     (df_filtered['status'].isin(status_filter))
# ]

# 결과 표시
# st.dataframe(
#     df_filtered,
#     use_container_width=True,
#     column_config={
#         "name": "프로젝트명",
#         "type": "유형",
#         "size": "규모",
#         "status": "상태",
#         "lat": st.column_config.NumberColumn("위도", format="%.4f"),
#         "lon": st.column_config.NumberColumn("경도", format="%.4f")
#     }
# )

# 사이드바 - 추가 정보
# with st.sidebar:
#     st.header("🗺️ 지도 정보")
    
#     st.metric("총 프로젝트", "118", "12")
#     st.metric("활성 프로젝트", "45", "8")
#     st.metric("완료된 프로젝트", "73", "4")
    
#     st.markdown("---")
    
#     st.header("📍 주요 지역")
#     for city in cities_data:
#         st.write(f"**{city['city']}**: {city['projects']}개 프로젝트")
    
#     st.markdown("---")
    
#     st.header("🏗️ 프로젝트 유형")
#     type_counts = {'주거': 25, '상업': 18, '교육': 12, '문화': 8, '의료': 7}
#     for ptype, count in type_counts.items():
#         st.write(f"**{ptype}**: {count}개")

# # 푸터
# st.markdown("---")
# st.markdown("**지도 분석** - 프로젝트 위치 및 지리적 인사이트")

import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(
    page_title="지도 분석",
    page_icon=None,
    layout="wide"
)

# 제목
st.title("지도 분석")
st.markdown("**프로젝트 위치 및 지리적 데이터 시각화**")

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

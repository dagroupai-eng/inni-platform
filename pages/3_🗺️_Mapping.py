import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import random
import numpy as np
from datetime import datetime, timedelta
import json

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

# 탭으로 기능 분리
tab1, tab2, tab3, tab4, tab5 = st.tabs(["지도 시각화", "통계 분석 (개발중)", "데이터 필터 (개발중)", "인사이트 (개발중)", "데이터 입력 (개발중)"])

with tab1:
    st.subheader("프로젝트 위치 지도")
    
    # 지도 타입 선택
    map_type = st.selectbox(
        "지도 타입 선택",
        ["서울 상세 지도", "전국 프로젝트 분포", "히트맵", "타임라인 지도"]
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
            '의료': 'orange',
            '기타': 'gray'
        }
        
        # scatter_map 사용
        fig_seoul = px.scatter_map(
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
            map_style="open-street-map",
            map_center_lat=37.5665,
            map_center_lon=126.9780,
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        
        st.plotly_chart(fig_seoul, use_container_width=True)

    elif map_type == "전국 프로젝트 분포":
        # 전국 도시별 프로젝트 분포
        df_cities = pd.DataFrame(cities_data)
        
        fig_cities = px.scatter_map(
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
            map_style="open-street-map",
            map_center_lat=36.5,
            map_center_lon=127.5,
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        
        st.plotly_chart(fig_cities, use_container_width=True)

    elif map_type == "히트맵":
        # 히트맵 생성
        df_seoul = pd.DataFrame(seoul_projects)
        
        # 히트맵용 데이터 준비
        fig_heatmap = px.density_map(
            df_seoul,
            lat='lat',
            lon='lon',
            z='budget',
            radius=20,
            zoom=10,
            height=600,
            title="서울 지역 프로젝트 예산 히트맵"
        )
        
        fig_heatmap.update_layout(
            map_style="open-street-map",
            map_center_lat=37.5665,
            map_center_lon=126.9780,
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        
        st.plotly_chart(fig_heatmap, use_container_width=True)
    
    elif map_type == "타임라인 지도":
        # 타임라인 지도 (진행 상태별)
        df_seoul = pd.DataFrame(seoul_projects)
        
        # 상태별 색상 설정
        status_colors = {
            '계획': 'lightblue',
            '진행중': 'orange', 
            '완료': 'green'
        }
        
        fig_timeline = px.scatter_map(
            df_seoul,
            lat='lat',
            lon='lon',
            hover_name='name',
            hover_data=['type', 'status'],
            color='status',
            color_discrete_map=status_colors,
            size='budget',
            size_max=25,
            zoom=10,
            height=600,
            title="프로젝트 진행 상태별 분포"
        )
        
        fig_timeline.update_layout(
            map_style="open-street-map",
            map_center_lat=37.5665,
            map_center_lon=126.9780,
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        
        st.plotly_chart(fig_timeline, use_container_width=True)

with tab2:
    st.subheader("통계 분석 (개발중)")
    st.info("이 기능은 현재 개발 중입니다.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("지역별 프로젝트 통계")
        
        # 지역별 프로젝트 수
        region_stats = pd.DataFrame({
            '지역': ['서울', '부산', '대구', '인천', '광주', '대전', '울산'],
            '프로젝트 수': [35, 15, 12, 10, 8, 6, 4],
            '인구 (만명)': [972, 345, 241, 295, 144, 148, 113]
        })
        
        fig_region = px.bar(
            region_stats,
            x='지역',
            y='프로젝트 수',
            title="지역별 프로젝트 수",
            color='프로젝트 수',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_region, use_container_width=True)
    
    with col2:
        st.subheader("프로젝트 유형별 분포")
        
        # 프로젝트 유형별 통계
        type_stats = pd.DataFrame({
            '유형': ['주거', '상업', '교육', '문화', '의료'],
            '개수': [25, 18, 12, 8, 7],
            '비율': [35.7, 25.7, 17.1, 11.4, 10.0]
        })
        
        fig_type = px.pie(
            type_stats,
            values='개수',
            names='유형',
            title="프로젝트 유형별 분포"
        )
        st.plotly_chart(fig_type, use_container_width=True)
    
    # 예산 분석 (사용자 데이터 포함)
    st.subheader("예산 분석")
    df_seoul = pd.DataFrame(seoul_projects)
    
    # 사용자 입력 데이터가 있으면 추가
    if 'user_projects' in st.session_state and st.session_state.user_projects:
        user_df = pd.DataFrame(st.session_state.user_projects)
        df_seoul = pd.concat([df_seoul, user_df], ignore_index=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 프로젝트 유형별 평균 예산
        budget_by_type = df_seoul.groupby('type')['budget'].mean().reset_index()
        budget_by_type['budget_billion'] = budget_by_type['budget'] / 1000000000
        
        fig_budget = px.bar(
            budget_by_type,
            x='type',
            y='budget_billion',
            title="프로젝트 유형별 평균 예산 (억원)",
            color='budget_billion',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_budget, use_container_width=True)
    
    with col2:
        # 프로젝트 규모별 예산 분포
        fig_size_budget = px.box(
            df_seoul,
            x='size',
            y='budget',
            title="프로젝트 규모별 예산 분포",
            color='size'
        )
        # fig_size_budget.update_yaxis(tickformat='.0f')  # 이 라인을 주석 처리
        st.plotly_chart(fig_size_budget, use_container_width=True)

with tab3:
    st.subheader("데이터 필터 (개발중)")
    st.info("이 기능은 현재 개발 중입니다.")
    
    df_seoul = pd.DataFrame(seoul_projects)
    
    # 사용자 입력 데이터가 있으면 추가
    if 'user_projects' in st.session_state and st.session_state.user_projects:
        user_df = pd.DataFrame(st.session_state.user_projects)
        df_seoul = pd.concat([df_seoul, user_df], ignore_index=True)

# 필터 옵션
    col1, col2, col3 = st.columns(3)
    
    with col1:
        type_filter = st.multiselect(
            "프로젝트 유형",
            options=['주거', '상업', '교육', '문화', '의료', '기타'],
            default=['주거', '상업', '교육', '문화', '의료', '기타']
        )
    
    with col2:
        size_filter = st.multiselect(
            "프로젝트 규모",
            options=['소형', '중형', '대형'],
            default=['소형', '중형', '대형']
        )
    
    with col3:
        status_filter = st.multiselect(
            "진행 상태",
            options=['계획', '진행중', '완료'],
            default=['계획', '진행중', '완료']
        )
    
    # 예산 범위 필터
    budget_range = st.slider(
        "예산 범위 (억원)",
        min_value=0,
        max_value=2500,
        value=(0, 2500),
        step=50
    )

# 필터 적용
    df_filtered = df_seoul[
        (df_seoul['type'].isin(type_filter)) &
        (df_seoul['size'].isin(size_filter)) &
        (df_seoul['status'].isin(status_filter)) &
        (df_seoul['budget'] >= budget_range[0] * 100000000) &
        (df_seoul['budget'] <= budget_range[1] * 100000000)
    ]
    
    st.write(f"**필터링된 결과: {len(df_filtered)}개 프로젝트**")

# 결과 표시
    st.dataframe(
        df_filtered,
        use_container_width=True,
        column_config={
            "name": "프로젝트명",
            "type": "유형",
            "size": "규모",
            "status": "상태",
            "budget": st.column_config.NumberColumn("예산 (원)", format="%d"),
            "area": st.column_config.NumberColumn("면적 (㎡)", format="%d"),
            "lat": st.column_config.NumberColumn("위도", format="%.4f"),
            "lon": st.column_config.NumberColumn("경도", format="%.4f")
        }
    )

with tab4:
    st.subheader("인사이트 (개발중)")
    st.info("이 기능은 현재 개발 중입니다.")
    
    df_seoul = pd.DataFrame(seoul_projects)
    
    # 사용자 입력 데이터가 있으면 추가
    if 'user_projects' in st.session_state and st.session_state.user_projects:
        user_df = pd.DataFrame(st.session_state.user_projects)
        df_seoul = pd.concat([df_seoul, user_df], ignore_index=True)
    
    # 주요 지표
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_projects = len(df_seoul)
        st.metric("총 프로젝트", total_projects)
    
    with col2:
        total_budget = df_seoul['budget'].sum() / 1000000000  # 억원 단위
        st.metric("총 예산", f"{total_budget:,.0f}억원")
    
    with col3:
        avg_budget = df_seoul['budget'].mean() / 1000000000  # 억원 단위
        st.metric("평균 예산", f"{avg_budget:,.0f}억원")
    
    with col4:
        completed_projects = len(df_seoul[df_seoul['status'] == '완료'])
        completion_rate = (completed_projects / total_projects) * 100
        st.metric("완료율", f"{completion_rate:.1f}%")
    
    st.markdown("---")
    
    # 인사이트 분석
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("프로젝트 유형별 인사이트")
        
        # 유형별 통계
        type_analysis = df_seoul.groupby('type').agg({
            'budget': ['count', 'mean', 'sum'],
            'area': 'mean'
        }).round(0)
        
        type_analysis.columns = ['프로젝트 수', '평균 예산', '총 예산', '평균 면적']
        type_analysis['평균 예산'] = type_analysis['평균 예산'] / 1000000000  # 억원 단위
        type_analysis['총 예산'] = type_analysis['총 예산'] / 1000000000  # 억원 단위
        
        st.dataframe(type_analysis, use_container_width=True)
    
    with col2:
        st.subheader("지역별 인사이트")
        
        # 지역별 통계 (구 단위)
        df_seoul['district'] = df_seoul['name'].str.extract(r'(\w+구)')
        district_analysis = df_seoul.groupby('district').agg({
            'budget': ['count', 'sum'],
            'area': 'sum'
        }).round(0)
        
        district_analysis.columns = ['프로젝트 수', '총 예산', '총 면적']
        district_analysis['총 예산'] = district_analysis['총 예산'] / 1000000000  # 억원 단위
        
        st.dataframe(district_analysis, use_container_width=True)
    
    # 예산 대비 면적 효율성
    st.subheader("예산 대비 면적 효율성")
    
    df_seoul['efficiency'] = df_seoul['area'] / (df_seoul['budget'] / 1000000000)  # ㎡/억원
    
    fig_efficiency = px.scatter(
        df_seoul,
        x='budget',
        y='area',
        color='type',
        size='efficiency',
        hover_name='name',
        hover_data=['type', 'status', 'efficiency'],
        title="예산 대비 면적 효율성 분석",
        labels={'budget': '예산 (원)', 'area': '면적 (㎡)'}
    )
    
    st.plotly_chart(fig_efficiency, use_container_width=True)

with tab5:
    st.subheader("프로젝트 데이터 입력 (개발중)")
    st.info("이 기능은 현재 개발 중입니다.")
    
    # 사용자 입력 폼
    with st.form("project_input_form"):
        st.markdown("### 새 프로젝트 추가")
        
        col1, col2 = st.columns(2)
        
        with col1:
            project_name = st.text_input("프로젝트명", placeholder="예: 강남구 주거단지")
            project_type = st.selectbox("프로젝트 유형", ["주거", "상업", "교육", "문화", "의료", "기타"])
            project_size = st.selectbox("프로젝트 규모", ["소형", "중형", "대형"])
            project_status = st.selectbox("진행 상태", ["계획", "진행중", "완료"])
        
        with col2:
            latitude = st.number_input("위도", min_value=33.0, max_value=39.0, value=37.5665, step=0.0001, format="%.4f")
            longitude = st.number_input("경도", min_value=124.0, max_value=132.0, value=126.9780, step=0.0001, format="%.4f")
            budget = st.number_input("예산 (억원)", min_value=0, max_value=10000, value=100, step=10)
            area = st.number_input("면적 (㎡)", min_value=0, max_value=100000, value=10000, step=100)
        
        # 날짜 입력
        col3, col4 = st.columns(2)
        with col3:
            start_date = st.date_input("시작일", value=datetime.now().date())
        with col4:
            end_date = st.date_input("종료일", value=datetime.now().date() + timedelta(days=365))
        
        # 추가 정보
        additional_info = st.text_area("추가 정보", placeholder="프로젝트에 대한 추가 설명이나 특이사항을 입력하세요.")
        
        # 제출 버튼
        submitted = st.form_submit_button("프로젝트 추가", type="primary")
        
        if submitted:
            # 입력 검증
            if not project_name:
                st.error("프로젝트명을 입력해주세요.")
            elif budget <= 0:
                st.error("예산을 올바르게 입력해주세요.")
            elif area <= 0:
                st.error("면적을 올바르게 입력해주세요.")
            elif start_date >= end_date:
                st.error("종료일은 시작일보다 늦어야 합니다.")
            else:
                # 새 프로젝트 데이터 생성
                new_project = {
                    'name': project_name,
                    'lat': latitude,
                    'lon': longitude,
                    'type': project_type,
                    'size': project_size,
                    'status': project_status,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'budget': budget * 100000000,  # 억원을 원으로 변환
                    'area': area,
                    'additional_info': additional_info
                }
                
                # 세션 상태에 저장
                if 'user_projects' not in st.session_state:
                    st.session_state.user_projects = []
                
                st.session_state.user_projects.append(new_project)
                st.success(f"프로젝트 '{project_name}'이 성공적으로 추가되었습니다!")
                st.balloons()
    
    # 사용자 입력 데이터 표시
    if 'user_projects' in st.session_state and st.session_state.user_projects:
        st.markdown("---")
        st.subheader("입력된 프로젝트 목록")
        
        # 데이터프레임으로 표시
        user_df = pd.DataFrame(st.session_state.user_projects)
        
        # 데이터 테이블 표시
        st.dataframe(
            user_df,
            use_container_width=True,
            column_config={
                "name": "프로젝트명",
                "type": "유형",
                "size": "규모",
                "status": "상태",
                "budget": st.column_config.NumberColumn("예산 (원)", format="%d"),
                "area": st.column_config.NumberColumn("면적 (㎡)", format="%d"),
                "lat": st.column_config.NumberColumn("위도", format="%.4f"),
                "lon": st.column_config.NumberColumn("경도", format="%.4f"),
                "start_date": "시작일",
                "end_date": "종료일"
            }
        )
        
        # 사용자 데이터로 지도 생성
        st.subheader("입력된 프로젝트 지도")
        
        # 색상 매핑
        color_map = {
            '주거': 'red',
            '상업': 'blue', 
            '교육': 'green',
            '문화': 'purple',
            '의료': 'orange',
            '기타': 'gray'
        }
        
        # 크기 매핑
        size_map = {'소형': 8, '중형': 12, '대형': 16}
        user_df['size_num'] = user_df['size'].map(size_map)
        
        # 지도 생성
        fig_user = px.scatter_map(
            user_df,
            lat='lat',
            lon='lon',
            hover_name='name',
            hover_data=['type', 'size', 'status', 'budget', 'area', 'start_date', 'end_date'],
            color='type',
            color_discrete_map=color_map,
            size='size_num',
            size_max=20,
            zoom=10,
            height=500,
            title="사용자 입력 프로젝트 지도"
        )
        
        fig_user.update_layout(
            map_style="open-street-map",
            map_center_lat=user_df['lat'].mean(),
            map_center_lon=user_df['lon'].mean(),
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        
        st.plotly_chart(fig_user, use_container_width=True)
        
        # 데이터 관리 버튼
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("데이터 초기화", type="secondary"):
                st.session_state.user_projects = []
                st.rerun()
        
        with col2:
            # CSV 다운로드
            csv_data = user_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="CSV 다운로드",
                data=csv_data,
                file_name=f"user_projects_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col3:
            # JSON 다운로드
            json_data = user_df.to_json(orient='records', force_ascii=False, indent=2)
            st.download_button(
                label="JSON 다운로드",
                data=json_data,
                file_name=f"user_projects_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    # CSV 파일 업로드 기능
    st.markdown("---")
    st.subheader("CSV 파일 업로드")
    
    uploaded_file = st.file_uploader(
        "CSV 파일을 업로드하여 프로젝트 데이터를 일괄 추가하세요",
        type=['csv'],
        help="CSV 파일은 다음 컬럼을 포함해야 합니다: name, lat, lon, type, size, status, budget, area, start_date, end_date"
    )
    
    if uploaded_file is not None:
        try:
            # CSV 파일 읽기
            df_uploaded = pd.read_csv(uploaded_file)
            
            # 필수 컬럼 확인
            required_columns = ['name', 'lat', 'lon', 'type', 'size', 'status', 'budget', 'area']
            missing_columns = [col for col in required_columns if col not in df_uploaded.columns]
            
            if missing_columns:
                st.error(f"필수 컬럼이 누락되었습니다: {', '.join(missing_columns)}")
            else:
                # 데이터 검증
                valid_data = []
                for idx, row in df_uploaded.iterrows():
                    if (pd.notna(row['name']) and 
                        pd.notna(row['lat']) and pd.notna(row['lon']) and
                        pd.notna(row['type']) and pd.notna(row['size']) and
                        pd.notna(row['status']) and pd.notna(row['budget']) and
                        pd.notna(row['area'])):
                        
                        # 예산을 원 단위로 변환 (억원으로 입력된 경우)
                        budget = row['budget']
                        if budget < 100000000:  # 억원 단위로 입력된 것으로 가정
                            budget = budget * 100000000
                        
                        valid_data.append({
                            'name': str(row['name']),
                            'lat': float(row['lat']),
                            'lon': float(row['lon']),
                            'type': str(row['type']),
                            'size': str(row['size']),
                            'status': str(row['status']),
                            'budget': int(budget),
                            'area': int(row['area']),
                            'start_date': row.get('start_date', datetime.now().strftime('%Y-%m-%d')),
                            'end_date': row.get('end_date', (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')),
                            'additional_info': str(row.get('additional_info', ''))
                        })
                
                if valid_data:
                    # 세션 상태에 추가
                    if 'user_projects' not in st.session_state:
                        st.session_state.user_projects = []
                    
                    st.session_state.user_projects.extend(valid_data)
                    st.success(f"{len(valid_data)}개의 프로젝트가 성공적으로 추가되었습니다!")
                    st.rerun()
                else:
                    st.error("유효한 데이터가 없습니다.")
                    
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {str(e)}")
    
    # 샘플 CSV 다운로드
    st.markdown("---")
    st.subheader("샘플 CSV 템플릿")
    
    sample_data = {
        'name': ['샘플 프로젝트 1', '샘플 프로젝트 2'],
        'lat': [37.5665, 37.5172],
        'lon': [126.9780, 127.0473],
        'type': ['주거', '상업'],
        'size': ['대형', '중형'],
        'status': ['진행중', '계획'],
        'budget': [150, 80],  # 억원 단위
        'area': [25000, 12000],
        'start_date': ['2024-01-01', '2024-06-01'],
        'end_date': ['2025-12-31', '2025-08-31'],
        'additional_info': ['샘플 설명 1', '샘플 설명 2']
    }
    
    sample_df = pd.DataFrame(sample_data)
    sample_csv = sample_df.to_csv(index=False, encoding='utf-8-sig')
    
    st.download_button(
        label="샘플 CSV 다운로드",
        data=sample_csv,
        file_name="sample_projects.csv",
        mime="text/csv",
        help="이 템플릿을 사용하여 프로젝트 데이터를 준비하세요"
    )

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import numpy as np

# 페이지 설정
st.set_page_config(
    page_title="통계 대시보드",
    page_icon="📊",
    layout="wide"
)

# 제목
st.title("📊 통계 대시보드")
st.markdown("**프로젝트 분석 통계 및 시각화**")

# 샘플 데이터 생성 (실제로는 분석 결과에서 가져올 데이터)
@st.cache_data
def generate_sample_data():
    """샘플 통계 데이터 생성"""
    
    # 프로젝트 유형별 통계
    project_types = ['주거', '상업', '교육', '의료', '문화']
    project_counts = [25, 18, 12, 8, 7]
    
    # 월별 분석 통계
    months = pd.date_range('2024-01-01', periods=12, freq='M')
    monthly_analysis = [random.randint(10, 50) for _ in range(12)]
    
    # 분석 블록별 사용 통계
    analysis_blocks = ['기본 정보 추출', '요구사항 분석', '설계 제안', '비용 분석', '위험 분석']
    block_usage = [45, 38, 32, 28, 22]
    
    # 지역별 프로젝트 분포
    regions = ['서울', '경기', '부산', '대구', '인천', '광주', '대전', '울산']
    region_counts = [35, 28, 15, 12, 10, 8, 6, 4]
    
    return {
        'project_types': project_types,
        'project_counts': project_counts,
        'months': months,
        'monthly_analysis': monthly_analysis,
        'analysis_blocks': analysis_blocks,
        'block_usage': block_usage,
        'regions': regions,
        'region_counts': region_counts
    }

# 데이터 로드
data = generate_sample_data()

# 메인 대시보드
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="총 프로젝트 수",
        value="118",
        delta="12"
    )

with col2:
    st.metric(
        label="이번 달 분석",
        value="45",
        delta="8"
    )

with col3:
    st.metric(
        label="평균 분석 시간",
        value="3.2분",
        delta="-0.5분"
    )

with col4:
    st.metric(
        label="성공률",
        value="94.2%",
        delta="2.1%"
    )

st.markdown("---")

# 차트 섹션
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 프로젝트 유형별 분포")
    
    # 파이 차트
    fig_pie = px.pie(
        values=data['project_counts'],
        names=data['project_types'],
        title="프로젝트 유형별 분포"
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.subheader("📊 월별 분석 통계")
    
    # 라인 차트
    df_monthly = pd.DataFrame({
        '월': data['months'],
        '분석 수': data['monthly_analysis']
    })
    
    fig_line = px.line(
        df_monthly,
        x='월',
        y='분석 수',
        title="월별 분석 통계",
        markers=True
    )
    fig_line.update_xaxis(tickformat="%Y-%m")
    st.plotly_chart(fig_line, use_container_width=True)

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔧 분석 블록별 사용률")
    
    # 바 차트
    df_blocks = pd.DataFrame({
        '분석 블록': data['analysis_blocks'],
        '사용 횟수': data['block_usage']
    })
    
    fig_bar = px.bar(
        df_blocks,
        x='사용 횟수',
        y='분석 블록',
        orientation='h',
        title="분석 블록별 사용률",
        color='사용 횟수',
        color_continuous_scale='Blues'
    )
    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.subheader("🗺️ 지역별 프로젝트 분포")
    
    # 도넛 차트
    fig_donut = go.Figure(data=[go.Pie(
        labels=data['regions'],
        values=data['region_counts'],
        hole=0.3,
        textinfo='label+percent'
    )])
    fig_donut.update_layout(title="지역별 프로젝트 분포")
    st.plotly_chart(fig_donut, use_container_width=True)

st.markdown("---")

# 상세 통계 테이블
st.subheader("📋 상세 통계")

# 샘플 데이터프레임 생성
sample_stats = pd.DataFrame({
    '지표': ['총 프로젝트 수', '성공한 분석', '실패한 분석', '평균 분석 시간', '가장 많이 사용된 블록', '최근 분석일'],
    '값': ['118', '111', '7', '3.2분', '기본 정보 추출', '2024-09-15'],
    '변화': ['+12', '+8', '-2', '-0.5분', '→', '오늘']
})

st.dataframe(sample_stats, use_container_width=True)

# 필터 옵션
st.subheader("🔍 필터 옵션")

col1, col2, col3 = st.columns(3)

with col1:
    date_range = st.date_input(
        "분석 기간 선택",
        value=(datetime.now() - timedelta(days=30), datetime.now()),
        max_value=datetime.now()
    )

with col2:
    project_type_filter = st.multiselect(
        "프로젝트 유형",
        options=data['project_types'],
        default=data['project_types']
    )

with col3:
    region_filter = st.multiselect(
        "지역",
        options=data['regions'],
        default=data['regions']
    )

# 필터 적용된 결과 표시
if st.button("필터 적용"):
    st.success(f"✅ 필터가 적용되었습니다!")
    st.info(f"선택된 기간: {date_range[0]} ~ {date_range[1]}")
    st.info(f"선택된 프로젝트 유형: {', '.join(project_type_filter)}")
    st.info(f"선택된 지역: {', '.join(region_filter)}")

# 사이드바 - 추가 정보
with st.sidebar:
    st.header("📊 통계 정보")
    
    st.metric("오늘 분석", "12", "3")
    st.metric("이번 주 분석", "67", "15")
    st.metric("이번 달 분석", "245", "32")
    
    st.markdown("---")
    
    st.header("🏆 인기 분석 블록")
    for i, (block, usage) in enumerate(zip(data['analysis_blocks'], data['block_usage'])):
        st.write(f"{i+1}. {block}: {usage}회")
    
    st.markdown("---")
    
    st.header("📈 성과 지표")
    st.progress(0.942, text="성공률: 94.2%")
    st.progress(0.876, text="만족도: 87.6%")
    st.progress(0.923, text="정확도: 92.3%")

# 푸터
st.markdown("---")
st.markdown("**통계 대시보드** - 실시간 분석 통계 및 성과 지표")

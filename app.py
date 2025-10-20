import streamlit as st
import os
from dotenv import load_dotenv

# 환경변수 로드 (안전하게 처리)
try:
    load_dotenv()
except UnicodeDecodeError:
    # .env 파일에 인코딩 문제가 있는 경우 무시
    pass

# 페이지 설정
st.set_page_config(
    page_title="Urban ArchInsight - 교육용",
    page_icon=None,
    layout="wide"
)

# 제목
st.title("Urban ArchInsight")
st.markdown("**학생들을 위한 도시 프로젝트 분석 도구**")

# 메인 페이지 내용
st.markdown("""
## 주요 기능

### PDF 분석
- 도시 프로젝트 PDF 문서 업로드
- AI 기반 자동 분석 (Chain of Thought)
- 구조화된 분석 결과 제공

### 지도 분석
- 프로젝트 위치 정보
- 지역별 분석 데이터
- 지리적 인사이트 제공

### Midjourney 프롬프트 생성기
- 분석 결과를 기반으로 한 이미지 생성 프롬프트
- 도시 프로젝트 시각화를 위한 AI 아트 프롬프트
- 맞춤형 시각적 표현 지원

## 시작하기

왼쪽 사이드바에서 원하는 기능을 선택하세요:
- **PDF 분석**: 메인 분석 기능
- **지도**: 지리적 분석 및 매핑
- **Midjourney 프롬프트**: AI 아트 이미지 생성
""")

# API 키 상태 표시
st.sidebar.header("시스템 상태")

# Streamlit secrets와 환경변수 모두 확인

# Streamlit secrets에서 먼저 확인
api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    st.sidebar.error("ANTHROPIC_API_KEY가 설정되지 않았습니다!")
    st.sidebar.info("다음 중 하나의 방법으로 API 키를 설정해주세요:")
    st.sidebar.code("""
# 방법 1: .streamlit/secrets.toml 파일에 추가
[secrets]
ANTHROPIC_API_KEY = "your_api_key_here"

# 방법 2: .env 파일에 추가
ANTHROPIC_API_KEY=your_api_key_here
    """, language="toml")
else:
    st.sidebar.success("API 키가 설정되었습니다!")
    st.sidebar.info(f"API 키 길이: {len(api_key)}자")
    st.sidebar.info(f"키 소스: {'Streamlit Secrets' if st.secrets.get('ANTHROPIC_API_KEY') else '환경변수'}")

# 사용법 안내
st.sidebar.header("사용법")
st.sidebar.markdown("""
1. **PDF 분석**: PDF 문서를 업로드하고 분석 블록을 선택하세요
2. **통계**: 분석 결과를 시각적으로 확인하세요
3. **지도**: 프로젝트 위치와 관련 데이터를 지도에서 확인하세요
4. **사이트 데이터 수집**: 좌표를 입력하여 주변 도시 데이터를 자동 수집하세요
""")

# 푸터
st.markdown("---")
st.markdown("**Urban ArchInsight** - 도시 교육을 위한 AI 분석 도구")
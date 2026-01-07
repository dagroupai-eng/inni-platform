import streamlit as st
import os
from dotenv import load_dotenv

# dspy_analyzer 안전한 import 처리
try:
    from dspy_analyzer import PROVIDER_CONFIG, get_api_key
    DSPY_ANALYZER_AVAILABLE = True
except ImportError as e:
    DSPY_ANALYZER_AVAILABLE = False
    PROVIDER_CONFIG = {}
    get_api_key = None
    st.error("⚠️ 필수 모듈이 설치되지 않았습니다.")
    st.error(f"오류: {str(e)}")
    st.warning("""
    **해결 방법:**
    
    1. `install.bat`을 실행하여 모든 의존성을 설치하세요.
    2. 또는 다음 명령을 실행하세요:
       ```
       python -m pip install dspy-ai PyMuPDF python-docx geopandas
       ```
    3. 설치 후 앱을 다시 시작하세요.
    """)
    st.stop()
except Exception as e:
    DSPY_ANALYZER_AVAILABLE = False
    PROVIDER_CONFIG = {}
    get_api_key = None
    st.error(f"⚠️ 모듈 로드 중 오류가 발생했습니다: {str(e)}")
    st.warning("앱을 다시 시작하거나 `install.bat`을 실행해보세요.")
    st.stop()

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

# API 제공자 선택 (세션 상태 초기화)
if 'llm_provider' not in st.session_state:
    st.session_state.llm_provider = 'gemini'

# API 제공자 선택 (dspy_analyzer가 사용 가능한 경우에만)
if DSPY_ANALYZER_AVAILABLE and PROVIDER_CONFIG:
    st.sidebar.subheader("🤖 AI 모델 선택")
    provider_options = {
        provider: config.get('display_name', provider.title())
        for provider, config in PROVIDER_CONFIG.items()
    }
    selected_provider = st.sidebar.selectbox(
        "사용할 AI 모델:",
        options=list(provider_options.keys()),
        format_func=lambda x: provider_options[x],
        key='llm_provider',
        help="분석에 사용할 AI 모델을 선택합니다."
    )

    # 선택된 제공자 정보 표시
    provider_config = PROVIDER_CONFIG.get(selected_provider, {})
    provider_name = provider_config.get('display_name', selected_provider)
    model_name = provider_config.get('model', 'unknown')
    api_key_env = provider_config.get('api_key_env', '')

    st.sidebar.caption(f"모델: {model_name}")

    # 선택된 제공자의 API 키 확인
    if get_api_key:
        api_key = get_api_key(selected_provider)
    else:
        api_key = None
else:
    selected_provider = None
    provider_name = "N/A"
    model_name = "N/A"
    api_key_env = ""
    api_key = None

if DSPY_ANALYZER_AVAILABLE:
    if not api_key:
        st.sidebar.error(f"{provider_name} API 키가 설정되지 않았습니다!")
        st.sidebar.info(f"{api_key_env}를 설정해주세요.")
        st.sidebar.code(f"""
# .streamlit/secrets.toml 또는 .env 파일에 추가
{api_key_env} = "your_api_key_here"
        """, language="toml")
    else:
        st.sidebar.success(f"✅ {provider_name} API 키 설정됨")
        st.sidebar.info(f"키 길이: {len(api_key)}자")
        try:
            key_source = 'Streamlit Secrets' if st.secrets.get(api_key_env) else '환경변수'
        except:
            key_source = '환경변수'
        st.sidebar.caption(f"소스: {key_source}")
else:
    st.sidebar.warning("⚠️ AI 모델 기능을 사용할 수 없습니다.")

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


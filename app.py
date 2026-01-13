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
    # AI 모델 선택
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
    
    st.sidebar.markdown("---")
    
    # API 키 입력 섹션 (선택된 모델에 따라 동적으로 표시)
    if api_key_env:  # API 키가 필요한 모델인 경우
        st.sidebar.subheader("🔑 API 키 설정")
        
        # 세션 상태 초기화
        session_key = f'user_api_key_{api_key_env}'
        if session_key not in st.session_state:
            st.session_state[session_key] = ''
        
        # API 키 입력 필드
        user_input_key = st.sidebar.text_input(
            f"{api_key_env} 입력:",
            value=st.session_state[session_key],
            type="password",
            help=f"여기에 {provider_name} API 키를 입력하세요. 브라우저를 닫으면 자동으로 삭제됩니다.",
            key=f"api_key_input_{api_key_env}"
        )
        
        # 버튼 컬럼 (확인, 삭제)
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            # 확인 버튼
            if st.button("✅ 확인", key=f"confirm_key_{api_key_env}", use_container_width=True):
                if user_input_key.strip():
                    st.session_state[session_key] = user_input_key.strip()
                    st.sidebar.success("API 키가 등록되었습니다!")
                    st.rerun()
                else:
                    st.sidebar.error("API 키를 입력해주세요.")
        
        with col2:
            # 삭제 버튼 (키가 있을 때만 표시)
            if st.session_state[session_key]:
                if st.button("🗑️ 삭제", key=f"delete_key_{api_key_env}", use_container_width=True):
                    st.session_state[session_key] = ''
                    st.sidebar.info("API 키가 삭제되었습니다.")
                    st.rerun()
        
        # 안내 메시지
        if st.session_state[session_key]:
            st.sidebar.caption("ℹ️ 브라우저를 닫으면 API 키가 자동으로 삭제됩니다.")
        
        st.sidebar.markdown("---")

    # 선택된 제공자의 API 키 확인
    if get_api_key:
        api_key = get_api_key(selected_provider)
    else:
        api_key = None
    
    # API 키 상태 표시
    if api_key_env and not api_key:
        st.sidebar.warning(f"⚠️ {provider_name} API 키가 설정되지 않았습니다!")
        st.sidebar.info("위에 API 키를 입력하고 확인 버튼을 눌러주세요.")
    elif api_key:
        # 키 소스 확인
        current_session_key = f'user_api_key_{api_key_env}'
        try:
            if current_session_key in st.session_state and st.session_state[current_session_key]:
                key_source = '웹 입력'
            elif st.secrets.get(api_key_env):
                key_source = 'Streamlit Secrets'
            else:
                key_source = '환경변수'
        except:
            if current_session_key in st.session_state and st.session_state[current_session_key]:
                key_source = '웹 입력'
            else:
                key_source = '환경변수'
        
        st.sidebar.success(f"✅ {provider_name} API 키 설정됨")
        st.sidebar.info(f"키 길이: {len(api_key)}자")
        st.sidebar.caption(f"소스: {key_source}")
    elif not api_key_env:
        # API 키가 필요 없는 모델 (예: Vertex AI)
        st.sidebar.info(f"✅ {provider_name}는 API 키가 필요하지 않습니다.")
else:
    selected_provider = None
    provider_name = "N/A"
    model_name = "N/A"
    api_key_env = ""
    api_key = None
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


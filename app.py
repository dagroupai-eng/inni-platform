import streamlit as st
import os
from dotenv import load_dotenv

# 페이지 설정 (가장 먼저 호출해야 함)
st.set_page_config(
    page_title="Urban ArchInsight - 교육용",
    page_icon=None,
    layout="wide"
)

# 데이터베이스 및 인증 모듈 초기화
try:
    from database.init_db import init_database
    from database.db_manager import table_exists
    if not table_exists("users"):
        init_database()
except Exception as e:
    print(f"데이터베이스 초기화 경고: {e}")

# 인증 모듈 import
try:
    from auth.authentication import (
        is_authenticated, get_current_user, logout, login
    )
    AUTH_AVAILABLE = True
except ImportError as e:
    AUTH_AVAILABLE = False
    print(f"인증 모듈 로드 실패: {e}")

# 환경변수 로드 (안전하게 처리)
try:
    load_dotenv()
except UnicodeDecodeError:
    pass


def show_login_page():
    """로그인 페이지를 표시합니다."""
    st.title("Urban ArchInsight")
    st.markdown("**학생들을 위한 도시 프로젝트 분석 도구**")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.subheader("로그인")
        st.markdown("개인 번호를 입력하여 로그인하세요.")

        with st.form("login_form"):
            personal_number = st.text_input(
                "개인 번호",
                placeholder="예: ADMIN001",
                help="관리자에게 부여받은 개인 번호를 입력하세요."
            )

            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

        if submitted and personal_number:
            success, message = login(personal_number)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

        st.markdown("---")
        st.caption("개인 번호가 없으신가요? 관리자에게 문의하세요.")
        st.caption("기본 관리자 번호: ADMIN001")


def load_user_api_keys():
    """로그인한 사용자의 API 키를 DB에서 세션 상태로 로드합니다."""
    try:
        from security.api_key_manager import get_user_api_keys, get_user_api_key
        from auth.authentication import get_current_user_id
        from dspy_analyzer import PROVIDER_CONFIG

        user_id = get_current_user_id()
        if not user_id:
            return

        # 모든 제공자의 API 키 확인
        for provider, config in PROVIDER_CONFIG.items():
            api_key_env = config.get('api_key_env')
            if api_key_env:
                # DB에서 키 가져오기
                db_key = get_user_api_key(user_id, api_key_env)
                if db_key:
                    # 세션 상태에 로드
                    session_key = f'user_api_key_{api_key_env}'
                    st.session_state[session_key] = db_key
    except Exception as e:
        print(f"API 키 로드 오류: {e}")


def show_main_app():
    """메인 앱을 표시합니다 (로그인 후)."""
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
        return
    except Exception as e:
        DSPY_ANALYZER_AVAILABLE = False
        PROVIDER_CONFIG = {}
        get_api_key = None
        st.error(f"⚠️ 모듈 로드 중 오류가 발생했습니다: {str(e)}")
        st.warning("앱을 다시 시작하거나 `install.bat`을 실행해보세요.")
        return

    # DB에서 API 키 로드 (로그인 직후 한 번만)
    if 'api_keys_loaded' not in st.session_state:
        load_user_api_keys()
        st.session_state.api_keys_loaded = True

    # 사이드바: 사용자 정보 및 로그아웃
    user = get_current_user()
    with st.sidebar:
        st.success(f"로그인: {user.get('display_name', user.get('personal_number'))}")
        role_display = {"user": "일반", "team_lead": "팀리드", "admin": "관리자"}
        st.caption(f"역할: {role_display.get(user.get('role'), user.get('role'))}")
        if st.button("로그아웃", key="main_logout", use_container_width=True):
            logout()
            st.rerun()
        st.markdown("---")

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

    # API 제공자 선택 (세션 상태 초기화)
    if 'llm_provider' not in st.session_state:
        st.session_state.llm_provider = 'gemini_25flash'

    # API 제공자 선택 (dspy_analyzer가 사용 가능한 경우에만)
    if DSPY_ANALYZER_AVAILABLE and PROVIDER_CONFIG:
        # AI 모델 선택
        st.sidebar.subheader("AI 모델 선택")
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
        if api_key_env:
            st.sidebar.subheader("API 키 설정")

            # 세션 상태 초기화
            session_key = f'user_api_key_{api_key_env}'
            if session_key not in st.session_state:
                st.session_state[session_key] = ''

            # API 키 입력 필드
            user_input_key = st.sidebar.text_input(
                f"{api_key_env} 입력:",
                value=st.session_state[session_key],
                type="password",
                help=f"여기에 {provider_name} API 키를 입력하세요.",
                key=f"api_key_input_{api_key_env}"
            )

            # 버튼 컬럼 (확인, 삭제)
            col1, col2 = st.sidebar.columns(2)

            with col1:
                if st.button("확인", key=f"confirm_key_{api_key_env}", use_container_width=True):
                    if user_input_key.strip():
                        # 세션 상태에 저장
                        st.session_state[session_key] = user_input_key.strip()

                        # DB에도 암호화하여 저장
                        try:
                            from security.api_key_manager import save_user_api_key
                            user_id = user.get('id')
                            if user_id:
                                if save_user_api_key(user_id, api_key_env, user_input_key.strip()):
                                    st.sidebar.success("API 키가 안전하게 저장되었습니다!")
                                else:
                                    st.sidebar.warning("API 키 저장에 실패했습니다.")
                        except Exception as e:
                            st.sidebar.warning(f"DB 저장 오류: {e}")

                        st.rerun()
                    else:
                        st.sidebar.error("API 키를 입력해주세요.")

            with col2:
                if st.session_state[session_key]:
                    if st.button("삭제", key=f"delete_key_{api_key_env}", use_container_width=True):
                        # 세션 상태에서 삭제
                        st.session_state[session_key] = ''

                        # DB에서도 삭제
                        try:
                            from security.api_key_manager import delete_user_api_key
                            user_id = user.get('id')
                            if user_id:
                                delete_user_api_key(user_id, api_key_env)
                        except Exception:
                            pass

                        st.sidebar.info("API 키 삭제됨")
                        st.rerun()

            st.sidebar.markdown("---")

        # 선택된 제공자의 API 키 확인
        if get_api_key:
            api_key = get_api_key(selected_provider)
        else:
            api_key = None

        # API 키 상태 표시
        if api_key_env and not api_key:
            st.sidebar.warning(f"⚠️ {provider_name} API 키 필요")
        elif api_key:
            st.sidebar.success(f"✅ {provider_name} API 키 설정됨")
        elif not api_key_env:
            st.sidebar.info(f"✅ {provider_name}는 API 키 불필요")
    else:
        st.sidebar.warning("⚠️ AI 모델 기능 사용 불가")

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


# 메인 로직
if AUTH_AVAILABLE:
    if is_authenticated():
        show_main_app()
    else:
        show_login_page()
else:
    st.error("인증 시스템을 사용할 수 없습니다.")
    st.info("database, auth 모듈이 올바르게 설치되어 있는지 확인하세요.")

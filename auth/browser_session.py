"""
브라우저 세션 유지 모듈
JavaScript를 사용하여 localStorage에 세션 저장
"""

import streamlit as st
import streamlit.components.v1 as components
from typing import Optional
import json


def save_session_to_browser(session_token: str):
    """
    세션 토큰을 브라우저 localStorage에 저장합니다.

    Args:
        session_token: 저장할 세션 토큰
    """
    if not session_token:
        return

    # JavaScript로 localStorage에 저장 (즉시 실행)
    save_script = f"""
    <script>
        localStorage.setItem('pms_session_token', '{session_token}');
    </script>
    """
    components.html(save_script, height=0, width=0)


def load_session_from_browser() -> Optional[str]:
    """
    브라우저 localStorage에서 세션 토큰을 로드합니다.

    Returns:
        저장된 세션 토큰 또는 None
    """
    # 이미 복원했으면 스킵
    if hasattr(st.session_state, '_browser_session_loaded'):
        return st.session_state.get('_loaded_token')

    # JavaScript로 localStorage에서 읽기
    load_script = """
    <script>
        const token = localStorage.getItem('pms_session_token');
        const data = {token: token};
        window.parent.postMessage({type: 'streamlit:setComponentValue', data: data}, '*');
    </script>
    """

    result = components.html(load_script, height=0, width=0)

    # 결과 저장
    st.session_state._browser_session_loaded = True
    if result and isinstance(result, dict):
        token = result.get('token')
        st.session_state._loaded_token = token
        return token

    return None


def clear_session_from_browser():
    """
    브라우저 localStorage에서 세션 토큰을 삭제합니다.
    """
    clear_script = """
    <script>
        localStorage.removeItem('pms_session_token');
    </script>
    """
    components.html(clear_script, height=0, width=0)


def init_browser_session():
    """
    페이지 로드 시 URL에서 세션을 복원합니다.
    app.py 시작 부분에서 호출하세요.
    """
    # 세션 상태에 이미 토큰이 있으면 스킵
    if 'pms_session_token' in st.session_state and st.session_state.pms_session_token:
        return

    # URL에서 토큰 로드
    token = load_session_from_url()

    if token:
        # 세션 유효성 확인
        from auth.session_manager import get_session
        from auth.user_manager import get_user_by_id

        session_data = get_session(token)
        if session_data:
            # 유효한 세션이면 복원
            st.session_state.pms_session_token = token

            # 사용자 정보도 복원
            user_id = session_data.get("user_id")
            if user_id:
                user = get_user_by_id(user_id)
                if user:
                    st.session_state.pms_current_user = user

                    # API 키도 복원
                    try:
                        from security.api_key_manager import get_user_api_key
                        from dspy_analyzer import PROVIDER_CONFIG

                        for provider, config in PROVIDER_CONFIG.items():
                            api_key_env = config.get('api_key_env')
                            if api_key_env:
                                db_key = get_user_api_key(user_id, api_key_env)
                                if db_key:
                                    session_key = f'user_api_key_{api_key_env}'
                                    st.session_state[session_key] = db_key
                    except:
                        pass

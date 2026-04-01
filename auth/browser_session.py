"""
브라우저 세션 유지 모듈
JavaScript를 사용하여 localStorage에 세션 저장/삭제
실제 복원 로직은 auth/session_init.py의 restore_login_session()이 담당
"""

from typing import Optional


def save_session_to_browser(session_token: str):
    """
    세션 토큰을 브라우저 localStorage에 저장합니다.

    Args:
        session_token: 저장할 세션 토큰
    """
    if not session_token:
        return

    # st_javascript로 저장 — components.html은 iframe(별도 포트)에서 실행돼
    # 메인 페이지 localStorage와 분리되므로 반드시 st_javascript 사용
    try:
        from streamlit_javascript import st_javascript
        safe_token = session_token.replace("'", "\\'")
        st_javascript(f"localStorage.setItem('pms_session_token', '{safe_token}'); 1")
    except Exception as e:
        print(f"[BrowserSession] localStorage 저장 오류: {e}")


def clear_session_from_browser():
    """
    브라우저 localStorage에서 세션 토큰을 삭제합니다.
    """
    try:
        from streamlit_javascript import st_javascript
        st_javascript("localStorage.removeItem('pms_session_token'); 1")
    except Exception as e:
        print(f"[BrowserSession] localStorage 삭제 오류: {e}")

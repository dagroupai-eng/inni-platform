"""
인증 모듈
로그인, 로그아웃, 인증 상태 확인
"""

from typing import Optional, Dict, Any, Callable
from functools import wraps

from auth.session_manager import create_session, get_session, delete_session
from auth.user_manager import (
    get_user_by_personal_number,
    update_last_login,
    UserStatus,
    create_user,
    UserRole
)


# Streamlit 세션 상태 키
SESSION_TOKEN_KEY = "pms_session_token"
CURRENT_USER_KEY = "pms_current_user"


def _get_streamlit_session():
    """Streamlit 세션 상태를 가져옵니다."""
    try:
        import streamlit as st
        return st.session_state
    except ImportError:
        return {}


def login(personal_number: str, auto_create: bool = False) -> tuple[bool, str]:
    """
    개인 번호로 로그인합니다.

    Args:
        personal_number: 개인 번호
        auto_create: True면 사용자가 없을 때 자동 생성

    Returns:
        (성공 여부, 메시지)
    """
    if not personal_number or not personal_number.strip():
        return False, "개인 번호를 입력해주세요."

    personal_number = personal_number.strip().upper()

    # 사용자 조회
    user = get_user_by_personal_number(personal_number)

    if not user:
        if auto_create:
            # 자동 생성 모드 (첫 로그인 시 계정 생성)
            user_id = create_user(personal_number)
            if user_id:
                user = get_user_by_personal_number(personal_number)
            else:
                return False, "계정 생성에 실패했습니다."
        else:
            return False, "등록되지 않은 개인 번호입니다. 관리자에게 문의하세요."

    # 상태 확인
    if user.get("status") != UserStatus.ACTIVE.value:
        return False, "비활성화된 계정입니다. 관리자에게 문의하세요."

    # 세션 생성
    session_token = create_session(
        user_id=user["id"],
        personal_number=personal_number,
        extra_data={
            "display_name": user.get("display_name"),
            "role": user.get("role"),
            "team_id": user.get("team_id")
        }
    )

    # 마지막 로그인 시간 업데이트
    update_last_login(user["id"])

    # Streamlit 세션에 저장
    st_session = _get_streamlit_session()
    st_session[SESSION_TOKEN_KEY] = session_token
    st_session[CURRENT_USER_KEY] = user

    # 로컬 파일 저장 제거 (멀티유저 환경에서 세션 충돌 방지)
    # Streamlit Cloud에서는 각 브라우저 세션이 독립적이므로 파일 기반 세션 불필요
    # try:
    #     from pathlib import Path
    #     from config.settings import DATA_DIR
    #     last_session_file = DATA_DIR / "last_session.txt"
    #     with open(last_session_file, 'w') as f:
    #         f.write(session_token)
    # except Exception as e:
    #     print(f"세션 파일 저장 오류: {e}")

    return True, f"환영합니다, {user.get('display_name', personal_number)}님!"


def logout() -> bool:
    """
    로그아웃합니다.

    Returns:
        성공 여부
    """
    st_session = _get_streamlit_session()

    # 세션 토큰 가져오기
    session_token = st_session.get(SESSION_TOKEN_KEY)

    # 파일 세션 삭제
    if session_token:
        delete_session(session_token)

    # Streamlit 세션에서 인증 정보 제거
    if SESSION_TOKEN_KEY in st_session:
        del st_session[SESSION_TOKEN_KEY]
    if CURRENT_USER_KEY in st_session:
        del st_session[CURRENT_USER_KEY]

    # API 키 세션 상태 클리어
    keys_to_remove = [key for key in st_session.keys() if key.startswith('user_api_key_')]
    for key in keys_to_remove:
        del st_session[key]

    # API 키 로드 플래그 제거
    if 'api_keys_loaded' in st_session:
        del st_session['api_keys_loaded']

    # 로컬 파일 삭제 제거 (멀티유저 환경에서 세션 충돌 방지)
    # try:
    #     from pathlib import Path
    #     from config.settings import DATA_DIR
    #     last_session_file = DATA_DIR / "last_session.txt"
    #     if last_session_file.exists():
    #         last_session_file.unlink()
    # except Exception as e:
    #     print(f"세션 파일 삭제 오류: {e}")

    return True


def is_authenticated() -> bool:
    """
    현재 사용자가 인증되었는지 확인합니다.

    Returns:
        인증 여부
    """
    st_session = _get_streamlit_session()
    session_token = st_session.get(SESSION_TOKEN_KEY)

    if not session_token:
        return False

    # 세션 유효성 확인
    session_data = get_session(session_token)
    if not session_data:
        # 유효하지 않은 세션 정리
        if SESSION_TOKEN_KEY in st_session:
            del st_session[SESSION_TOKEN_KEY]
        if CURRENT_USER_KEY in st_session:
            del st_session[CURRENT_USER_KEY]
        return False

    # 사용자 정보가 세션에 없으면 복원
    if CURRENT_USER_KEY not in st_session:
        user_id = session_data.get("user_id")
        if user_id:
            from auth.user_manager import get_user_by_id
            user = get_user_by_id(user_id)
            if user:
                st_session[CURRENT_USER_KEY] = user

    return True


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    현재 로그인한 사용자 정보를 가져옵니다.

    Returns:
        사용자 정보 또는 None
    """
    if not is_authenticated():
        return None

    st_session = _get_streamlit_session()
    return st_session.get(CURRENT_USER_KEY)


def get_current_user_id() -> Optional[int]:
    """현재 로그인한 사용자 ID를 가져옵니다."""
    user = get_current_user()
    return user.get("id") if user else None


def get_current_user_role() -> Optional[str]:
    """현재 로그인한 사용자의 역할을 가져옵니다."""
    user = get_current_user()
    return user.get("role") if user else None


def is_current_user_admin() -> bool:
    """현재 사용자가 관리자인지 확인합니다."""
    role = get_current_user_role()
    return role == UserRole.ADMIN.value


def is_current_user_team_lead() -> bool:
    """현재 사용자가 팀 리드 이상인지 확인합니다."""
    role = get_current_user_role()
    return role in [UserRole.TEAM_LEAD.value, UserRole.ADMIN.value]


def require_auth(redirect_to_login: bool = True):
    """
    인증이 필요한 페이지를 위한 데코레이터

    Args:
        redirect_to_login: True면 로그인 페이지로 리다이렉트

    Usage:
        @require_auth()
        def protected_page():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                try:
                    import streamlit as st
                    st.warning("로그인이 필요합니다. 메인 페이지에서 로그인해주세요.")
                    st.stop()
                except ImportError:
                    raise PermissionError("Authentication required")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(func: Callable):
    """관리자 권한이 필요한 함수를 위한 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_current_user_admin():
            try:
                import streamlit as st
                st.error("관리자 권한이 필요합니다.")
                st.stop()
            except ImportError:
                raise PermissionError("Admin permission required")
        return func(*args, **kwargs)
    return wrapper


def require_team_lead(func: Callable):
    """팀 리드 이상 권한이 필요한 함수를 위한 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_current_user_team_lead():
            try:
                import streamlit as st
                st.error("팀 리드 이상 권한이 필요합니다.")
                st.stop()
            except ImportError:
                raise PermissionError("Team lead permission required")
        return func(*args, **kwargs)
    return wrapper


def check_page_access():
    """
    페이지 접근 권한을 확인하고 필요시 로그인 페이지로 리다이렉트합니다.
    페이지 상단에서 호출하세요.
    """
    if not is_authenticated():
        try:
            import streamlit as st
            st.warning("로그인이 필요합니다.")
            st.info("사이드바에서 '로그인' 페이지로 이동하여 로그인해주세요.")
            st.stop()
        except ImportError:
            raise PermissionError("Authentication required")

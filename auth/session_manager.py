"""
파일 기반 세션 관리자
JSON 파일로 세션 데이터 저장
"""

import json
import secrets
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from config.settings import SESSIONS_DIR, SESSION_TTL_HOURS, SESSION_TOKEN_LENGTH


def _get_session_path(session_token: str) -> Path:
    """세션 토큰에 해당하는 파일 경로를 반환합니다."""
    return SESSIONS_DIR / f"{session_token}.json"


def generate_session_token() -> str:
    """안전한 세션 토큰을 생성합니다."""
    return secrets.token_urlsafe(SESSION_TOKEN_LENGTH)


def create_session(user_id: int, personal_number: str, extra_data: Optional[Dict[str, Any]] = None) -> str:
    """
    새 세션을 생성합니다.

    Args:
        user_id: 사용자 ID
        personal_number: 개인 번호
        extra_data: 추가 세션 데이터

    Returns:
        세션 토큰
    """
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    token = generate_session_token()
    session_data = {
        "user_id": user_id,
        "personal_number": personal_number,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=SESSION_TTL_HOURS)).isoformat(),
        "last_activity": datetime.now().isoformat()
    }

    if extra_data:
        session_data.update(extra_data)

    session_path = _get_session_path(token)
    with open(session_path, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    return token


def get_session(session_token: str) -> Optional[Dict[str, Any]]:
    """
    세션 데이터를 가져옵니다.
    만료된 세션은 삭제하고 None을 반환합니다.

    Args:
        session_token: 세션 토큰

    Returns:
        세션 데이터 또는 None
    """
    session_path = _get_session_path(session_token)

    if not session_path.exists():
        return None

    try:
        with open(session_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        # 만료 확인
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if datetime.now() > expires_at:
            delete_session(session_token)
            return None

        # 마지막 활동 시간 업데이트
        session_data["last_activity"] = datetime.now().isoformat()
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

        return session_data

    except (json.JSONDecodeError, KeyError, ValueError):
        # 손상된 세션 파일 삭제
        delete_session(session_token)
        return None


def update_session(session_token: str, data: Dict[str, Any]) -> bool:
    """
    세션 데이터를 업데이트합니다.

    Args:
        session_token: 세션 토큰
        data: 업데이트할 데이터

    Returns:
        성공 여부
    """
    session_data = get_session(session_token)
    if not session_data:
        return False

    session_data.update(data)
    session_data["last_activity"] = datetime.now().isoformat()

    session_path = _get_session_path(session_token)
    with open(session_path, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    return True


def delete_session(session_token: str) -> bool:
    """
    세션을 삭제합니다.

    Args:
        session_token: 세션 토큰

    Returns:
        성공 여부
    """
    session_path = _get_session_path(session_token)

    if session_path.exists():
        try:
            os.remove(session_path)
            return True
        except OSError:
            return False
    return False


def extend_session(session_token: str, hours: int = SESSION_TTL_HOURS) -> bool:
    """
    세션 만료 시간을 연장합니다.

    Args:
        session_token: 세션 토큰
        hours: 연장할 시간 (기본값: SESSION_TTL_HOURS)

    Returns:
        성공 여부
    """
    session_data = get_session(session_token)
    if not session_data:
        return False

    session_data["expires_at"] = (datetime.now() + timedelta(hours=hours)).isoformat()

    return update_session(session_token, session_data)


def cleanup_expired_sessions():
    """만료된 세션 파일들을 정리합니다."""
    if not SESSIONS_DIR.exists():
        return

    deleted_count = 0
    for session_file in SESSIONS_DIR.glob("*.json"):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            expires_at = datetime.fromisoformat(session_data.get("expires_at", ""))
            if datetime.now() > expires_at:
                os.remove(session_file)
                deleted_count += 1
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            # 손상된 파일 삭제
            try:
                os.remove(session_file)
                deleted_count += 1
            except OSError:
                pass

    if deleted_count > 0:
        print(f"Cleaned up {deleted_count} expired sessions.")


def get_active_sessions_count() -> int:
    """활성 세션 수를 반환합니다."""
    if not SESSIONS_DIR.exists():
        return 0

    count = 0
    now = datetime.now()

    for session_file in SESSIONS_DIR.glob("*.json"):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            expires_at = datetime.fromisoformat(session_data.get("expires_at", ""))
            if now <= expires_at:
                count += 1
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    return count

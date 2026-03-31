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


def _save_session_supabase(user_id: int, token: str, session_data: dict):
    """세션 토큰을 Supabase user_settings에 저장합니다."""
    try:
        from database.db_manager import execute_query
        import json as _json

        rows = execute_query(
            "SELECT settings_data FROM user_settings WHERE user_id = ?",
            (user_id,)
        )
        if rows and rows[0]:
            raw = rows[0]['settings_data']
            settings = _json.loads(raw) if isinstance(raw, str) else (raw or {})
        else:
            settings = {}

        settings['_session'] = {
            'token': token,
            'user_id': user_id,
            'personal_number': session_data.get('personal_number'),
            'display_name': session_data.get('display_name'),
            'role': session_data.get('role'),
            'team_id': session_data.get('team_id'),
            'expires_at': session_data.get('expires_at'),
        }

        execute_query(
            "INSERT OR REPLACE INTO user_settings (user_id, settings_data, updated_at) VALUES (?, ?, ?)",
            (user_id, _json.dumps(settings, ensure_ascii=False), datetime.now().isoformat()),
            commit=True
        )
    except Exception as e:
        print(f"[Session] Supabase 세션 저장 오류: {e}")


def _clear_session_supabase(user_id: int):
    """Supabase user_settings에서 _session 키를 제거합니다 (로그아웃 시 호출)."""
    try:
        from database.db_manager import execute_query
        import json as _json

        rows = execute_query(
            "SELECT settings_data FROM user_settings WHERE user_id = ?",
            (user_id,)
        )
        if rows and rows[0]:
            raw = rows[0]['settings_data']
            settings = _json.loads(raw) if isinstance(raw, str) else (raw or {})
            settings.pop('_session', None)
            execute_query(
                "INSERT OR REPLACE INTO user_settings (user_id, settings_data, updated_at) VALUES (?, ?, ?)",
                (user_id, _json.dumps(settings, ensure_ascii=False), datetime.now().isoformat()),
                commit=True
            )
    except Exception as e:
        print(f"[Session] Supabase 세션 정리 오류: {e}")


def _get_session_supabase(token: str) -> Optional[Dict[str, Any]]:
    """Supabase user_settings에서 토큰으로 세션을 조회합니다."""
    try:
        from database.supabase_client import get_supabase_client

        client = get_supabase_client()
        result = client.table('user_settings').select('user_id, settings_data').execute()

        for row in (result.data or []):
            settings = row.get('settings_data') or {}
            session = settings.get('_session') or {}
            if session.get('token') == token:
                expires_at = session.get('expires_at')
                if expires_at and datetime.fromisoformat(expires_at) > datetime.now():
                    return session
        return None
    except Exception as e:
        print(f"[Session] Supabase 세션 조회 오류: {e}")
        return None


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

    # 로컬 파일 저장 (현재 프로세스 내 빠른 조회용)
    session_path = _get_session_path(token)
    with open(session_path, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    # Supabase 저장 (서버 재시작 후 복원용)
    _save_session_supabase(user_id, token, session_data)

    return token


def get_session(session_token: str) -> Optional[Dict[str, Any]]:
    """
    세션 데이터를 가져옵니다.
    로컬 파일 → Supabase 순서로 조회합니다.

    Args:
        session_token: 세션 토큰

    Returns:
        세션 데이터 또는 None
    """
    session_path = _get_session_path(session_token)

    # 1. 로컬 파일 조회 (현재 프로세스 내 빠른 경로)
    if session_path.exists():
        try:
            with open(session_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            expires_at = datetime.fromisoformat(session_data["expires_at"])
            if datetime.now() > expires_at:
                delete_session(session_token)
            else:
                session_data["last_activity"] = datetime.now().isoformat()
                with open(session_path, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2)
                return session_data

        except (json.JSONDecodeError, KeyError, ValueError):
            delete_session(session_token)

    # 2. Supabase 폴백 (서버 재시작 후 로컬 파일 없을 때)
    return _get_session_supabase(session_token)


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
    세션을 삭제합니다. 로컬 파일 + Supabase _session 모두 정리합니다.

    Args:
        session_token: 세션 토큰

    Returns:
        성공 여부
    """
    session_path = _get_session_path(session_token)

    # 로컬 파일에서 user_id 먼저 확인 (Supabase 정리에 필요)
    user_id = None
    if session_path.exists():
        try:
            with open(session_path, 'r', encoding='utf-8') as f:
                user_id = json.load(f).get('user_id')
        except Exception:
            pass

    # 로컬 파일 삭제
    deleted = False
    if session_path.exists():
        try:
            os.remove(session_path)
            deleted = True
        except OSError:
            return False

    # Supabase _session 무효화
    if user_id:
        _clear_session_supabase(user_id)

    return deleted


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

"""
Supabase 클라이언트 싱글턴 모듈
service_role 키를 사용하여 RLS 바이패스
"""

from typing import Optional

_client = None


def get_supabase_client():
    """Supabase 클라이언트를 반환합니다 (싱글턴)."""
    global _client
    if _client is None:
        from supabase import create_client
        from config.settings import get_secret

        url = get_secret("SUPABASE_URL")
        key = get_secret("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY가 설정되지 않았습니다. "
                "환경변수 또는 Streamlit secrets에 설정하세요."
            )

        _client = create_client(url, key)
    return _client


def is_supabase_available() -> bool:
    """Supabase 연결이 가능한지 확인합니다."""
    try:
        client = get_supabase_client()
        client.table("users").select("id").limit(1).execute()
        return True
    except Exception:
        return False

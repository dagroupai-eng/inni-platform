"""
API 키 관리 모듈
사용자별 API 키의 안전한 저장 및 조회
"""

from typing import Optional, Dict, Any, List

from database.db_manager import execute_query, get_last_insert_id
from security.encryption import encrypt_value, decrypt_value


def save_user_api_key(user_id: int, key_name: str, key_value: str) -> bool:
    """
    사용자의 API 키를 암호화하여 저장합니다.

    Args:
        user_id: 사용자 ID
        key_name: API 키 이름 (예: GEMINI_API_KEY)
        key_value: API 키 값

    Returns:
        성공 여부
    """
    try:
        # 암호화
        encrypted_value, iv = encrypt_value(key_value)

        # 기존 키가 있으면 업데이트, 없으면 삽입
        existing = execute_query(
            "SELECT id FROM api_keys WHERE user_id = ? AND key_name = ?",
            (user_id, key_name)
        )

        if existing:
            execute_query(
                """
                UPDATE api_keys
                SET encrypted_value = ?, encryption_iv = ?
                WHERE user_id = ? AND key_name = ?
                """,
                (encrypted_value, iv, user_id, key_name),
                commit=True
            )
        else:
            execute_query(
                """
                INSERT INTO api_keys (user_id, key_name, encrypted_value, encryption_iv)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, key_name, encrypted_value, iv),
                commit=True
            )

        return True
    except Exception as e:
        print(f"API 키 저장 오류: {e}")
        return False


def get_user_api_key(user_id: int, key_name: str) -> Optional[str]:
    """
    사용자의 API 키를 복호화하여 조회합니다.

    Args:
        user_id: 사용자 ID
        key_name: API 키 이름

    Returns:
        API 키 값 또는 None
    """
    try:
        result = execute_query(
            """
            SELECT encrypted_value, encryption_iv
            FROM api_keys
            WHERE user_id = ? AND key_name = ?
            """,
            (user_id, key_name)
        )

        if result:
            row = result[0]
            return decrypt_value(row["encrypted_value"], row["encryption_iv"])

        return None
    except Exception as e:
        print(f"API 키 조회 오류: {e}")
        return None


def get_user_api_keys(user_id: int) -> List[Dict[str, Any]]:
    """
    사용자의 모든 API 키 목록을 조회합니다.
    (키 값은 포함하지 않음)

    Args:
        user_id: 사용자 ID

    Returns:
        API 키 정보 목록 [{"id": ..., "key_name": ...}, ...]
    """
    try:
        result = execute_query(
            "SELECT id, key_name FROM api_keys WHERE user_id = ?",
            (user_id,)
        )
        return [dict(row) for row in result]
    except Exception as e:
        print(f"API 키 목록 조회 오류: {e}")
        return []


def delete_user_api_key(user_id: int, key_name: str) -> bool:
    """
    사용자의 API 키를 삭제합니다.

    Args:
        user_id: 사용자 ID
        key_name: API 키 이름

    Returns:
        성공 여부
    """
    try:
        execute_query(
            "DELETE FROM api_keys WHERE user_id = ? AND key_name = ?",
            (user_id, key_name),
            commit=True
        )
        return True
    except Exception as e:
        print(f"API 키 삭제 오류: {e}")
        return False


def get_api_key_for_current_user(key_name: str) -> Optional[str]:
    """
    현재 로그인한 사용자의 API 키를 조회합니다.

    Args:
        key_name: API 키 이름

    Returns:
        API 키 값 또는 None
    """
    try:
        from auth.authentication import get_current_user_id
        user_id = get_current_user_id()

        if user_id:
            return get_user_api_key(user_id, key_name)
        return None
    except ImportError:
        return None


def has_api_key(user_id: int, key_name: str) -> bool:
    """
    사용자가 특정 API 키를 가지고 있는지 확인합니다.

    Args:
        user_id: 사용자 ID
        key_name: API 키 이름

    Returns:
        키 존재 여부
    """
    result = execute_query(
        "SELECT 1 FROM api_keys WHERE user_id = ? AND key_name = ?",
        (user_id, key_name)
    )
    return len(result) > 0

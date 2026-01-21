"""
사용자 관리 모듈
사용자 CRUD 및 권한 관리
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime

from database.db_manager import execute_query, get_last_insert_id


class UserRole(Enum):
    """사용자 역할"""
    USER = "user"
    TEAM_LEAD = "team_lead"
    ADMIN = "admin"


class UserStatus(Enum):
    """사용자 상태"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    ID로 사용자를 조회합니다.

    Args:
        user_id: 사용자 ID

    Returns:
        사용자 정보 딕셔너리 또는 None
    """
    result = execute_query(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    )

    if result:
        return dict(result[0])
    return None


def get_user_by_personal_number(personal_number: str) -> Optional[Dict[str, Any]]:
    """
    개인 번호로 사용자를 조회합니다.

    Args:
        personal_number: 개인 번호

    Returns:
        사용자 정보 딕셔너리 또는 None
    """
    result = execute_query(
        "SELECT * FROM users WHERE personal_number = ?",
        (personal_number,)
    )

    if result:
        return dict(result[0])
    return None


def create_user(
    personal_number: str,
    display_name: Optional[str] = None,
    role: UserRole = UserRole.USER,
    team_id: Optional[int] = None,
    status: UserStatus = UserStatus.ACTIVE
) -> Optional[int]:
    """
    새 사용자를 생성합니다.

    Args:
        personal_number: 개인 번호 (고유)
        display_name: 표시 이름
        role: 사용자 역할
        team_id: 소속 팀 ID
        status: 사용자 상태

    Returns:
        생성된 사용자 ID 또는 None (실패 시)
    """
    # 중복 확인
    existing = get_user_by_personal_number(personal_number)
    if existing:
        return None

    if display_name is None:
        display_name = personal_number

    try:
        execute_query(
            """
            INSERT INTO users (personal_number, display_name, role, team_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                personal_number,
                display_name,
                role.value if isinstance(role, UserRole) else role,
                team_id,
                status.value if isinstance(status, UserStatus) else status,
                datetime.now().isoformat()
            ),
            commit=True
        )
        return get_last_insert_id()
    except Exception as e:
        print(f"Error creating user: {e}")
        return None


def update_user(user_id: int, **kwargs) -> bool:
    """
    사용자 정보를 업데이트합니다.

    Args:
        user_id: 사용자 ID
        **kwargs: 업데이트할 필드 (display_name, role, team_id, status)

    Returns:
        성공 여부
    """
    allowed_fields = ["display_name", "role", "team_id", "status"]
    update_fields = []
    values = []

    for field, value in kwargs.items():
        if field in allowed_fields:
            update_fields.append(f"{field} = ?")
            if isinstance(value, (UserRole, UserStatus)):
                values.append(value.value)
            else:
                values.append(value)

    if not update_fields:
        return False

    values.append(user_id)

    try:
        execute_query(
            f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?",
            tuple(values),
            commit=True
        )
        return True
    except Exception as e:
        print(f"Error updating user: {e}")
        return False


def update_last_login(user_id: int) -> bool:
    """
    사용자의 마지막 로그인 시간을 업데이트합니다.

    Args:
        user_id: 사용자 ID

    Returns:
        성공 여부
    """
    try:
        execute_query(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now().isoformat(), user_id),
            commit=True
        )
        return True
    except Exception as e:
        print(f"Error updating last login: {e}")
        return False


def delete_user(user_id: int) -> bool:
    """
    사용자를 삭제합니다.

    Args:
        user_id: 사용자 ID

    Returns:
        성공 여부
    """
    try:
        execute_query(
            "DELETE FROM users WHERE id = ?",
            (user_id,),
            commit=True
        )
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False


def get_all_users(
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    team_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    사용자 목록을 조회합니다.

    Args:
        role: 역할 필터
        status: 상태 필터
        team_id: 팀 ID 필터

    Returns:
        사용자 목록
    """
    query = "SELECT * FROM users WHERE 1=1"
    params = []

    if role:
        query += " AND role = ?"
        params.append(role.value if isinstance(role, UserRole) else role)

    if status:
        query += " AND status = ?"
        params.append(status.value if isinstance(status, UserStatus) else status)

    if team_id is not None:
        query += " AND team_id = ?"
        params.append(team_id)

    query += " ORDER BY created_at DESC"

    result = execute_query(query, tuple(params) if params else None)
    return [dict(row) for row in result]


def get_user_count() -> int:
    """총 사용자 수를 반환합니다."""
    result = execute_query("SELECT COUNT(*) as count FROM users")
    return result[0]["count"] if result else 0


def is_admin(user_id: int) -> bool:
    """사용자가 관리자인지 확인합니다."""
    user = get_user_by_id(user_id)
    return user is not None and user.get("role") == UserRole.ADMIN.value


def is_team_lead(user_id: int) -> bool:
    """사용자가 팀 리드인지 확인합니다."""
    user = get_user_by_id(user_id)
    return user is not None and user.get("role") in [UserRole.TEAM_LEAD.value, UserRole.ADMIN.value]


# 팀 관련 함수들
def get_team_by_id(team_id: int) -> Optional[Dict[str, Any]]:
    """팀 정보를 조회합니다."""
    result = execute_query(
        "SELECT * FROM teams WHERE id = ?",
        (team_id,)
    )
    return dict(result[0]) if result else None


def create_team(name: str, description: Optional[str] = None) -> Optional[int]:
    """새 팀을 생성합니다."""
    try:
        execute_query(
            "INSERT INTO teams (name, description, created_at) VALUES (?, ?, ?)",
            (name, description, datetime.now().isoformat()),
            commit=True
        )
        return get_last_insert_id()
    except Exception as e:
        print(f"Error creating team: {e}")
        return None


def get_all_teams() -> List[Dict[str, Any]]:
    """모든 팀 목록을 조회합니다."""
    result = execute_query("SELECT * FROM teams ORDER BY name")
    return [dict(row) for row in result]


def get_team_members(team_id: int) -> List[Dict[str, Any]]:
    """팀 멤버 목록을 조회합니다."""
    result = execute_query(
        "SELECT * FROM users WHERE team_id = ? ORDER BY display_name",
        (team_id,)
    )
    return [dict(row) for row in result]

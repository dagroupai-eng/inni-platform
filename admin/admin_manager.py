"""
관리자 기능 모듈
사용자, 팀, 시스템 관리 기능
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from database.db_manager import execute_query, get_last_insert_id
from auth.user_manager import (
    get_all_users,
    create_user,
    update_user,
    delete_user,
    get_all_teams,
    create_team,
    get_team_members,
    UserRole,
    UserStatus
)
from auth.session_manager import get_active_sessions_count, cleanup_expired_sessions


def get_system_stats() -> Dict[str, Any]:
    """
    시스템 통계를 가져옵니다.

    Returns:
        통계 딕셔너리
    """
    # 사용자 통계
    users_result = execute_query("SELECT COUNT(*) as count FROM users")
    total_users = users_result[0]["count"] if users_result else 0

    active_users_result = execute_query(
        "SELECT COUNT(*) as count FROM users WHERE status = 'active'"
    )
    active_users = active_users_result[0]["count"] if active_users_result else 0

    admin_users_result = execute_query(
        "SELECT COUNT(*) as count FROM users WHERE role = 'admin'"
    )
    admin_users = admin_users_result[0]["count"] if admin_users_result else 0

    # 팀 통계
    teams_result = execute_query("SELECT COUNT(*) as count FROM teams")
    total_teams = teams_result[0]["count"] if teams_result else 0

    # 블록 통계
    blocks_result = execute_query("SELECT COUNT(*) as count FROM blocks")
    total_blocks = blocks_result[0]["count"] if blocks_result else 0

    public_blocks_result = execute_query(
        "SELECT COUNT(*) as count FROM blocks WHERE visibility = 'public'"
    )
    public_blocks = public_blocks_result[0]["count"] if public_blocks_result else 0

    # 세션 통계
    active_sessions = get_active_sessions_count()

    # API 키 통계
    api_keys_result = execute_query("SELECT COUNT(*) as count FROM api_keys")
    total_api_keys = api_keys_result[0]["count"] if api_keys_result else 0

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "admins": admin_users
        },
        "teams": {
            "total": total_teams
        },
        "blocks": {
            "total": total_blocks,
            "public": public_blocks
        },
        "sessions": {
            "active": active_sessions
        },
        "api_keys": {
            "total": total_api_keys
        }
    }


def get_all_users_admin(
    include_inactive: bool = True,
    search_query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    관리자용 전체 사용자 목록을 가져옵니다.

    Args:
        include_inactive: 비활성 사용자 포함 여부
        search_query: 검색어 (개인번호 또는 이름)

    Returns:
        사용자 목록
    """
    query = "SELECT u.*, t.name as team_name FROM users u LEFT JOIN teams t ON u.team_id = t.id WHERE 1=1"
    params = []

    if not include_inactive:
        query += " AND u.status = 'active'"

    if search_query:
        query += " AND (u.personal_number LIKE ? OR u.display_name LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    query += " ORDER BY u.created_at DESC"

    result = execute_query(query, tuple(params) if params else None)
    return [dict(row) for row in result]


def create_user_admin(
    personal_number: str,
    display_name: Optional[str] = None,
    role: str = "user",
    team_id: Optional[int] = None
) -> tuple[bool, str]:
    """
    관리자가 새 사용자를 생성합니다.

    Args:
        personal_number: 개인 번호
        display_name: 표시 이름
        role: 역할 (user, team_lead, admin)
        team_id: 팀 ID

    Returns:
        (성공 여부, 메시지)
    """
    if not personal_number:
        return False, "개인 번호를 입력해주세요."

    personal_number = personal_number.strip().upper()

    # 중복 확인
    existing = execute_query(
        "SELECT id FROM users WHERE personal_number = ?",
        (personal_number,)
    )
    if existing:
        return False, f"'{personal_number}' 번호가 이미 존재합니다."

    # 역할 변환
    try:
        user_role = UserRole(role)
    except ValueError:
        user_role = UserRole.USER

    # 사용자 생성
    user_id = create_user(
        personal_number=personal_number,
        display_name=display_name,
        role=user_role,
        team_id=team_id
    )

    if user_id:
        return True, f"사용자 '{personal_number}'가 생성되었습니다."
    else:
        return False, "사용자 생성에 실패했습니다."


def update_user_admin(
    user_id: int,
    display_name: Optional[str] = None,
    role: Optional[str] = None,
    team_id: Optional[int] = ...,  # ... (Ellipsis)를 기본값으로 사용
    status: Optional[str] = None
) -> tuple[bool, str]:
    """
    관리자가 사용자 정보를 업데이트합니다.

    Args:
        user_id: 사용자 ID
        display_name: 새 표시 이름
        role: 새 역할
        team_id: 새 팀 ID (None이면 팀 제거, ...이면 변경 안 함)
        status: 새 상태

    Returns:
        (성공 여부, 메시지)
    """
    update_data = {}

    if display_name is not None:
        update_data["display_name"] = display_name

    if role is not None:
        try:
            update_data["role"] = UserRole(role).value
        except ValueError:
            pass

    # team_id: ... (Ellipsis)가 아니면 업데이트 (None 포함)
    if team_id is not ...:
        update_data["team_id"] = team_id
        print(f"[DEBUG update_user_admin] team_id 업데이트: {team_id}")

    if status is not None:
        try:
            update_data["status"] = UserStatus(status).value
        except ValueError:
            pass

    if not update_data:
        return False, "업데이트할 정보가 없습니다."

    print(f"[DEBUG update_user_admin] update_data: {update_data}")
    success = update_user(user_id, **update_data)
    if success:
        return True, "사용자 정보가 업데이트되었습니다."
    else:
        return False, "업데이트에 실패했습니다."


def delete_user_admin(user_id: int) -> tuple[bool, str]:
    """
    관리자가 사용자를 삭제합니다.

    Args:
        user_id: 사용자 ID

    Returns:
        (성공 여부, 메시지)
    """
    success = delete_user(user_id)
    if success:
        return True, "사용자가 삭제되었습니다."
    else:
        return False, "삭제에 실패했습니다."


def get_all_teams_admin() -> List[Dict[str, Any]]:
    """
    관리자용 전체 팀 목록을 가져옵니다.
    각 팀의 멤버 수도 포함합니다.
    """
    teams = get_all_teams()

    for team in teams:
        members = get_team_members(team["id"])
        team["member_count"] = len(members)

    return teams


def create_team_admin(name: str, description: Optional[str] = None) -> tuple[bool, str]:
    """
    관리자가 새 팀을 생성합니다.

    Args:
        name: 팀 이름
        description: 팀 설명

    Returns:
        (성공 여부, 메시지)
    """
    if not name:
        return False, "팀 이름을 입력해주세요."

    # 중복 확인
    existing = execute_query(
        "SELECT id FROM teams WHERE name = ?",
        (name,)
    )
    if existing:
        return False, f"'{name}' 팀이 이미 존재합니다."

    team_id = create_team(name, description)
    if team_id:
        return True, f"팀 '{name}'이 생성되었습니다."
    else:
        return False, "팀 생성에 실패했습니다."


def delete_team_admin(team_id: int) -> tuple[bool, str]:
    """
    관리자가 팀을 삭제합니다.
    팀 멤버들의 team_id는 NULL로 설정됩니다.

    Args:
        team_id: 팀 ID

    Returns:
        (성공 여부, 메시지)
    """
    try:
        # 멤버들의 team_id를 NULL로 설정
        execute_query(
            "UPDATE users SET team_id = NULL WHERE team_id = ?",
            (team_id,),
            commit=True
        )

        # 팀 삭제
        execute_query(
            "DELETE FROM teams WHERE id = ?",
            (team_id,),
            commit=True
        )

        # GitHub 백업
        try:
            from github_storage import backup_all_teams, backup_all_users, is_github_storage_available
            if is_github_storage_available():
                backup_all_teams()
                backup_all_users()  # 멤버들의 team_id가 변경됨
        except Exception:
            pass

        return True, "팀이 삭제되었습니다."
    except Exception as e:
        return False, f"삭제에 실패했습니다: {e}"


def cleanup_system():
    """시스템 정리 (만료된 세션 삭제 등)"""
    cleanup_expired_sessions()
    return True, "시스템 정리가 완료되었습니다."


def get_recent_logins(limit: int = 10) -> List[Dict[str, Any]]:
    """최근 로그인 기록을 가져옵니다."""
    result = execute_query(
        """
        SELECT personal_number, display_name, last_login
        FROM users
        WHERE last_login IS NOT NULL
        ORDER BY last_login DESC
        LIMIT ?
        """,
        (limit,)
    )
    return [dict(row) for row in result]

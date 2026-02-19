"""
블록 공유 모듈
팀/사용자 간 블록 공유 기능
"""

import json
from typing import List, Optional, Dict, Any

from database.db_manager import execute_query
from blocks.block_manager import (
    get_block_by_id,
    update_user_block,
    BlockVisibility
)


def share_block_with_team(
    block_db_id: int,
    owner_id: int,
    team_id: int
) -> bool:
    """
    블록을 팀과 공유합니다.

    Args:
        block_db_id: 블록 데이터베이스 ID
        owner_id: 소유자 ID (권한 확인용)
        team_id: 공유할 팀 ID

    Returns:
        성공 여부
    """
    block = get_block_by_id(block_db_id)
    if not block or block["owner_id"] != owner_id:
        return False

    shared_teams = block.get("shared_with_teams") or []
    if team_id not in shared_teams:
        shared_teams.append(team_id)

    return update_user_block(
        block_db_id,
        owner_id,
        visibility=BlockVisibility.TEAM.value,
        shared_with_teams=shared_teams
    )


def unshare_block_from_team(
    block_db_id: int,
    owner_id: int,
    team_id: int
) -> bool:
    """
    팀과의 블록 공유를 해제합니다.

    Args:
        block_db_id: 블록 데이터베이스 ID
        owner_id: 소유자 ID
        team_id: 공유 해제할 팀 ID

    Returns:
        성공 여부
    """
    block = get_block_by_id(block_db_id)
    if not block or block["owner_id"] != owner_id:
        return False

    shared_teams = block.get("shared_with_teams") or []
    if team_id in shared_teams:
        shared_teams.remove(team_id)

    # 더 이상 공유된 팀이 없으면 personal로 변경
    new_visibility = BlockVisibility.TEAM.value if shared_teams else BlockVisibility.PERSONAL.value

    return update_user_block(
        block_db_id,
        owner_id,
        visibility=new_visibility,
        shared_with_teams=shared_teams
    )


def make_block_public(block_db_id: int, owner_id: int) -> bool:
    """
    블록을 공개로 설정합니다.

    Args:
        block_db_id: 블록 데이터베이스 ID
        owner_id: 소유자 ID

    Returns:
        성공 여부
    """
    return update_user_block(
        block_db_id,
        owner_id,
        visibility=BlockVisibility.PUBLIC.value
    )


def make_block_private(block_db_id: int, owner_id: int) -> bool:
    """
    블록을 비공개로 설정합니다.

    Args:
        block_db_id: 블록 데이터베이스 ID
        owner_id: 소유자 ID

    Returns:
        성공 여부
    """
    return update_user_block(
        block_db_id,
        owner_id,
        visibility=BlockVisibility.PERSONAL.value,
        shared_with_teams=[]
    )


def get_shared_blocks_for_user(
    user_id: int,
    team_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    사용자에게 공유된 블록 목록을 조회합니다 (본인 소유 제외).

    Args:
        user_id: 사용자 ID
        team_id: 사용자의 팀 ID

    Returns:
        공유된 블록 목록
    """
    shared_blocks = []

    # 공개 블록
    public_result = execute_query(
        "SELECT * FROM blocks WHERE visibility = 'public' AND owner_id != ?",
        (user_id,)
    )

    for row in public_result:
        block = dict(row)
        try:
            block["block_data"] = json.loads(block["block_data"]) if isinstance(block["block_data"], str) else block["block_data"]
            _swt = block.get("shared_with_teams") or "[]"
            block["shared_with_teams"] = json.loads(_swt) if isinstance(_swt, str) else _swt
        except json.JSONDecodeError:
            pass
        block["share_type"] = "public"
        shared_blocks.append(block)

    # 팀 공유 블록
    if team_id:
        team_result = execute_query(
            "SELECT * FROM blocks WHERE visibility = 'team' AND owner_id != ?",
            (user_id,)
        )

        for row in team_result:
            block = dict(row)
            try:
                block["block_data"] = json.loads(block["block_data"]) if isinstance(block["block_data"], str) else block["block_data"]
                _swt2 = block.get("shared_with_teams") or "[]"
                teams = json.loads(_swt2) if isinstance(_swt2, str) else _swt2
                block["shared_with_teams"] = teams
                if team_id in teams:
                    block["share_type"] = "team"
                    shared_blocks.append(block)
            except json.JSONDecodeError:
                pass

    return shared_blocks


def get_block_sharing_info(block_db_id: int) -> Dict[str, Any]:
    """
    블록의 공유 정보를 조회합니다.

    Args:
        block_db_id: 블록 데이터베이스 ID

    Returns:
        공유 정보 딕셔너리
    """
    block = get_block_by_id(block_db_id)
    if not block:
        return {"error": "블록을 찾을 수 없습니다."}

    # 공유된 팀 정보 조회
    shared_teams = block.get("shared_with_teams") or []
    team_info = []

    for team_id in shared_teams:
        team_result = execute_query(
            "SELECT id, name FROM teams WHERE id = ?",
            (team_id,)
        )
        if team_result:
            team_info.append(dict(team_result[0]))

    return {
        "visibility": block.get("visibility"),
        "shared_with_teams": team_info,
        "owner_id": block.get("owner_id"),
        "block_name": block.get("name")
    }


def can_access_block(block_db_id: int, user_id: int, team_id: Optional[int] = None) -> bool:
    """
    사용자가 블록에 접근 가능한지 확인합니다.

    Args:
        block_db_id: 블록 데이터베이스 ID
        user_id: 사용자 ID
        team_id: 사용자의 팀 ID

    Returns:
        접근 가능 여부
    """
    block = get_block_by_id(block_db_id)
    if not block:
        return False

    # 소유자는 항상 접근 가능
    if block["owner_id"] == user_id:
        return True

    visibility = block.get("visibility")

    # 공개 블록
    if visibility == BlockVisibility.PUBLIC.value:
        return True

    # 팀 공유 블록
    if visibility == BlockVisibility.TEAM.value and team_id:
        shared_teams = block.get("shared_with_teams") or []
        return team_id in shared_teams

    # 비공개 블록
    return False

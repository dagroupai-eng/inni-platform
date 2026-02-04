"""
블록 관리 모듈
사용자별 분석 블록의 CRUD 및 접근 권한 관리
"""

import json
import uuid
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime

from database.db_manager import execute_query, get_last_insert_id


class BlockVisibility(Enum):
    """블록 공개 범위"""
    PERSONAL = "personal"  # 본인만 접근 가능
    TEAM = "team"  # 팀원 접근 가능
    PUBLIC = "public"  # 모든 사용자 접근 가능


def generate_block_id(name: str) -> str:
    """블록 이름에서 고유 ID를 생성합니다."""
    import re
    # 한글, 영문, 숫자만 유지
    cleaned = re.sub(r'[^\w\s가-힣]', '', name)
    # 공백을 언더스코어로 변환
    cleaned = re.sub(r'\s+', '_', cleaned)
    # 소문자로 변환하고 UUID 일부 추가
    return f"{cleaned.lower()}_{uuid.uuid4().hex[:8]}"


def create_user_block(
    owner_id: int,
    name: str,
    block_data: Dict[str, Any],
    category: Optional[str] = None,
    visibility: BlockVisibility = BlockVisibility.PERSONAL,
    shared_with_teams: Optional[List[int]] = None,
    block_id: Optional[str] = None
) -> Optional[int]:
    """
    새 사용자 블록을 생성합니다.

    Args:
        owner_id: 소유자 사용자 ID
        name: 블록 이름
        block_data: 블록 데이터 (JSON 직렬화 가능한 딕셔너리)
        category: 카테고리
        visibility: 공개 범위
        shared_with_teams: 공유된 팀 ID 목록
        block_id: 커스텀 블록 ID (없으면 자동 생성)

    Returns:
        생성된 블록 ID 또는 None
    """
    if not block_id:
        block_id = generate_block_id(name)

    # block_data에 메타데이터 추가
    block_data["id"] = block_id
    block_data["name"] = name
    block_data["created_at"] = datetime.now().isoformat()
    block_data["created_by"] = "user"

    try:
        execute_query(
            """
            INSERT INTO blocks (block_id, owner_id, name, category, block_data, visibility, shared_with_teams, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                block_id,
                owner_id,
                name,
                category,
                json.dumps(block_data, ensure_ascii=False),
                visibility.value if isinstance(visibility, BlockVisibility) else visibility,
                json.dumps(shared_with_teams or []),
                datetime.now().isoformat()
            ),
            commit=True
        )

        # GitHub 백업 (Streamlit Cloud용)
        try:
            from github_storage import backup_all_blocks, is_github_storage_available
            if is_github_storage_available():
                backup_all_blocks()
        except Exception as gh_e:
            print(f"[GitHub] 블록 백업 오류 (무시): {gh_e}")

        return get_last_insert_id()
    except Exception as e:
        print(f"블록 생성 오류: {e}")
        return None


def get_user_blocks(
    owner_id: int,
    category: Optional[str] = None,
    visibility: Optional[BlockVisibility] = None
) -> List[Dict[str, Any]]:
    """
    사용자가 생성한 블록 목록을 조회합니다.

    Args:
        owner_id: 소유자 사용자 ID
        category: 카테고리 필터
        visibility: 공개 범위 필터

    Returns:
        블록 목록
    """
    query = "SELECT * FROM blocks WHERE owner_id = ?"
    params = [owner_id]

    if category:
        query += " AND category = ?"
        params.append(category)

    if visibility:
        query += " AND visibility = ?"
        params.append(visibility.value if isinstance(visibility, BlockVisibility) else visibility)

    query += " ORDER BY created_at DESC"

    result = execute_query(query, tuple(params))

    blocks = []
    for row in result:
        block = dict(row)
        # JSON 문자열을 파싱
        try:
            block["block_data"] = json.loads(block["block_data"])
            block["shared_with_teams"] = json.loads(block.get("shared_with_teams") or "[]")
        except json.JSONDecodeError:
            pass
        blocks.append(block)

    return blocks


def get_block_by_id(block_db_id: int) -> Optional[Dict[str, Any]]:
    """
    데이터베이스 ID로 블록을 조회합니다.

    Args:
        block_db_id: 데이터베이스 블록 ID

    Returns:
        블록 정보 또는 None
    """
    result = execute_query(
        "SELECT * FROM blocks WHERE id = ?",
        (block_db_id,)
    )

    if result:
        block = dict(result[0])
        try:
            block["block_data"] = json.loads(block["block_data"])
            block["shared_with_teams"] = json.loads(block.get("shared_with_teams") or "[]")
        except json.JSONDecodeError:
            pass
        return block

    return None


def get_block_by_block_id(block_id: str, owner_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    블록 ID(문자열)로 블록을 조회합니다.

    Args:
        block_id: 블록 ID
        owner_id: 소유자 ID (특정 소유자의 블록만 검색 시)

    Returns:
        블록 정보 또는 None
    """
    if owner_id:
        result = execute_query(
            "SELECT * FROM blocks WHERE block_id = ? AND owner_id = ?",
            (block_id, owner_id)
        )
    else:
        result = execute_query(
            "SELECT * FROM blocks WHERE block_id = ?",
            (block_id,)
        )

    if result:
        block = dict(result[0])
        try:
            block["block_data"] = json.loads(block["block_data"])
            block["shared_with_teams"] = json.loads(block.get("shared_with_teams") or "[]")
        except json.JSONDecodeError:
            pass
        return block

    return None


def update_user_block(
    block_db_id: int,
    owner_id: int,
    **kwargs
) -> bool:
    """
    블록을 업데이트합니다.

    Args:
        block_db_id: 데이터베이스 블록 ID
        owner_id: 소유자 ID (권한 확인용)
        **kwargs: 업데이트할 필드

    Returns:
        성공 여부
    """
    # 소유권 확인
    existing = get_block_by_id(block_db_id)
    if not existing or existing["owner_id"] != owner_id:
        return False

    allowed_fields = ["name", "category", "block_data", "visibility", "shared_with_teams"]
    update_fields = []
    values = []

    for field, value in kwargs.items():
        if field in allowed_fields:
            update_fields.append(f"{field} = ?")
            if field == "block_data":
                values.append(json.dumps(value, ensure_ascii=False))
            elif field == "shared_with_teams":
                values.append(json.dumps(value))
            elif field == "visibility" and isinstance(value, BlockVisibility):
                values.append(value.value)
            else:
                values.append(value)

    if not update_fields:
        return False

    values.append(block_db_id)

    try:
        execute_query(
            f"UPDATE blocks SET {', '.join(update_fields)} WHERE id = ?",
            tuple(values),
            commit=True
        )

        # GitHub 백업
        try:
            from github_storage import backup_all_blocks, is_github_storage_available
            if is_github_storage_available():
                backup_all_blocks()
        except Exception:
            pass

        return True
    except Exception as e:
        print(f"블록 업데이트 오류: {e}")
        return False


def delete_user_block(block_db_id: int, owner_id: int) -> bool:
    """
    블록을 삭제합니다.

    Args:
        block_db_id: 데이터베이스 블록 ID
        owner_id: 소유자 ID (권한 확인용)

    Returns:
        성공 여부
    """
    # 소유권 확인
    existing = get_block_by_id(block_db_id)
    if not existing or existing["owner_id"] != owner_id:
        return False

    try:
        execute_query(
            "DELETE FROM blocks WHERE id = ?",
            (block_db_id,),
            commit=True
        )

        # GitHub 백업
        try:
            from github_storage import backup_all_blocks, is_github_storage_available
            if is_github_storage_available():
                backup_all_blocks()
        except Exception:
            pass

        return True
    except Exception as e:
        print(f"블록 삭제 오류: {e}")
        return False


def get_accessible_blocks(user_id: int, team_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    사용자가 접근 가능한 모든 블록을 조회합니다.
    (본인 블록 + 팀 공유 블록 + 공개 블록)

    Args:
        user_id: 사용자 ID
        team_id: 사용자의 팀 ID

    Returns:
        접근 가능한 블록 목록
    """
    # 본인 블록
    own_blocks = get_user_blocks(user_id)

    # 공개 블록 (다른 사용자의)
    public_result = execute_query(
        "SELECT * FROM blocks WHERE visibility = 'public' AND owner_id != ?",
        (user_id,)
    )
    public_blocks = []
    for row in public_result:
        block = dict(row)
        try:
            block["block_data"] = json.loads(block["block_data"])
            block["shared_with_teams"] = json.loads(block.get("shared_with_teams") or "[]")
        except json.JSONDecodeError:
            pass
        public_blocks.append(block)

    # 팀 공유 블록
    team_blocks = []
    if team_id:
        # 방법 1: shared_with_teams에 현재 팀이 포함된 블록
        # 방법 2: 소유자가 같은 팀에 속한 블록 (visibility='team')
        team_result = execute_query(
            """
            SELECT b.*, u.team_id as owner_team_id
            FROM blocks b
            LEFT JOIN users u ON b.owner_id = u.id
            WHERE b.visibility = 'team' AND b.owner_id != ?
            """,
            (user_id,)
        )
        for row in team_result:
            block = dict(row)
            try:
                block["block_data"] = json.loads(block["block_data"])
                shared_teams = json.loads(block.get("shared_with_teams") or "[]")
                block["shared_with_teams"] = shared_teams
                owner_team_id = block.get("owner_team_id")

                # 조건 1: shared_with_teams에 현재 팀이 포함
                # 조건 2: 블록 소유자가 같은 팀에 속함
                if team_id in shared_teams or owner_team_id == team_id:
                    team_blocks.append(block)
            except json.JSONDecodeError:
                pass

    # 중복 제거하며 병합
    all_blocks = own_blocks + public_blocks + team_blocks
    seen_ids = set()
    unique_blocks = []
    for block in all_blocks:
        if block["id"] not in seen_ids:
            seen_ids.add(block["id"])
            unique_blocks.append(block)

    return unique_blocks


def get_block_categories(owner_id: Optional[int] = None) -> List[str]:
    """블록 카테고리 목록을 조회합니다."""
    if owner_id:
        result = execute_query(
            "SELECT DISTINCT category FROM blocks WHERE owner_id = ? AND category IS NOT NULL",
            (owner_id,)
        )
    else:
        result = execute_query(
            "SELECT DISTINCT category FROM blocks WHERE category IS NOT NULL"
        )

    return [row["category"] for row in result if row["category"]]

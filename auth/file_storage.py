"""
Supabase Storage 기반 파일 업로드/다운로드 래퍼.

버킷: project-files
경로: {user_id}/{project_id}/{filename}

사용 전 Supabase Dashboard > Storage에서 버킷 생성 필요:
  - Bucket name: project-files
  - Public: false (비공개)
"""

import os
from typing import Optional

_BUCKET = "project-files"
_MAX_BYTES = 20 * 1024 * 1024  # 20 MB


def _client():
    from database.supabase_client import get_supabase_client
    return get_supabase_client()


def upload_project_file(
    user_id: int,
    project_id: int,
    filename: str,
    file_bytes: bytes,
) -> Optional[str]:
    """
    파일 바이너리를 Supabase Storage에 업로드하고 storage_path를 반환합니다.

    Args:
        user_id: 사용자 DB ID
        project_id: 프로젝트 DB ID
        filename: 원본 파일명
        file_bytes: 파일 바이너리

    Returns:
        storage_path (str) 또는 None (업로드 실패 / 크기 초과)
    """
    if len(file_bytes) > _MAX_BYTES:
        print(f"[FileStorage] 파일 크기 초과 ({len(file_bytes)//1024}KB > 20MB), 저장 스킵")
        return None

    try:
        import mimetypes
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        path = f"{user_id}/{project_id}/{filename}"

        client = _client()
        # 동일 경로에 파일이 있으면 upsert
        client.storage.from_(_BUCKET).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        print(f"[FileStorage] 업로드 완료: {path}")
        return path
    except Exception as e:
        print(f"[FileStorage] 업로드 실패: {e}")
        return None


def download_project_file(storage_path: str) -> Optional[bytes]:
    """
    Supabase Storage에서 파일 바이너리를 다운로드합니다.

    Args:
        storage_path: upload_project_file()이 반환한 경로

    Returns:
        파일 bytes 또는 None (실패)
    """
    try:
        client = _client()
        data = client.storage.from_(_BUCKET).download(storage_path)
        print(f"[FileStorage] 다운로드 완료: {storage_path} ({len(data)}bytes)")
        return data
    except Exception as e:
        print(f"[FileStorage] 다운로드 실패: {e}")
        return None


def delete_project_files(user_id: int, project_id: int) -> bool:
    """프로젝트의 모든 저장 파일을 Storage와 DB에서 삭제합니다."""
    try:
        prefix = f"{user_id}/{project_id}/"
        client = _client()
        items = client.storage.from_(_BUCKET).list(prefix)
        paths = [item["name"] for item in (items or []) if item.get("name")]
        if paths:
            full_paths = [f"{prefix}{p}" for p in paths]
            client.storage.from_(_BUCKET).remove(full_paths)
        # DB 레코드도 삭제
        from database.db_manager import execute_query
        execute_query(
            "DELETE FROM project_files WHERE project_id = ? AND user_id = ?",
            (project_id, user_id),
            commit=True,
        )
        return True
    except Exception as e:
        print(f"[FileStorage] 파일 삭제 실패: {e}")
        return False


def save_file_meta(
    project_id: int,
    user_id: int,
    filename: str,
    file_type: str,
    storage_path: Optional[str],
    char_count: int,
    file_size_bytes: int,
    file_meta: dict,
) -> Optional[int]:
    """
    project_files 테이블에 파일 메타데이터를 저장합니다.

    Returns:
        삽입된 row의 id 또는 None
    """
    try:
        from database.db_manager import execute_query
        import json

        result = execute_query(
            """
            INSERT INTO project_files
                (project_id, user_id, filename, file_type, storage_path,
                 char_count, file_size_bytes, file_meta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id, user_id, filename, file_type,
                storage_path, char_count, file_size_bytes,
                json.dumps(file_meta, ensure_ascii=False),
            ),
            commit=True,
        )
        from database.db_manager import get_last_insert_id
        return get_last_insert_id()
    except Exception as e:
        print(f"[FileStorage] 메타 저장 실패: {e}")
        return None


def get_project_files(project_id: int) -> list:
    """프로젝트에 저장된 파일 목록을 반환합니다."""
    try:
        from database.db_manager import execute_query
        rows = execute_query(
            """
            SELECT id, filename, file_type, storage_path, char_count,
                   file_size_bytes, file_meta, created_at
            FROM project_files
            WHERE project_id = ?
            ORDER BY created_at DESC
            """,
            (project_id,),
        )
        return [dict(r) for r in (rows or [])]
    except Exception as e:
        print(f"[FileStorage] 파일 목록 조회 실패: {e}")
        return []

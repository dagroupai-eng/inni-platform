"""
SQLite 데이터베이스 연결 관리자
동시성 제어 및 연결 풀링 지원
"""

import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional, Any, List, Tuple
from pathlib import Path

# 모듈 레벨 import는 순환 import 방지를 위해 함수 내부에서 수행
_DB_PATH: Optional[Path] = None


def _get_db_path() -> Path:
    """DB 경로를 지연 로딩합니다."""
    global _DB_PATH
    if _DB_PATH is None:
        from config.settings import DB_PATH
        _DB_PATH = DB_PATH
    return _DB_PATH


# 스레드 로컬 저장소 (스레드별 연결 관리)
_thread_local = threading.local()

# 연결 잠금 (동시성 제어)
_connection_lock = threading.Lock()


def get_db_connection() -> sqlite3.Connection:
    """
    현재 스레드에 대한 데이터베이스 연결을 가져옵니다.
    연결이 없으면 새로 생성합니다.
    """
    if not hasattr(_thread_local, 'connection') or _thread_local.connection is None:
        db_path = _get_db_path()
        parent = db_path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OSError(
                f"데이터 디렉토리를 생성할 수 없습니다: {parent}. "
                f"경로에 쓰기 권한이 있는지 확인하세요. ({e})"
            ) from e
        try:
            _thread_local.connection = sqlite3.connect(
                str(db_path),
                timeout=30.0,  # 30초 타임아웃
                check_same_thread=False
            )
        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e).lower():
                raise sqlite3.OperationalError(
                    f"데이터베이스 파일을 열 수 없습니다: {db_path}. "
                    "data/ 디렉토리 존재 및 쓰기 권한을 확인하세요."
                ) from e
            raise
        _thread_local.connection.row_factory = sqlite3.Row
        # WAL 모드 활성화 (동시성 향상)
        _thread_local.connection.execute("PRAGMA journal_mode=WAL")
        _thread_local.connection.execute("PRAGMA foreign_keys=ON")

    return _thread_local.connection


def close_connection():
    """현재 스레드의 데이터베이스 연결을 닫습니다."""
    if hasattr(_thread_local, 'connection') and _thread_local.connection is not None:
        _thread_local.connection.close()
        _thread_local.connection = None


@contextmanager
def db_transaction():
    """
    트랜잭션 컨텍스트 매니저
    자동 커밋/롤백 처리
    """
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e


def execute_query(
    query: str,
    params: Optional[Tuple] = None,
    commit: bool = False
) -> List[sqlite3.Row]:
    """
    단일 쿼리를 실행합니다.

    Args:
        query: SQL 쿼리
        params: 쿼리 파라미터
        commit: 커밋 여부

    Returns:
        쿼리 결과 (SELECT인 경우)
    """
    with _connection_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if commit:
                conn.commit()

            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
            return []
        except Exception as e:
            if commit:
                conn.rollback()
            raise e


def execute_many(
    query: str,
    params_list: List[Tuple],
    commit: bool = True
) -> int:
    """
    여러 개의 쿼리를 배치로 실행합니다.

    Args:
        query: SQL 쿼리
        params_list: 파라미터 튜플 리스트
        commit: 커밋 여부

    Returns:
        영향 받은 행 수
    """
    with _connection_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.executemany(query, params_list)
            if commit:
                conn.commit()
            return cursor.rowcount
        except Exception as e:
            if commit:
                conn.rollback()
            raise e


def get_last_insert_id() -> int:
    """마지막으로 삽입된 행의 ID를 반환합니다."""
    conn = get_db_connection()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def table_exists(table_name: str) -> bool:
    """테이블 존재 여부를 확인합니다."""
    result = execute_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return len(result) > 0

"""
데이터베이스 초기화 스크립트
테이블 생성 및 초기 데이터 설정
"""

from database.db_manager import get_db_connection, execute_query, table_exists
from config.settings import get_admin_personal_numbers
from datetime import datetime


# 테이블 생성 SQL
CREATE_TABLES_SQL = """
-- 팀 테이블
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personal_number TEXT UNIQUE NOT NULL,
    display_name TEXT,
    role TEXT DEFAULT 'user',
    team_id INTEGER REFERENCES teams(id),
    status TEXT DEFAULT 'active',
    last_login TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- API 키 저장 (암호화)
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    key_name TEXT NOT NULL,
    encrypted_value TEXT NOT NULL,
    encryption_iv TEXT NOT NULL,
    UNIQUE(user_id, key_name)
);

-- 사용자 블록
CREATE TABLE IF NOT EXISTS blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id TEXT NOT NULL,
    owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT,
    block_data TEXT NOT NULL,
    visibility TEXT DEFAULT 'personal',
    shared_with_teams TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 분석 세션
CREATE TABLE IF NOT EXISTS analysis_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_name TEXT,
    project_name TEXT,
    session_data TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 사용자 설정
CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    settings_data TEXT NOT NULL DEFAULT '{}'
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_users_personal_number ON users(personal_number);
CREATE INDEX IF NOT EXISTS idx_blocks_owner ON blocks(owner_id);
CREATE INDEX IF NOT EXISTS idx_blocks_visibility ON blocks(visibility);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_sessions_user ON analysis_sessions(user_id);
"""


def init_database():
    """
    데이터베이스를 초기화합니다.
    테이블이 없으면 생성하고, 관리자 계정을 설정합니다.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 테이블 생성
    cursor.executescript(CREATE_TABLES_SQL)
    conn.commit()

    # 관리자 계정 생성
    _create_admin_users()

    print("Database initialized successfully.")


def _create_admin_users():
    """환경 변수에 지정된 관리자 번호로 관리자 계정을 생성합니다."""
    admin_numbers = get_admin_personal_numbers()

    for personal_number in admin_numbers:
        # 이미 존재하는지 확인
        existing = execute_query(
            "SELECT id FROM users WHERE personal_number = ?",
            (personal_number,)
        )

        if not existing:
            # 새 관리자 계정 생성
            execute_query(
                """
                INSERT INTO users (personal_number, display_name, role, status, created_at)
                VALUES (?, ?, 'admin', 'active', ?)
                """,
                (personal_number, f"Admin ({personal_number})", datetime.now().isoformat()),
                commit=True
            )
            print(f"Admin user created: {personal_number}")
        else:
            # 기존 사용자를 관리자로 업그레이드
            execute_query(
                "UPDATE users SET role = 'admin' WHERE personal_number = ?",
                (personal_number,),
                commit=True
            )


def reset_database():
    """
    데이터베이스를 초기화합니다 (모든 데이터 삭제).
    주의: 이 작업은 되돌릴 수 없습니다.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 모든 테이블 삭제
    tables = ["user_settings", "analysis_sessions", "blocks", "api_keys", "users", "teams"]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

    conn.commit()

    # 다시 초기화
    init_database()


# 모듈 로드 시 자동 초기화
if not table_exists("users"):
    init_database()

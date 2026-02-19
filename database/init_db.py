"""
데이터베이스 초기화 스크립트 (Supabase 버전)
테이블 존재 확인 및 관리자 계정 설정
"""

from database.db_manager import execute_query, table_exists
from config.settings import get_admin_personal_numbers
from datetime import datetime


def init_database():
    """
    데이터베이스를 초기화합니다.
    Supabase 테이블이 존재하는지 확인하고, 관리자 계정을 설정합니다.
    """
    # Supabase 연결 확인
    if not table_exists("users"):
        print("⚠️ Supabase 테이블이 없습니다. supabase_schema.sql을 먼저 실행하세요.")
        return

    # 관리자 계정 생성
    _create_admin_users()

    print("Database initialized successfully (Supabase).")


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
    Supabase에서는 테이블의 데이터만 삭제합니다.
    """
    from database.supabase_client import get_supabase_client
    client = get_supabase_client()

    tables = ["user_settings", "analysis_progress", "analysis_sessions", "blocks", "api_keys", "users", "teams"]
    for table in tables:
        try:
            # 모든 행 삭제 (id > 0 조건으로 전체 삭제)
            client.table(table).delete().gte("id", 0).execute()
            print(f"  Cleared: {table}")
        except Exception as e:
            print(f"  ⚠️ {table} 삭제 오류: {e}")

    # 다시 초기화 (관리자 계정 생성)
    init_database()


# 모듈 로드 시 자동 초기화
try:
    if table_exists("users"):
        # 관리자 계정이 없으면 생성
        admin_count = execute_query("SELECT COUNT(*) as cnt FROM users WHERE role = 'admin'")
        if admin_count and admin_count[0]['cnt'] == 0:
            init_database()
    else:
        print("⚠️ Supabase 연결 실패 또는 테이블 미생성")
except Exception as e:
    print(f"⚠️ DB 초기화 확인 오류: {e}")

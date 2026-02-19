"""
PMS 환경설정 모듈
Streamlit Cloud 및 로컬 환경 모두 지원
"""

import os
from pathlib import Path
from typing import Optional

# 프로젝트 루트 디렉토리 (절대 경로로 고정, cwd 무관)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 데이터 디렉토리
DATA_DIR = (PROJECT_ROOT / "data").resolve()
DB_PATH = (DATA_DIR / "inni_platform.db").resolve()
SESSIONS_DIR = DATA_DIR / "sessions"
CACHE_DIR = DATA_DIR / "cache"
USERS_DIR = DATA_DIR / "users"

# 세션 설정
SESSION_TTL_HOURS = 24
SESSION_TOKEN_LENGTH = 64

# 암호화 설정
ENCRYPTION_KEY_LENGTH = 32  # AES-256


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    환경 변수 또는 Streamlit secrets에서 비밀 값을 가져옵니다.
    우선순위: 환경변수 -> Streamlit secrets -> 기본값
    """
    # 1. 환경변수에서 확인
    value = os.environ.get(key)
    if value:
        return value

    # 2. Streamlit secrets에서 확인
    try:
        import streamlit as st
        try:
            value = st.secrets.get(key)
            if value:
                return value
        except (FileNotFoundError, AttributeError, KeyError):
            pass
    except ImportError:
        pass

    return default


def get_encryption_master_key() -> str:
    """
    암호화 마스터 키를 가져옵니다.
    키가 없으면 기본 키를 반환합니다 (프로덕션에서는 반드시 설정해야 함).
    """
    key = get_secret("ENCRYPTION_MASTER_KEY")
    if not key:
        # 기본 키 (개발용 - 프로덕션에서는 반드시 변경)
        key = "default-32-character-secret-key!"
        print("WARNING: Using default encryption key. Set ENCRYPTION_MASTER_KEY in production.")
    return key


def get_admin_personal_numbers() -> list:
    """
    관리자 개인 번호 목록을 가져옵니다.
    """
    numbers_str = get_secret("ADMIN_PERSONAL_NUMBERS", "ADMIN001")
    return [n.strip() for n in numbers_str.split(",") if n.strip()]


def ensure_directories():
    """
    필요한 데이터 디렉토리들을 생성합니다.
    """
    for directory in [DATA_DIR, SESSIONS_DIR, CACHE_DIR, USERS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


# 앱 시작 시 디렉토리 생성
ensure_directories()

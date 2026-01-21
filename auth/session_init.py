"""
모든 페이지에서 사용할 세션 초기화 모듈
로그인 세션 복원 + 작업 데이터 복원
"""

import streamlit as st
from typing import Optional


def init_page_session():
    """
    모든 페이지에서 호출해야 하는 세션 초기화 함수
    1. 로그인 세션 복원 (URL에서)
    2. 작업 세션 복원 (DB에서)
    """
    # 1. 로그인 세션 복원
    restore_login_session()

    # 2. 작업 데이터 복원
    restore_work_session()


def restore_login_session():
    """로그인 세션을 URL에서 복원합니다."""
    # 이미 세션이 있으면 스킵
    if 'pms_session_token' in st.session_state and st.session_state.pms_session_token:
        print("[DEBUG] 세션 이미 존재, 복원 스킵")
        return

    try:
        from pathlib import Path
        from config.settings import DATA_DIR
        from auth.session_manager import get_session
        from auth.user_manager import get_user_by_id

        # 로컬 파일에서 토큰 로드
        token = None
        last_session_file = DATA_DIR / "last_session.txt"
        if last_session_file.exists():
            with open(last_session_file, 'r') as f:
                token = f.read().strip()

        print(f"[DEBUG] 파일에서 로드된 토큰: {token[:20] if token else 'None'}...")

        if token:
            # 세션 유효성 확인
            session_data = get_session(token)
            print(f"[DEBUG] 세션 데이터: {session_data is not None}")

            if session_data:
                # 유효한 세션이면 복원
                st.session_state.pms_session_token = token
                print(f"[DEBUG] 세션 토큰 복원 완료")

                # 사용자 정보도 복원
                user_id = session_data.get("user_id")
                if user_id:
                    user = get_user_by_id(user_id)
                    if user:
                        st.session_state.pms_current_user = user
                        print(f"[DEBUG] 사용자 정보 복원: {user.get('personal_number')}")

                        # API 키도 복원
                        try:
                            from security.api_key_manager import get_user_api_key
                            from dspy_analyzer import PROVIDER_CONFIG

                            for provider, config in PROVIDER_CONFIG.items():
                                api_key_env = config.get('api_key_env')
                                if api_key_env:
                                    db_key = get_user_api_key(user_id, api_key_env)
                                    if db_key:
                                        session_key = f'user_api_key_{api_key_env}'
                                        st.session_state[session_key] = db_key
                        except:
                            pass
            else:
                print("[DEBUG] 세션 데이터가 유효하지 않음")
        else:
            print("[DEBUG] URL에 토큰 없음")
    except Exception as e:
        print(f"로그인 세션 복원 오류: {e}")
        import traceback
        traceback.print_exc()


def restore_work_session():
    """작업 데이터를 DB에서 복원합니다."""
    # 로그인 확인
    if 'pms_current_user' not in st.session_state:
        print("[DEBUG] 사용자 정보 없음, 복원 스킵")
        return

    # 현재 페이지에서 이미 복원했는지 확인
    import inspect
    current_frame = inspect.currentframe()
    caller_frame = inspect.getouterframes(current_frame, 2)
    page_name = caller_frame[2].filename if len(caller_frame) > 2 else "unknown"

    restore_key = f'work_session_restored_{hash(page_name)}'

    if restore_key in st.session_state:
        print(f"[DEBUG] 페이지 {page_name}에서 이미 복원됨, 스킵")
        return

    try:
        from database.db_manager import execute_query
        import json

        user_id = st.session_state.pms_current_user.get('id')
        if not user_id:
            return

        print(f"[DEBUG] 사용자 {user_id}의 작업 세션 복원 중...")

        # 가장 최근 작업 세션 조회
        result = execute_query(
            """
            SELECT session_data FROM analysis_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,)
        )

        if result and result[0]:
            session_data = json.loads(result[0]['session_data'])
            restored_count = 0

            # 세션 상태로 복원
            for key, value in session_data.items():
                if key not in st.session_state:
                    st.session_state[key] = value
                    restored_count += 1

            print(f"[DEBUG] {restored_count}개의 세션 키 복원됨")
            print(f"[DEBUG] 복원된 키: {list(session_data.keys())[:5]}...")
        else:
            print("[DEBUG] 저장된 작업 세션 없음")

        st.session_state[restore_key] = True
    except Exception as e:
        print(f"작업 세션 복원 오류: {e}")
        import traceback
        traceback.print_exc()


def save_work_session():
    """현재 작업 데이터를 DB에 저장합니다."""
    # 로그인 확인
    if 'pms_current_user' not in st.session_state:
        return

    try:
        from database.db_manager import execute_query
        from datetime import datetime
        import json

        user_id = st.session_state.pms_current_user.get('id')
        if not user_id:
            return

        # 저장할 세션 데이터 수집
        session_data = {}

        # Document Analysis 관련 데이터
        save_keys = [
            'project_name', 'location', 'latitude', 'longitude',
            'project_goals', 'additional_info', 'pdf_text',
            'analysis_results', 'selected_blocks', 'cot_results',
            'cot_history', 'preprocessed_text', 'preprocessing_meta',
            'reference_documents', 'reference_combined_text',
            # CoT 분석 세션 관련
            'cot_session', 'cot_plan', 'cot_current_index',
            'cot_running_block', 'cot_progress_messages',
            'cot_feedback_inputs', 'skipped_blocks', 'cot_citations'
        ]

        for key in save_keys:
            if key in st.session_state:
                value = st.session_state[key]
                # JSON 직렬화 가능한지 확인
                try:
                    json.dumps(value)
                    session_data[key] = value
                except (TypeError, ValueError):
                    pass

        # DB에 저장
        if session_data:  # 저장할 데이터가 있을 때만
            execute_query(
                """
                INSERT INTO analysis_sessions (user_id, session_data, created_at)
                VALUES (?, ?, ?)
                """,
                (user_id, json.dumps(session_data, ensure_ascii=False), datetime.now().isoformat()),
                commit=True
            )
            print(f"[DEBUG] {len(session_data)}개의 세션 키 저장됨")
        else:
            print("[DEBUG] 저장할 세션 데이터 없음")
    except Exception as e:
        print(f"작업 세션 저장 오류: {e}")
        import traceback
        traceback.print_exc()


def auto_save_trigger():
    """자동 저장 트리거 (중요한 상태 변경 시 호출)"""
    # 너무 자주 저장하지 않도록 제한
    import time
    current_time = time.time()

    if 'last_save_time' not in st.session_state:
        st.session_state.last_save_time = 0

    # 마지막 저장 후 5초 이상 경과한 경우에만 저장
    if current_time - st.session_state.last_save_time > 5:
        print(f"[DEBUG] 작업 세션 자동 저장 중...")
        save_work_session()
        st.session_state.last_save_time = current_time
        print(f"[DEBUG] 작업 세션 저장 완료")

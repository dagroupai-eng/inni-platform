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
    """로그인 세션을 복원합니다. (파일 기반 복원 제거됨)"""
    # 이미 세션이 있으면 스킵
    if 'pms_session_token' in st.session_state and st.session_state.pms_session_token:
        # print("[DEBUG] 세션 이미 존재, 복원 스킵")
        return

    # 파일 기반 세션 복원 제거 (멀티유저 환경에서 세션 충돌 방지)
    # Streamlit Cloud에서는 각 브라우저 세션이 독립적이므로 파일 기반 복원 불필요
    # 새로운 세션의 경우 로그인 페이지로 이동하게 됨
    pass


def restore_work_session():
    """작업 데이터를 DB에서 복원합니다."""
    # 로그인 확인
    if 'pms_current_user' not in st.session_state:
        return

    # 현재 페이지에서 이미 복원했는지 확인
    import inspect
    current_frame = inspect.currentframe()
    caller_frame = inspect.getouterframes(current_frame, 2)
    page_name = caller_frame[2].filename if len(caller_frame) > 2 else "unknown"

    restore_key = f'work_session_restored_{hash(page_name)}'

    if restore_key in st.session_state:
        return

    try:
        from database.db_manager import execute_query
        import json

        user_id = st.session_state.pms_current_user.get('id')
        if not user_id:
            return

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

            # 세션 상태로 복원
            for key, value in session_data.items():
                if key not in st.session_state:
                    st.session_state[key] = value

        st.session_state[restore_key] = True
    except Exception as e:
        print(f"작업 세션 복원 오류: {e}")


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
    except Exception as e:
        print(f"작업 세션 저장 오류: {e}")


def auto_save_trigger():
    """자동 저장 트리거 (중요한 상태 변경 시 호출)"""
    # 너무 자주 저장하지 않도록 제한
    import time
    current_time = time.time()

    if 'last_save_time' not in st.session_state:
        st.session_state.last_save_time = 0

    # 마지막 저장 후 5초 이상 경과한 경우에만 저장
    if current_time - st.session_state.last_save_time > 5:
        save_work_session()
        st.session_state.last_save_time = current_time

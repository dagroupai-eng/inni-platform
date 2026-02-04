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
    print("[복원] restore_work_session() 호출됨")

    # 로그인 확인
    if 'pms_current_user' not in st.session_state:
        print("[복원] 로그인 정보 없음, 복원 스킵")
        return

    print(f"[복원] 로그인 확인됨: {st.session_state.pms_current_user.get('personal_number', 'unknown')}")

    # 현재 페이지에서 이미 복원했는지 확인
    import inspect
    current_frame = inspect.currentframe()
    caller_frame = inspect.getouterframes(current_frame, 2)
    page_name = caller_frame[2].filename if len(caller_frame) > 2 else "unknown"

    # 전역 복원 키 사용 (페이지마다 복원하지 않고, 앱 전체에서 한 번만 복원)
    restore_key = 'work_session_restored_global'

    # 복원 진행 중 플래그
    restoring_key = 'work_session_restoring'

    # 이미 복원 중이면 대기
    if st.session_state.get(restoring_key):
        print(f"[복원] 복원 진행 중, 대기: {page_name}")
        return

    # 복원 키가 있어도, 실제 데이터가 없으면 다시 복원
    if restore_key in st.session_state:
        # 프로젝트 정보 키 중 하나라도 있는지 확인
        has_data = any([
            st.session_state.get('project_name'),
            st.session_state.get('location'),
            st.session_state.get('analysis_results'),
            st.session_state.get('cot_results')
        ])
        if has_data:
            print(f"[복원] 이미 복원됨 (데이터 확인 완료), 스킵: {page_name}")
            return
        else:
            print(f"[복원] 복원 키 존재하지만 데이터 없음, 재복원: {page_name}")
            # restore_key 삭제하고 다시 복원
            del st.session_state[restore_key]

    # 복원 시작 - 플래그 설정
    st.session_state[restoring_key] = True
    print(f"[복원] 복원 시작: {page_name}")

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
            print(f"[복원] DB에서 데이터 로드 완료: {len(session_data)}개 키")

            # 프로젝트 정보는 빈 값이어도 덮어쓰기 (복원 우선)
            project_info_keys = ['project_name', 'location', 'latitude', 'longitude',
                                'project_goals', 'additional_info', 'pdf_text', 'pdf_uploaded']

            # 분석 결과는 항상 복원 (중요!)
            analysis_keys = ['analysis_results', 'cot_results', 'cot_session', 'cot_plan',
                           'cot_current_index', 'selected_blocks', 'cot_history', 'cot_citations']

            restored_count = 0
            # 세션 상태로 복원
            for key, value in session_data.items():
                # 프로젝트 정보는 값이 None이 아니면 무조건 복원 (빈 문자열도 복원)
                if key in project_info_keys:
                    if value is not None:
                        st.session_state[key] = value
                        restored_count += 1
                        print(f"[복원] 프로젝트 정보 복원: {key} = {value if isinstance(value, (str, int, float, bool)) and len(str(value)) < 50 else f'{type(value).__name__}...'}")
                # 분석 결과는 값이 있으면 무조건 복원 (빈 딕셔너리/리스트는 제외)
                elif key in analysis_keys:
                    if value is not None and value not in [[], {}, ""]:
                        st.session_state[key] = value
                        restored_count += 1
                        print(f"[복원] 분석 데이터 복원: {key}")
                # 그 외 키는 세션에 없을 때만 복원
                elif key not in st.session_state:
                    st.session_state[key] = value
                    restored_count += 1

            print(f"[복원] 총 {restored_count}개 키 복원 완료")
        else:
            print("[복원] DB에 저장된 세션 없음, GitHub에서 시도...")

            # GitHub에서 복원 시도 (Streamlit Cloud 재시작 후)
            try:
                from github_storage import load_from_github, is_github_storage_available
                if is_github_storage_available():
                    github_user_id = str(user_id) if isinstance(user_id, int) else user_id
                    session_data = load_from_github(github_user_id, "session")

                    if session_data:
                        print(f"[GitHub] 세션 복원 성공: {len(session_data)}개 키")

                        # 프로젝트 정보 키
                        project_info_keys = ['project_name', 'location', 'latitude', 'longitude',
                                            'project_goals', 'additional_info', 'pdf_text', 'pdf_uploaded']
                        # 분석 결과 키
                        analysis_keys = ['analysis_results', 'cot_results', 'cot_session', 'cot_plan',
                                       'cot_current_index', 'selected_blocks', 'cot_history', 'cot_citations']

                        restored_count = 0
                        for key, value in session_data.items():
                            if key in project_info_keys:
                                if value is not None:
                                    st.session_state[key] = value
                                    restored_count += 1
                            elif key in analysis_keys:
                                if value is not None and value not in [[], {}, ""]:
                                    st.session_state[key] = value
                                    restored_count += 1
                            elif key not in st.session_state:
                                st.session_state[key] = value
                                restored_count += 1

                        print(f"[GitHub] 총 {restored_count}개 키 복원 완료")
                    else:
                        print("[GitHub] 저장된 세션 없음")
            except Exception as gh_e:
                print(f"[GitHub] 복원 오류 (무시): {gh_e}")

        # 복원 완료 플래그 설정
        st.session_state[restore_key] = True
        # 복원 진행 중 플래그 해제
        if restoring_key in st.session_state:
            del st.session_state[restoring_key]
        print(f"[복원] 복원 프로세스 완료")
    except Exception as e:
        print(f"작업 세션 복원 오류: {e}")
        # 에러 발생 시에도 복원 진행 중 플래그 해제
        restoring_key = 'work_session_restoring'
        if restoring_key in st.session_state:
            del st.session_state[restoring_key]


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

            # GitHub 백업 (Streamlit Cloud용)
            try:
                from github_storage import save_to_github, is_github_storage_available
                if is_github_storage_available():
                    github_user_id = str(user_id) if isinstance(user_id, int) else user_id
                    save_to_github(github_user_id, "session", session_data)
                    print(f"[GitHub] 세션 백업 완료: {len(session_data)}개 키")
            except Exception as gh_e:
                print(f"[GitHub] 세션 백업 오류 (무시): {gh_e}")

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


def save_analysis_progress(force: bool = False):
    """
    분석 진행 상태 즉시 저장 (2초 간격)

    Args:
        force: True이면 간격 제한 무시하고 즉시 저장
    """
    import time
    current_time = time.time()

    if 'last_analysis_save_time' not in st.session_state:
        st.session_state.last_analysis_save_time = 0

    # 마지막 저장 후 2초 이상 경과한 경우에만 저장 (force=True이면 무시)
    if not force and current_time - st.session_state.last_analysis_save_time < 2:
        return

    # 로그인 확인
    if 'pms_current_user' not in st.session_state:
        return

    try:
        from database.db_manager import execute_query, table_exists
        from datetime import datetime
        import json

        # 테이블 존재 확인 및 생성
        if not table_exists('analysis_progress'):
            print("[저장] analysis_progress 테이블 생성")
            execute_query(
                """
                CREATE TABLE IF NOT EXISTS analysis_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                    progress_data TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """,
                commit=True
            )

        user_id = st.session_state.pms_current_user.get('id')
        if not user_id:
            return

        # 분석 진행 상태만 수집
        progress_data = {}

        progress_keys = [
            'cot_session', 'cot_plan', 'cot_current_index',
            'cot_results', 'cot_running_block', 'cot_progress_messages',
            'cot_feedback_inputs', 'skipped_blocks', 'cot_citations',
            'cot_history', 'analysis_results', 'selected_blocks'
        ]

        for key in progress_keys:
            if key in st.session_state:
                value = st.session_state[key]
                try:
                    json.dumps(value)
                    progress_data[key] = value
                except (TypeError, ValueError):
                    pass

        if progress_data:
            # 저장 시간 기록
            progress_data['_saved_at'] = datetime.now().isoformat()

            # 기존 분석 진행 상태 업데이트 또는 삽입
            execute_query(
                """
                INSERT OR REPLACE INTO analysis_progress
                (user_id, progress_data, updated_at)
                VALUES (?, ?, ?)
                """,
                (user_id, json.dumps(progress_data, ensure_ascii=False), datetime.now().isoformat()),
                commit=True
            )

        st.session_state.last_analysis_save_time = current_time
    except Exception as e:
        print(f"분석 진행 저장 오류: {e}")


def restore_analysis_progress() -> Optional[dict]:
    """
    중단된 분석 진행 상태 복원 (1시간 이내)

    Returns:
        복원 가능한 진행 상태가 있으면 dict 반환, 없으면 None
    """
    # 로그인 확인
    if 'pms_current_user' not in st.session_state:
        return None

    try:
        from database.db_manager import execute_query
        from datetime import datetime, timedelta
        import json

        user_id = st.session_state.pms_current_user.get('id')
        if not user_id:
            return None

        # 1시간 이내의 분석 진행 상태 조회
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

        result = execute_query(
            """
            SELECT progress_data, updated_at FROM analysis_progress
            WHERE user_id = ? AND updated_at > ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (user_id, one_hour_ago)
        )

        if result and result[0]:
            progress_data = json.loads(result[0]['progress_data'])
            updated_at = result[0]['updated_at']

            # 분석 결과가 있는지 확인
            if progress_data.get('cot_results') or progress_data.get('cot_session'):
                progress_data['_restored_from'] = updated_at
                return progress_data

        return None
    except Exception as e:
        print(f"분석 진행 복원 조회 오류: {e}")
        return None


def apply_restored_progress(progress_data: dict) -> bool:
    """
    복원된 진행 상태를 세션에 적용

    Args:
        progress_data: 복원된 진행 데이터

    Returns:
        성공 여부
    """
    if not progress_data:
        return False

    try:
        restore_keys = [
            'cot_session', 'cot_plan', 'cot_current_index',
            'cot_results', 'cot_progress_messages',
            'cot_feedback_inputs', 'skipped_blocks', 'cot_citations',
            'cot_history', 'analysis_results', 'selected_blocks'
        ]

        for key in restore_keys:
            if key in progress_data:
                st.session_state[key] = progress_data[key]

        # 실행 중 상태는 복원하지 않음 (안전)
        st.session_state.cot_running_block = None

        return True
    except Exception as e:
        print(f"분석 진행 복원 적용 오류: {e}")
        return False


def reset_analysis_state_selective(
    reset_results: bool = True,
    reset_session: bool = True,
    preserve_api_keys: bool = True,
    preserve_blocks: bool = True,
    preserve_project_info: bool = True
) -> dict:
    """
    선택적 분석 상태 초기화

    Args:
        reset_results: 분석 결과 초기화 여부
        reset_session: CoT 세션 초기화 여부
        preserve_api_keys: API 키 유지 여부
        preserve_blocks: 선택된 블록 유지 여부
        preserve_project_info: 프로젝트 정보 유지 여부

    Returns:
        초기화 전 보존된 값들
    """
    preserved = {}

    # 보존할 값들 저장
    if preserve_api_keys:
        api_keys_to_preserve = [
            'user_api_key_GEMINI_API_KEY',
            'user_api_key_OPENAI_API_KEY',
            'user_api_key_ANTHROPIC_API_KEY',
            'llm_provider'
        ]
        for key in api_keys_to_preserve:
            if key in st.session_state:
                preserved[key] = st.session_state[key]

    if preserve_blocks:
        if 'selected_blocks' in st.session_state:
            preserved['selected_blocks'] = st.session_state.selected_blocks.copy()
        if 'block_spatial_selection' in st.session_state:
            preserved['block_spatial_selection'] = st.session_state.block_spatial_selection.copy()

    if preserve_project_info:
        project_keys = ['project_name', 'location', 'latitude', 'longitude',
                       'project_goals', 'additional_info', 'pdf_text', 'pdf_uploaded']
        for key in project_keys:
            if key in st.session_state:
                preserved[key] = st.session_state[key]

    # 선택적 초기화 수행
    if reset_session:
        st.session_state.cot_session = None
        st.session_state.cot_plan = []
        st.session_state.cot_current_index = 0
        st.session_state.cot_running_block = None
        st.session_state.cot_progress_messages = []
        st.session_state.skipped_blocks = []
        st.session_state.pop('cot_analyzer', None)

    if reset_results:
        st.session_state.cot_results = {}
        st.session_state.cot_citations = {}
        st.session_state.cot_history = []
        st.session_state.cot_feedback_inputs = {}
        st.session_state.analysis_results = {}

    # 보존된 값 복원
    for key, value in preserved.items():
        st.session_state[key] = value

    return preserved


def render_session_manager_sidebar():
    """
    모든 페이지의 사이드바에 세션 관리 UI를 렌더링합니다.
    각 페이지에서 st.sidebar 컨텍스트 내에서 호출해야 합니다.
    """
    with st.sidebar.expander("🔄 세션 관리", expanded=False):
        # 복원 대기 중인 상태 확인
        if 'pending_restore' in st.session_state and st.session_state.pending_restore:
            restored_progress = st.session_state.pending_restore
            restored_time = restored_progress.get('_restored_from', '')[:16].replace('T', ' ')
            results_count = len(restored_progress.get('cot_results', {}))

            st.warning(f"📂 중단된 세션 발견")
            st.caption(f"저장: {restored_time}, 완료 블록: {results_count}개")

            col_r, col_d = st.columns(2)
            with col_r:
                if st.button("✅ 복원", key="sidebar_restore_btn", use_container_width=True):
                    if apply_restored_progress(restored_progress):
                        st.session_state.pop('pending_restore', None)
                        st.success("복원됨")
                        st.rerun()
            with col_d:
                if st.button("❌ 삭제", key="sidebar_discard_btn", use_container_width=True):
                    st.session_state.pop('pending_restore', None)
                    st.rerun()

        # 초기화 항목 선택
        st.caption("⚙️ 초기화 항목 선택")

        # 초기화 항목 체크박스
        reset_analysis = st.checkbox("분석 결과", key="reset_analysis_cb", value=False,
                                     help="블록 분석 결과 초기화")
        reset_api_keys = st.checkbox("API 키", key="reset_api_keys_cb", value=False,
                                     help="저장된 API 키 초기화")
        reset_blocks = st.checkbox("선택 블록", key="reset_blocks_cb", value=False,
                                   help="선택된 블록 목록 초기화")
        reset_project = st.checkbox("프로젝트 정보", key="reset_project_cb", value=False,
                                    help="프로젝트명, 위치, PDF 등 초기화")

        # 선택 항목 초기화 버튼
        if st.button("🗑️ 선택 항목 초기화", key="sidebar_reset_selected_btn", use_container_width=True):
            reset_count = 0
            reset_items = []

            if reset_analysis:
                # 분석 결과 초기화
                analysis_keys = ['cot_results', 'cot_session', 'cot_plan', 'cot_current_index',
                                'cot_running_block', 'cot_progress_messages', 'cot_feedback_inputs',
                                'skipped_blocks', 'cot_citations', 'cot_history', 'analysis_results']
                deleted = 0
                for key in analysis_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                        deleted += 1
                if deleted > 0:
                    reset_count += 1
                    reset_items.append("분석 결과")

            if reset_api_keys:
                # API 키 초기화
                api_key_keys = [key for key in st.session_state.keys() if key.startswith('user_api_key_')]
                api_key_keys.extend(['api_keys_loaded', 'gemini_api_key', 'openai_api_key', 'anthropic_api_key'])
                deleted = 0
                for key in list(api_key_keys):
                    if key in st.session_state:
                        del st.session_state[key]
                        deleted += 1
                if deleted > 0:
                    reset_count += 1
                    reset_items.append("API 키")

            if reset_blocks:
                # 블록 초기화
                block_keys = ['selected_blocks', 'block_spatial_data', 'prelinked_block_layers']
                deleted = 0
                for key in block_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                        deleted += 1
                if deleted > 0:
                    reset_count += 1
                    reset_items.append("선택 블록")

            if reset_project:
                # 프로젝트 정보 초기화
                project_keys = ['project_name', 'location', 'latitude', 'longitude',
                               'project_goals', 'additional_info', 'pdf_text',
                               'preprocessed_text', 'preprocessing_meta',
                               'reference_documents', 'reference_combined_text',
                               'downloaded_geo_data', 'cadastral_data', 'cadastral_center_lat',
                               'cadastral_center_lon', 'geo_stats_result']
                deleted = 0
                for key in project_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                        deleted += 1
                if deleted > 0:
                    reset_count += 1
                    reset_items.append("프로젝트 정보")

            if reset_count > 0:
                st.success(f"초기화 완료: {', '.join(reset_items)}")
                st.rerun()
            else:
                st.warning("초기화할 항목을 선택하세요")

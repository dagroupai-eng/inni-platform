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
    """로그인 세션을 복원합니다. (브라우저 localStorage + Supabase 기반)"""
    # 이미 세션이 있으면 localStorage 동기화 후 스킵
    # (login() 직후 st.rerun()으로 인해 save_session_to_browser()가 미실행될 수 있으므로
    #  첫 렌더에서 여기서 확실히 저장)
    if 'pms_session_token' in st.session_state and st.session_state.pms_session_token:
        if not st.session_state.get('_browser_token_synced'):
            try:
                from auth.browser_session import save_session_to_browser
                save_session_to_browser(st.session_state.pms_session_token)
                st.session_state['_browser_token_synced'] = True
            except Exception:
                pass
        return

    # 복원 시도 중 플래그 (무한 루프 방지) - JS가 실제 값을 반환한 후에만 설정
    if st.session_state.get('_login_restore_attempted'):
        return

    try:
        from streamlit_javascript import st_javascript
        token = st_javascript("localStorage.getItem('pms_session_token') || ''")

        # st_javascript는 첫 렌더에서 0(int)을 반환함 → 아직 JS 미실행 상태
        if token == 0:
            st.session_state['_checking_session'] = True
            return  # _login_restore_attempted 설정하지 않고 대기

        # JS 실행 완료 → 체크 플래그 해제 + 재시도 방지 플래그 설정
        st.session_state['_login_restore_attempted'] = True
        st.session_state.pop('_checking_session', None)

        if not token or not isinstance(token, str) or len(token) < 10:
            return

        from auth.session_manager import get_session
        from auth.user_manager import get_user_by_id

        session_data = get_session(token)
        if not session_data:
            return

        user_id = session_data.get('user_id')
        if not user_id:
            return

        user = get_user_by_id(user_id)
        if user and user.get('status') == 'active':
            st.session_state.pms_session_token = token
            st.session_state.pms_current_user = {
                'id': user['id'],
                'personal_number': user.get('personal_number'),
                'display_name': user.get('display_name'),
                'role': user.get('role'),
                'team_id': user.get('team_id'),
            }
            print(f"[Session] localStorage에서 세션 복원: {user.get('display_name')}")

    except Exception as e:
        print(f"[Session] 브라우저 세션 복원 오류: {e}")
        st.session_state['_login_restore_attempted'] = True
        st.session_state.pop('_checking_session', None)


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

    # 페이지 초기화 직후에는 복원하지 않음
    if st.session_state.get('page_just_reset'):
        print(f"[복원] 페이지 초기화 직후, 복원 스킵: {page_name}")
        del st.session_state['page_just_reset']
        return

    # current_project_id가 있으면 복원 완료 상태로 간주 (재복원 금지)
    # 주의: has_data로 판단하면 {}(빈 dict) falsy 때문에 저장 직후 rerun 시 오복원 발생
    if restore_key in st.session_state:
        if st.session_state.get('current_project_id'):
            print(f"[복원] 이미 복원됨 (project_id 확인), 스킵: {page_name}")
            return
        # project_id도 없으면 재복원 시도 (예: 브라우저 완전 새로고침 직후)
        print(f"[복원] project_id 없음, 재복원 시도: {page_name}")
        del st.session_state[restore_key]

    # 복원 시작 - 플래그 설정
    st.session_state[restoring_key] = True
    print(f"[복원] 복원 시작: {page_name}")

    try:
        from database.db_manager import execute_query
        from auth.project_manager import load_project_session
        import json

        user_id = st.session_state.pms_current_user.get('id')
        if not user_id:
            return

        # project_id 기반 조회 우선 (병합 로직 포함한 load_project_session 사용)
        project_id = st.session_state.get('current_project_id')
        session_data = None

        if project_id:
            session_data = load_project_session(user_id, project_id)
        else:
            # project_id 없을 때 (브라우저 탭 닫고 재오픈 등): 가장 최근 세션으로 폴백
            try:
                from database.db_manager import execute_query as _eq
                import json as _json
                _rows = _eq(
                    "SELECT project_id, session_data FROM analysis_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                    (user_id,)
                )
                if _rows:
                    _pid_fb = _rows[0]["project_id"]
                    _raw_fb = _rows[0]["session_data"]
                    session_data = _json.loads(_raw_fb) if isinstance(_raw_fb, str) else _raw_fb
                    if _pid_fb:
                        st.session_state['current_project_id'] = _pid_fb
                        print(f"[복원] project_id 폴백 복원: {_pid_fb}")
            except Exception as _fb_err:
                print(f"[복원] 폴백 복원 오류: {_fb_err}")

        if session_data:
            print(f"[복원] DB에서 데이터 로드 완료: {len(session_data)}개 키")

            # pdf_text, preprocessed_text는 저장하지 않으므로 복원 목록에서도 제외
            project_info_keys = [
                'project_name', 'location', 'latitude', 'longitude',
                'project_goals', 'additional_info', 'pdf_uploaded',
                'file_analysis', 'file_storage_path', 'document_summary',
                'site_fields', 'downloaded_geo_data',
            ]
            # 빈 문자열 복원 금지 키: DB에 "" 저장된 경우 session_state를 덮어쓰지 않음
            _no_restore_empty = {'project_name', 'location', 'project_goals', 'additional_info'}

            # 분석 결과는 항상 복원 (중요!)
            analysis_keys = [
                'analysis_results', 'cot_results', 'cot_session', 'cot_plan',
                'cot_current_index', 'selected_blocks', 'cot_history', 'cot_citations',
                'cot_feedback_inputs', 'skipped_blocks',
                'cot_verifications', 'urban_indicator_results',
            ]

            restored_count = 0
            for key, value in session_data.items():
                if key in project_info_keys:
                    if value is None:
                        continue
                    # 빈 문자열은 의미 있는 데이터가 아닐 수 있으므로 복원 스킵
                    if key in _no_restore_empty and not value:
                        continue
                    st.session_state[key] = value
                    restored_count += 1
                    print(f"[복원] 프로젝트 정보 복원: {key}")
                elif key in analysis_keys:
                    if value is not None and value not in [[], {}, ""]:
                        st.session_state[key] = value
                        restored_count += 1
                        print(f"[복원] 분석 데이터 복원: {key}")
                elif key not in st.session_state:
                    st.session_state[key] = value
                    restored_count += 1

            print(f"[복원] 총 {restored_count}개 키 복원 완료")
            st.session_state['_save_status'] = 'saved'
        else:
            print("[복원] DB에 저장된 세션 없음")

        # session_data에 project_name이 없거나 비어있으면 projects 테이블에서 fallback
        _final_pid = st.session_state.get('current_project_id')
        if _final_pid and not st.session_state.get('project_name'):
            try:
                from database.db_manager import execute_query as _peq
                _prows = _peq(
                    "SELECT name, location FROM projects WHERE id = ? AND user_id = ?",
                    (_final_pid, user_id)
                )
                if _prows:
                    _pname = _prows[0].get('name') or ''
                    _ploc = _prows[0].get('location') or ''
                    if _pname and _pname != '새 프로젝트':
                        st.session_state['project_name'] = _pname
                        print(f"[복원] project_name → projects 테이블 fallback: {_pname}")
                    if _ploc and not st.session_state.get('location'):
                        st.session_state['location'] = _ploc
                        print(f"[복원] location → projects 테이블 fallback: {_ploc}")
            except Exception as _pe:
                print(f"[복원] projects fallback 오류: {_pe}")

    except Exception as e:
        print(f"작업 세션 복원 오류: {e}")
    finally:
        # 예외 발생 여부와 무관하게 항상 복원 완료 플래그 설정 (재복원 방지)
        st.session_state[restore_key] = True
        if restoring_key in st.session_state:
            del st.session_state[restoring_key]
        print(f"[복원] 복원 프로세스 완료")


def save_work_session():
    """현재 작업 데이터를 DB에 저장합니다."""
    if 'pms_current_user' not in st.session_state:
        return

    st.session_state['_save_status'] = 'saving'
    try:
        from database.db_manager import execute_query
        from datetime import datetime
        import json

        user_id = st.session_state.pms_current_user.get('id')
        if not user_id:
            return

        project_id = st.session_state.get('current_project_id')

        session_data = {}

        # 일반 직렬화 키
        # pdf_text, preprocessed_text, reference_combined_text 제외: 대역폭 절감 (23명 동시 사용 고려)
        # 해당 필드는 파일 재업로드 시 재생성됨
        save_keys = [
            'project_name', 'location', 'latitude', 'longitude',
            'project_goals', 'additional_info', 'pdf_uploaded',
            'analysis_results', 'selected_blocks', 'cot_results',
            'cot_history', 'preprocessing_meta',
            'reference_documents',
            'cot_session', 'cot_plan', 'cot_current_index',
            'cot_running_block', 'cot_progress_messages',
            'cot_feedback_inputs', 'skipped_blocks', 'cot_citations',
            # 새 키 (7-C)
            'file_analysis', 'file_storage_path', 'document_summary',
            'site_fields', 'cot_verifications', 'urban_indicator_results',
        ]

        # 크기 제한이 있는 키 (500KB 이하만 저장)
        large_keys = ['downloaded_geo_data']
        _SIZE_LIMIT = 500 * 1024  # 500 KB

        # 빈 문자열로 저장 금지: 이전 유효값을 덮어쓰지 않도록 보호
        _no_empty_keys = {'project_name', 'location', 'project_goals', 'additional_info'}

        for key in save_keys:
            if key in st.session_state:
                value = st.session_state[key]
                if key in _no_empty_keys and not value:
                    continue  # 빈 값이면 저장 스킵
                try:
                    json.dumps(value)
                    session_data[key] = value
                except (TypeError, ValueError):
                    pass

        for key in large_keys:
            if key in st.session_state:
                value = st.session_state[key]
                try:
                    serialized = json.dumps(value, ensure_ascii=False)
                    if len(serialized.encode('utf-8')) <= _SIZE_LIMIT:
                        session_data[key] = value
                    else:
                        print(f"[저장] {key} 크기 초과, 저장 스킵 ({len(serialized)//1024}KB)")
                except (TypeError, ValueError):
                    pass

        if session_data:
            # UNIQUE(user_id, project_id) constraint 유무와 무관하게 동작하는 수동 upsert:
            # 기존 행이 있으면 UPDATE, 없으면 INSERT
            from database.supabase_client import get_supabase_client as _gsc
            _client = _gsc()
            _now = datetime.now().isoformat()
            _sd_json = json.dumps(session_data, ensure_ascii=False)
            _existing = (
                _client.table('analysis_sessions')
                .select('id')
                .eq('user_id', user_id)
                .eq('project_id', project_id)
                .limit(1)
                .execute()
            )
            if _existing.data:
                _client.table('analysis_sessions').update({
                    'session_data': json.loads(_sd_json),
                    'created_at': _now,
                }).eq('user_id', user_id).eq('project_id', project_id).execute()
            else:
                _client.table('analysis_sessions').insert({
                    'user_id': user_id,
                    'project_id': project_id,
                    'session_data': json.loads(_sd_json),
                    'created_at': _now,
                }).execute()
            # projects.updated_at 갱신
            if project_id:
                execute_query(
                    "UPDATE projects SET updated_at = ? WHERE id = ? AND user_id = ?",
                    (datetime.now().isoformat(), project_id, user_id),
                    commit=True,
                )
            # analysis_steps도 최신 cot_results로 동기화
            # (_load_latest_steps_into_session이 steps 데이터를 덮어쓰므로 일치시켜야 함)
            try:
                step_id_map = st.session_state.get("analysis_step_id_map") or {}
                cr = session_data.get("cot_results") or {}
                if step_id_map and cr:
                    from database.analysis_steps_manager import save_step_payloads
                    for _bid, _result in cr.items():
                        _sid = step_id_map.get(_bid)
                        if _sid:
                            save_step_payloads(_sid, outputs={"analysis": _result})
            except Exception as _sync_err:
                print(f"[저장] analysis_steps 동기화 오류: {_sync_err}")
            st.session_state['_save_status'] = 'saved'
            st.session_state['_last_saved_at'] = datetime.now().isoformat()
        else:
            st.session_state['_save_status'] = 'saved'

        # autosave 타이머 갱신 (명시적 save 후 즉시 autosave 중복 방지)
        import time as _time
        st.session_state['last_save_time'] = _time.time()

    except Exception as e:
        print(f"작업 세션 저장 오류: {e}")
        st.session_state['_save_status'] = 'error'


def auto_save_debounced(throttle_seconds: float = 3.0):
    """
    자동 저장 (3초 스로틀).
    입력 필드 변경 콜백이나 분석 완료 후 호출한다.
    """
    import time
    current_time = time.time()

    if 'last_save_time' not in st.session_state:
        st.session_state.last_save_time = 0

    if current_time - st.session_state.last_save_time >= throttle_seconds:
        save_work_session()
        st.session_state.last_save_time = current_time


def auto_save_trigger():
    """하위 호환: auto_save_debounced() 별칭."""
    auto_save_debounced(throttle_seconds=5.0)


def save_analysis_progress(force: bool = False):
    """
    분석 진행 상태 저장 — analysis_sessions UPSERT로 위임 (analysis_progress 테이블 제거됨).
    force=True이면 throttle 없이 즉시 저장.
    """
    import time
    current_time = time.time()

    if 'last_analysis_save_time' not in st.session_state:
        st.session_state.last_analysis_save_time = 0

    if not force and current_time - st.session_state.last_analysis_save_time < 2:
        return

    save_work_session()
    st.session_state.last_analysis_save_time = current_time


def restore_analysis_progress() -> Optional[dict]:
    """
    중단된 분석 진행 상태 복원 (1시간 이내) — analysis_sessions에서 조회.
    """
    if 'pms_current_user' not in st.session_state:
        return None

    try:
        from database.db_manager import execute_query
        from datetime import datetime, timedelta
        import json

        user_id = st.session_state.pms_current_user.get('id')
        if not user_id:
            return None

        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        project_id = st.session_state.get('current_project_id')

        if project_id:
            result = execute_query(
                """
                SELECT session_data, created_at FROM analysis_sessions
                WHERE user_id = ? AND project_id = ? AND created_at > ?
                LIMIT 1
                """,
                (user_id, project_id, one_hour_ago)
            )
        else:
            result = execute_query(
                """
                SELECT session_data, created_at FROM analysis_sessions
                WHERE user_id = ? AND created_at > ?
                LIMIT 1
                """,
                (user_id, one_hour_ago)
            )

        if result and result[0]:
            raw = result[0]['session_data']
            session_data = json.loads(raw) if isinstance(raw, str) else raw
            updated_at = result[0]['created_at']

            if session_data and (session_data.get('cot_results') or session_data.get('cot_session')):
                session_data['_restored_from'] = updated_at
                return session_data

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


def reset_full_work_state():
    """
    작업 관련 모든 세션 상태를 초기화한다.
    프로젝트 전환 / 새 프로젝트 생성 시 호출.
    로그인 정보·API 키·current_project_id 는 유지한다.
    """
    preserve_keys = {
        'pms_current_user', 'pms_session_token',
        'work_session_restored_global',
        'current_project_id',
        # API 키
        'user_api_key_GEMINI_API_KEY',
        'user_api_key_OPENAI_API_KEY',
        'user_api_key_ANTHROPIC_API_KEY',
        'llm_provider', 'api_keys_loaded',
    }
    drop_keys = [k for k in list(st.session_state.keys()) if k not in preserve_keys]
    for k in drop_keys:
        del st.session_state[k]

    # 저장 상태 초기화
    st.session_state['_save_status'] = 'saved'
    # 복원 플래그 리셋 (다음 페이지 로드에서 새 프로젝트 세션 복원)
    st.session_state.pop('work_session_restored_global', None)


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
                block_keys = ['selected_blocks', 'prelinked_block_layers']
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

"""
프로젝트 CRUD 및 선택 UI.

projects 테이블 기반으로 사용자별 다중 프로젝트를 관리한다.
"""

import json
import streamlit as st
from typing import Optional


# ─── DB 헬퍼 ──────────────────────────────────────────────────────────────────

def _uid() -> Optional[int]:
    user = st.session_state.get("pms_current_user")
    return user.get("id") if user else None


def list_projects(user_id: int) -> list:
    """최근 수정순으로 프로젝트 목록 반환 (최대 20개)."""
    try:
        from database.db_manager import execute_query
        rows = execute_query(
            """
            SELECT id, name, description, location, status, created_at, updated_at
            FROM projects
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT 20
            """,
            (user_id,),
        )
        return [dict(r) for r in (rows or [])]
    except Exception as e:
        print(f"[ProjectManager] list_projects 오류: {e}")
        return []


def create_project(user_id: int, name: str = "새 프로젝트", location: str = "") -> Optional[int]:
    """
    새 프로젝트를 생성하고 project_id(int)를 반환한다.
    실패 시 None 반환.
    """
    try:
        from database.db_manager import execute_query, get_last_insert_id
        from datetime import datetime
        now = datetime.now().isoformat()
        execute_query(
            """
            INSERT INTO projects (user_id, name, location, status, created_at, updated_at)
            VALUES (?, ?, ?, 'in_progress', ?, ?)
            """,
            (user_id, name, location, now, now),
            commit=True,
        )
        pid = get_last_insert_id()
        print(f"[ProjectManager] 프로젝트 생성: id={pid}, name={name}")
        return pid
    except Exception as e:
        print(f"[ProjectManager] create_project 오류: {e}")
        return None


def update_project(user_id: int, project_id: int, **kwargs) -> bool:
    """
    프로젝트 메타 업데이트 (name, location, status, description).
    updated_at 은 자동으로 현재 시각으로 설정된다.
    """
    allowed = {"name", "location", "status", "description"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    try:
        from database.db_manager import execute_query
        from datetime import datetime
        fields["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [project_id, user_id]
        execute_query(
            f"UPDATE projects SET {set_clause} WHERE id = ? AND user_id = ?",
            tuple(values),
            commit=True,
        )
        return True
    except Exception as e:
        print(f"[ProjectManager] update_project 오류: {e}")
        return False


def delete_project(user_id: int, project_id: int) -> bool:
    """프로젝트와 관련 파일을 삭제한다."""
    try:
        from database.db_manager import execute_query
        from auth.file_storage import delete_project_files
        delete_project_files(user_id, project_id)
        execute_query(
            "DELETE FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user_id),
            commit=True,
        )
        return True
    except Exception as e:
        print(f"[ProjectManager] delete_project 오류: {e}")
        return False


def load_project_session(user_id: int, project_id: int) -> Optional[dict]:
    """프로젝트의 최신 세션 데이터를 반환한다."""
    try:
        from database.db_manager import execute_query
        rows = execute_query(
            """
            SELECT session_data FROM analysis_sessions
            WHERE user_id = ? AND project_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (user_id, project_id),
        )
        if rows and rows[0]:
            raw = rows[0]["session_data"]
            return json.loads(raw) if isinstance(raw, str) else raw
        return None
    except Exception as e:
        print(f"[ProjectManager] load_project_session 오류: {e}")
        return None


def get_or_create_current_project(user_id: int) -> int:
    """
    session_state에 current_project_id 가 있으면 반환,
    없으면 가장 최근 프로젝트를 찾아 반환, 그것도 없으면 새로 생성한다.
    """
    if st.session_state.get("current_project_id"):
        return st.session_state.current_project_id

    projects = list_projects(user_id)
    if projects:
        pid = projects[0]["id"]
    else:
        pid = create_project(user_id)

    st.session_state.current_project_id = pid
    return pid


# ─── 세션 적용 ─────────────────────────────────────────────────────────────────

def apply_project_session(session_data: dict) -> int:
    """세션 데이터를 session_state에 적용하고 복원된 키 수를 반환한다."""
    project_keys = [
        "project_name", "location", "latitude", "longitude",
        "project_goals", "additional_info", "pdf_text", "pdf_uploaded",
        "file_analysis", "file_storage_path", "document_summary",
    ]
    analysis_keys = [
        "analysis_results", "cot_results", "cot_session", "cot_plan",
        "cot_current_index", "selected_blocks", "cot_history", "cot_citations",
        "cot_feedback_inputs", "skipped_blocks",
    ]
    extra_keys = [
        "site_fields", "downloaded_geo_data", "cot_verifications",
        "urban_indicator_results", "block_spatial_data", "preprocessing_meta",
        "preprocessed_text", "reference_documents", "reference_combined_text",
    ]

    count = 0
    for key in project_keys + analysis_keys + extra_keys:
        value = session_data.get(key)
        if value is None:
            continue
        if key in analysis_keys and value in [[], {}, ""]:
            continue
        st.session_state[key] = value
        count += 1
    return count


# ─── UI ───────────────────────────────────────────────────────────────────────

def render_project_selector():
    """
    페이지 상단에 프로젝트 선택 바를 렌더링한다.
    session_state.current_project_id 를 기준으로 동작한다.
    """
    uid = _uid()
    if not uid:
        return

    projects = list_projects(uid)
    current_pid = st.session_state.get("current_project_id")

    # 프로젝트가 아예 없으면 자동 생성
    if not projects:
        new_pid = create_project(uid)
        if new_pid:
            st.session_state.current_project_id = new_pid
            st.rerun()
        return

    # current_project_id 가 목록에 없으면 첫 번째로 교정
    ids = [p["id"] for p in projects]
    if current_pid not in ids:
        current_pid = ids[0]
        st.session_state.current_project_id = current_pid

    # 마지막 저장 시각 계산
    current_project = next((p for p in projects if p["id"] == current_pid), projects[0])
    updated_raw = current_project.get("updated_at", "")
    updated_str = updated_raw[:16].replace("T", " ") if updated_raw else "—"

    # ── UI 렌더링 ────────────────────────────────────────────────────────────
    with st.container():
        col_sel, col_new, col_del, col_info = st.columns([4, 1.4, 1, 2])

        with col_sel:
            options = [p["id"] for p in projects]
            labels = {p["id"]: p["name"] for p in projects}
            selected = st.selectbox(
                "📁 프로젝트",
                options=options,
                index=options.index(current_pid) if current_pid in options else 0,
                format_func=lambda pid: labels.get(pid, f"프로젝트 {pid}"),
                key="project_selector_widget",
                label_visibility="collapsed",
            )
            if selected != current_pid:
                _switch_project(uid, selected)

        with col_new:
            if st.button("＋ 새 프로젝트", use_container_width=True, key="btn_new_project"):
                _create_new_project(uid)

        with col_del:
            if st.button("🗑️", use_container_width=True, key="btn_del_project",
                         help="현재 프로젝트 삭제"):
                _confirm_delete_project(uid, current_pid)

        with col_info:
            save_status = st.session_state.get("_save_status", "saved")
            if save_status == "saving":
                st.caption("⏳ 저장 중...")
            elif save_status == "error":
                st.caption("⚠️ 저장 실패")
            else:
                st.caption(f"💾 저장됨 · {updated_str}")

    # 프로젝트명 인라인 편집
    with st.expander("프로젝트명 편집", expanded=False):
        new_name = st.text_input(
            "프로젝트명",
            value=current_project.get("name", ""),
            key="project_name_editor",
        )
        if st.button("저장", key="btn_save_project_name"):
            if new_name.strip():
                update_project(uid, current_pid, name=new_name.strip())
                st.success("프로젝트명이 저장되었습니다.")
                st.rerun()


def _switch_project(uid: int, project_id: int):
    """프로젝트 전환: 세션 초기화 후 선택 프로젝트 데이터 로드."""
    from auth.session_init import reset_full_work_state
    reset_full_work_state()
    session_data = load_project_session(uid, project_id)
    if session_data:
        count = apply_project_session(session_data)
        st.session_state["_restore_notice"] = {
            "project_name": session_data.get("project_name", ""),
            "count": count,
            "project_id": project_id,
        }
    st.session_state.current_project_id = project_id
    st.session_state.work_session_restored_global = True
    st.rerun()


def _create_new_project(uid: int):
    """새 프로젝트 생성 후 전환."""
    from auth.session_init import reset_full_work_state
    reset_full_work_state()
    pid = create_project(uid)
    if pid:
        st.session_state.current_project_id = pid
        st.session_state.work_session_restored_global = True
        st.rerun()


def _confirm_delete_project(uid: int, project_id: int):
    """삭제 확인 플래그 토글."""
    key = f"_confirm_del_{project_id}"
    if not st.session_state.get(key):
        st.session_state[key] = True
        st.warning("다시 한 번 클릭하면 삭제됩니다.")
    else:
        del st.session_state[key]
        delete_project(uid, project_id)
        # 다음 프로젝트로 전환
        remaining = list_projects(uid)
        new_pid = remaining[0]["id"] if remaining else create_project(uid)
        st.session_state.current_project_id = new_pid
        st.session_state.work_session_restored_global = True
        st.rerun()

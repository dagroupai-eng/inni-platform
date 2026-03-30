"""
analysis_runs / analysis_steps 저장/조회 헬퍼.

주의: database.db_manager.execute_query는 SQL 파싱 기반이므로
단순 SELECT/INSERT/UPDATE 패턴만 사용한다.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


def create_run(
    user_id: int,
    project_id: int,
    input_snapshot: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    try:
        from database.db_manager import execute_query, get_last_insert_id
        execute_query(
            """
            INSERT INTO analysis_runs (project_id, user_id, status, input_snapshot)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, user_id, 'running', json.dumps(input_snapshot or {}, ensure_ascii=False)),
            commit=True,
        )
        return get_last_insert_id()
    except Exception as e:
        print(f"[AnalysisSteps] create_run 오류: {e}")
        return None


def finalize_run(run_id: int, status: str = "completed") -> bool:
    try:
        from database.supabase_client import get_supabase_client
        from datetime import datetime
        client = get_supabase_client()
        client.table('analysis_runs').update({
            'status': status,
            'finished_at': datetime.now().isoformat(),
        }).eq('id', run_id).execute()
        return True
    except Exception as e:
        print(f"[AnalysisSteps] finalize_run 오류: {e}")
        return False


def create_steps(
    run_id: int,
    project_id: int,
    user_id: int,
    blocks: List[Dict[str, Any]],
) -> Dict[str, int]:
    """
    blocks: [{"id": "...", "name": "..."}] 순서대로 step_index 부여.
    Returns: {block_id: step_id}
    """
    from database.db_manager import execute_query, get_last_insert_id

    mapping: Dict[str, int] = {}
    for idx, b in enumerate(blocks, start=1):
        bid = str(b.get("id", "")).strip()
        if not bid:
            continue
        bname = b.get("name") or bid
        execute_query(
            """
            INSERT INTO analysis_steps
                (run_id, project_id, user_id, block_id, block_name, step_index, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, project_id, user_id, bid, bname, idx, 'pending'),
            commit=True,
        )
        mapping[bid] = get_last_insert_id()
    return mapping


def get_latest_run(project_id: int) -> Optional[Dict[str, Any]]:
    try:
        from database.db_manager import execute_query
        rows = execute_query(
            """
            SELECT id, project_id, user_id, status, input_snapshot, created_at
            FROM analysis_runs
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_id,),
        )
        if not rows:
            return None
        r = dict(rows[0])
        raw = r.get("input_snapshot")
        if isinstance(raw, str) and raw:
            try:
                r["input_snapshot"] = json.loads(raw)
            except Exception:
                pass
        return r
    except Exception as e:
        print(f"[AnalysisSteps] get_latest_run 오류: {e}")
        return None


def list_steps(run_id: int) -> List[Dict[str, Any]]:
    try:
        from database.db_manager import execute_query
        rows = execute_query(
            """
            SELECT id, run_id, project_id, user_id, block_id, block_name, step_index,
                   status, started_at, finished_at, inputs, outputs, error, created_at
            FROM analysis_steps
            WHERE run_id = ?
            ORDER BY step_index ASC
            """,
            (run_id,),
        )
        steps = []
        for row in rows or []:
            d = dict(row)
            for k in ("inputs", "outputs"):
                raw = d.get(k)
                if isinstance(raw, str) and raw:
                    try:
                        d[k] = json.loads(raw)
                    except Exception:
                        pass
            steps.append(d)
        return steps
    except Exception as e:
        print(f"[AnalysisSteps] list_steps 오류: {e}")
        return []


def set_step_status(step_id: int, status: str, error: Optional[str] = None) -> bool:
    try:
        from database.supabase_client import get_supabase_client
        from datetime import datetime
        client = get_supabase_client()
        update_data: dict = {'status': status}
        if error is not None:
            update_data['error'] = error
        if status == 'running':
            update_data['started_at'] = datetime.now().isoformat()
        elif status in ('completed', 'failed', 'skipped', 'cancelled'):
            update_data['finished_at'] = datetime.now().isoformat()
        client.table('analysis_steps').update(update_data).eq('id', step_id).execute()
        return True
    except Exception as e:
        print(f"[AnalysisSteps] set_step_status 오류: {e}")
        return False


def save_step_payloads(
    step_id: int,
    inputs: Optional[Dict[str, Any]] = None,
    outputs: Optional[Dict[str, Any]] = None,
) -> bool:
    try:
        from database.db_manager import execute_query
        execute_query(
            "UPDATE analysis_steps SET inputs = ?, outputs = ? WHERE id = ?",
            (
                json.dumps(inputs or {}, ensure_ascii=False),
                json.dumps(outputs or {}, ensure_ascii=False),
                step_id,
            ),
            commit=True,
        )
        return True
    except Exception as e:
        print(f"[AnalysisSteps] save_step_payloads 오류: {e}")
        return False


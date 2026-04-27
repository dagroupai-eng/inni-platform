"""
analysis_runs / analysis_steps 저장/조회 헬퍼.

주의: database.db_manager.execute_query는 SQL 파싱 기반이므로
단순 SELECT/INSERT/UPDATE 패턴만 사용한다.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


_last_cleanup_time: float = 0.0
_CLEANUP_INTERVAL_SECONDS: float = 300.0  # 5분에 1번만 실행


def cleanup_stale_runs(
    run_stale_hours: int = 3,
    step_stale_minutes: int = 20,
) -> None:
    """
    비정상 종료로 running 상태에 고착된 rows를 자동 정리합니다.
    - analysis_runs: run_stale_hours 이상 running → cancelled
    - analysis_steps: step_stale_minutes 이상 running → failed

    모듈 레벨 디바운스(_CLEANUP_INTERVAL_SECONDS)로 서버 프로세스당 5분에 1회만 실행.
    create_run() 호출 시 자동으로 실행됩니다.
    """
    global _last_cleanup_time
    import time
    now_ts = time.monotonic()
    if now_ts - _last_cleanup_time < _CLEANUP_INTERVAL_SECONDS:
        return
    _last_cleanup_time = now_ts

    try:
        from database.supabase_client import get_supabase_client
        from datetime import datetime, timezone, timedelta
        client = get_supabase_client()
        now = datetime.now(timezone.utc)
        finished = now.isoformat()

        run_cutoff = (now - timedelta(hours=run_stale_hours)).isoformat()
        result = client.table('analysis_runs').update({
            'status': 'cancelled',
            'finished_at': finished,
        }).eq('status', 'running').lt('created_at', run_cutoff).execute()
        n_runs = len(result.data) if result.data else 0
        if n_runs:
            print(f"[AnalysisSteps] stale runs {n_runs}개 cancelled 처리")

        step_cutoff = (now - timedelta(minutes=step_stale_minutes)).isoformat()
        result2 = client.table('analysis_steps').update({
            'status': 'failed',
            'finished_at': finished,
            'error': f'자동 정리: {step_stale_minutes}분 초과',
        }).eq('status', 'running').lt('started_at', step_cutoff).execute()
        n_steps = len(result2.data) if result2.data else 0
        if n_steps:
            print(f"[AnalysisSteps] stale steps {n_steps}개 failed 처리")

    except Exception as e:
        print(f"[AnalysisSteps] cleanup_stale_runs 오류: {e}")


def create_run(
    user_id: int,
    project_id: int,
    input_snapshot: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    cleanup_stale_runs()
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
    """inputs/outputs 중 None이 아닌 필드만 업데이트 (기존 데이터 보호)."""
    try:
        update_data: Dict[str, Any] = {}
        if inputs is not None:
            update_data['inputs'] = inputs
        if outputs is not None:
            update_data['outputs'] = outputs
        if not update_data:
            return True
        from database.supabase_client import get_supabase_client
        client = get_supabase_client()
        client.table('analysis_steps').update(update_data).eq('id', step_id).execute()
        return True
    except Exception as e:
        print(f"[AnalysisSteps] save_step_payloads 오류: {e}")
        return False


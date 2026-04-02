"""
분析 대기열 관리 모듈.
동시 분析 제한: processing 상태 행 수 ≤ MAX_CONCURRENT
"""
from __future__ import annotations
from typing import Optional


MAX_CONCURRENT = 2


def _client():
    from database.supabase_client import get_supabase_client
    return get_supabase_client()


STALE_MINUTES = 30  # 이 시간 이상 processing 상태인 행은 비정상 종료로 간주


def cleanup_stale() -> int:
    """비정상 종료로 잔류한 processing 행을 삭제합니다.
    started_at 기준 STALE_MINUTES 이상 경과한 행 대상.
    반환값: 삭제된 행 수."""
    from datetime import datetime, timezone, timedelta
    client = _client()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=STALE_MINUTES)).isoformat()
    try:
        result = client.table('analysis_queue').delete() \
            .eq('status', 'processing').lt('started_at', cutoff).execute()
        removed = len(result.data) if result.data else 0
        if removed:
            print(f"[Queue] stale processing 행 {removed}개 정리 완료")
        return removed
    except Exception as e:
        print(f"[Queue] cleanup_stale 오류: {e}")
        return 0


def enter_queue(user_id: int, project_id: Optional[int] = None, team_id: Optional[int] = None) -> None:
    """대기열 진입. 이미 있으면 무시. 진입 전 stale 행 자동 정리."""
    cleanup_stale()
    client = _client()
    existing = client.table('analysis_queue').select('id').eq('user_id', user_id).execute()
    if existing.data:
        return
    client.table('analysis_queue').insert({
        'user_id': user_id,
        'project_id': project_id,
        'team_id': team_id,
        'status': 'waiting',
    }).execute()


def start_processing(user_id: int) -> None:
    """status → 'processing', started_at 기록."""
    from datetime import datetime, timezone
    client = _client()
    client.table('analysis_queue').update({
        'status': 'processing',
        'started_at': datetime.now(timezone.utc).isoformat(),
    }).eq('user_id', user_id).execute()


def exit_queue(user_id: int) -> None:
    """대기열에서 제거 (분析 완료/중단/오류 시)."""
    _client().table('analysis_queue').delete().eq('user_id', user_id).execute()


def can_process(user_id: int, team_id: Optional[int] = None) -> bool:
    """내 차례이고 팀 슬롯이 있으면 True. team_id가 있으면 팀 단위로 제한."""
    client = _client()

    # 현재 팀 내 processing 수
    proc_qb = client.table('analysis_queue').select('id', count='exact').eq('status', 'processing')
    if team_id is not None:
        proc_qb = proc_qb.eq('team_id', team_id)
    proc = proc_qb.execute()
    processing_count = proc.count or 0

    if processing_count >= MAX_CONCURRENT:
        return False

    # 내 행 조회
    my = client.table('analysis_queue').select('status', 'entered_at').eq('user_id', user_id).execute()
    if not my.data:
        return False

    my_row = my.data[0]
    if my_row['status'] == 'processing':
        return True  # 이미 processing 중

    my_entered_at = my_row['entered_at']

    # 나보다 먼저 들어온 팀 내 waiting 행 수
    ahead_qb = client.table('analysis_queue').select('id', count='exact') \
        .eq('status', 'waiting').lt('entered_at', my_entered_at)
    if team_id is not None:
        ahead_qb = ahead_qb.eq('team_id', team_id)
    ahead = ahead_qb.execute()
    ahead_count = ahead.count or 0

    available_slots = MAX_CONCURRENT - processing_count
    return ahead_count < available_slots


def get_queue_info(user_id: int, team_id: Optional[int] = None) -> dict:
    """내 대기 상태 반환: {in_queue, status, position}. team_id 기준 대기 순서."""
    client = _client()
    my = client.table('analysis_queue').select('status', 'entered_at').eq('user_id', user_id).execute()
    if not my.data:
        return {'in_queue': False}

    my_row = my.data[0]
    if my_row['status'] == 'processing':
        return {'in_queue': True, 'status': 'processing', 'position': 0}

    ahead_qb = client.table('analysis_queue').select('id', count='exact') \
        .eq('status', 'waiting').lt('entered_at', my_row['entered_at'])
    if team_id is not None:
        ahead_qb = ahead_qb.eq('team_id', team_id)
    ahead = ahead_qb.execute()
    ahead_count = ahead.count or 0

    return {
        'in_queue': True,
        'status': 'waiting',
        'position': ahead_count + 1,  # 1-based
    }

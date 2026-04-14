"""
분析 대기열 관리 모듈.
동시 분析 제한: 같은 서버(A/B) 내 processing 상태 행 수 ≤ MAX_CONCURRENT
"""
from __future__ import annotations
from typing import Optional


MAX_CONCURRENT = 3


def _client():
    from database.supabase_client import get_supabase_client
    return get_supabase_client()


STALE_MINUTES = 8          # processing 상태 최대 허용 시간 (파일 1개 기준 — heartbeat로 리셋)
STALE_WAITING_MINUTES = 5  # waiting 상태 최대 허용 시간 (브라우저 종료 등 비정상 대기 정리)


def cleanup_stale() -> int:
    """비정상 종료로 잔류한 processing/waiting 행을 삭제합니다.
    - processing: started_at 기준 STALE_MINUTES 이상 경과
    - waiting: entered_at 기준 STALE_WAITING_MINUTES 이상 경과
    반환값: 삭제된 총 행 수."""
    from datetime import datetime, timezone, timedelta
    client = _client()
    now = datetime.now(timezone.utc)
    removed = 0

    # processing 행 정리
    cutoff_proc = (now - timedelta(minutes=STALE_MINUTES)).isoformat()
    try:
        result = client.table('analysis_queue').delete() \
            .eq('status', 'processing').lt('started_at', cutoff_proc).execute()
        n = len(result.data) if result.data else 0
        if n:
            print(f"[Queue] stale processing 행 {n}개 정리 완료")
        removed += n
    except Exception as e:
        print(f"[Queue] cleanup_stale(processing) 오류: {e}")

    # waiting 행 정리 (브라우저 종료 등으로 대기만 남은 경우)
    cutoff_wait = (now - timedelta(minutes=STALE_WAITING_MINUTES)).isoformat()
    try:
        result2 = client.table('analysis_queue').delete() \
            .eq('status', 'waiting').lt('entered_at', cutoff_wait).execute()
        n2 = len(result2.data) if result2.data else 0
        if n2:
            print(f"[Queue] stale waiting 행 {n2}개 정리 완료")
        removed += n2
    except Exception as e:
        print(f"[Queue] cleanup_stale(waiting) 오류: {e}")

    return removed


def enter_queue(user_id: int, project_id: Optional[int] = None, server: Optional[str] = None) -> None:
    """대기열 진입. 이미 있으면 무시. 진입 전 stale 행 자동 정리."""
    cleanup_stale()
    client = _client()
    existing = client.table('analysis_queue').select('id').eq('user_id', user_id).execute()
    if existing.data:
        return
    client.table('analysis_queue').insert({
        'user_id': user_id,
        'project_id': project_id,
        'server': server,
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


def try_start_processing(user_id: int, server: Optional[str] = None) -> bool:
    """processing 전환 후 즉시 서버 슬롯 재검증. 슬롯 초과 시 waiting으로 롤백.
    반환값: True = 처리 가능, False = 슬롯 초과(대기 재시도 필요).
    Race condition 방어용: can_process()와 start_processing() 사이 간격을 제거."""
    from datetime import datetime, timezone
    client = _client()

    # 1. 먼저 processing으로 전환
    client.table('analysis_queue').update({
        'status': 'processing',
        'started_at': datetime.now(timezone.utc).isoformat(),
    }).eq('user_id', user_id).execute()

    # 2. 즉시 재검증: 서버 내 processing 수 확인
    proc_qb = client.table('analysis_queue').select('id', count='exact').eq('status', 'processing')
    if server is not None:
        proc_qb = proc_qb.eq('server', server)
    processing_count = proc_qb.execute().count or 0

    if processing_count > MAX_CONCURRENT:
        # 슬롯 초과 → waiting으로 롤백
        client.table('analysis_queue').update({
            'status': 'waiting',
            'started_at': None,
        }).eq('user_id', user_id).execute()
        return False

    return True


def exit_queue(user_id: int) -> None:
    """대기열에서 제거 (분析 완료/중단/오류 시)."""
    _client().table('analysis_queue').delete().eq('user_id', user_id).execute()


def update_heartbeat(user_id: int) -> None:
    """파일 1개 완료 시 heartbeat 갱신 — started_at을 현재 시각으로 리셋해 stale 타이머를 초기화합니다."""
    from datetime import datetime, timezone
    _client().table('analysis_queue').update({
        'started_at': datetime.now(timezone.utc).isoformat(),
    }).eq('user_id', user_id).eq('status', 'processing').execute()


def can_process(user_id: int, server: Optional[str] = None) -> bool:
    """내 차례이고 서버 슬롯이 있으면 True. server가 있으면 서버 단위로 제한."""
    client = _client()

    # 현재 서버 내 processing 수
    proc_qb = client.table('analysis_queue').select('id', count='exact').eq('status', 'processing')
    if server is not None:
        proc_qb = proc_qb.eq('server', server)
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

    # 나보다 먼저 들어온 서버 내 waiting 행 수
    ahead_qb = client.table('analysis_queue').select('id', count='exact') \
        .eq('status', 'waiting').lt('entered_at', my_entered_at)
    if server is not None:
        ahead_qb = ahead_qb.eq('server', server)
    ahead = ahead_qb.execute()
    ahead_count = ahead.count or 0

    available_slots = MAX_CONCURRENT - processing_count
    return ahead_count < available_slots


def get_queue_info(user_id: int, server: Optional[str] = None) -> dict:
    """내 대기 상태 반환: {in_queue, status, position}. 서버 기준 대기 순서."""
    client = _client()
    my = client.table('analysis_queue').select('status', 'entered_at').eq('user_id', user_id).execute()
    if not my.data:
        return {'in_queue': False}

    my_row = my.data[0]
    if my_row['status'] == 'processing':
        return {'in_queue': True, 'status': 'processing', 'position': 0}

    ahead_qb = client.table('analysis_queue').select('id', count='exact') \
        .eq('status', 'waiting').lt('entered_at', my_row['entered_at'])
    if server is not None:
        ahead_qb = ahead_qb.eq('server', server)
    ahead = ahead_qb.execute()
    ahead_count = ahead.count or 0

    return {
        'in_queue': True,
        'status': 'waiting',
        'position': ahead_count + 1,  # 1-based
    }

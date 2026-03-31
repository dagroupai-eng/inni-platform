# -*- coding: utf-8 -*-
"""
Supabase 연동 상태 진단 스크립트

실행 방법:
  SUPABASE_URL=https://xxx.supabase.co SUPABASE_SERVICE_ROLE_KEY=xxx python check_supabase.py
"""

import os
import sys
import json
import io
from datetime import datetime

# Windows 터미널 UTF-8 강제
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── 환경변수 로드 ────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY 환경변수가 없습니다.")
    sys.exit(1)

from supabase import create_client
client = create_client(SUPABASE_URL, SUPABASE_KEY)

OK  = "[OK] "
NG  = "[NG] "
WARN = "[!!] "

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check(label, ok, detail=""):
    icon = OK if ok else NG
    msg = f"  {icon}{label}"
    if detail:
        msg += f"\n       -> {detail}"
    print(msg)


# ── A. 인증 / 사용자 ────────────────────────────────────────────────────────
section("A. 인증 / 사용자")

try:
    r = client.table("users").select("id, personal_number, role, last_login, team_id").execute()
    users = r.data or []
    check("users 테이블 조회", True, f"{len(users)}명 존재")
    for u in users[:5]:
        print(f"       - id={u['id']} | {u.get('personal_number')} | role={u.get('role')} | last_login={u.get('last_login')} | team_id={u.get('team_id')}")
except Exception as e:
    check("users 테이블 조회", False, str(e))

try:
    r = client.table("teams").select("id, name").execute()
    teams = r.data or []
    check("teams 테이블 조회", True, f"{len(teams)}개 팀 존재")
    for t in teams[:5]:
        print(f"       - id={t['id']} | {t.get('name')}")
except Exception as e:
    check("teams 테이블 조회", False, str(e))

try:
    r = client.table("user_settings").select("user_id, settings_data, updated_at").execute()
    rows = r.data or []
    check("user_settings 테이블 조회", True, f"{len(rows)}행 존재")
    for row in rows[:5]:
        settings = row.get("settings_data") or {}
        session = settings.get("_session")
        if session:
            expires = session.get("expires_at", "")
            expired = expires and datetime.fromisoformat(expires) < datetime.now()
            status = "만료됨" if expired else "유효"
            print(f"       - user_id={row['user_id']} | _session {status} (expires: {expires[:19] if expires else 'N/A'})")
        else:
            print(f"       - user_id={row['user_id']} | _session 없음 (로그아웃 상태)")
except Exception as e:
    check("user_settings 테이블 조회", False, str(e))


# ── B. 프로젝트 / 세션 ───────────────────────────────────────────────────────
section("B. 프로젝트 / 세션")

try:
    r = client.table("projects").select("id, user_id, name, location, status, updated_at").execute()
    projects = r.data or []
    check("projects 테이블 조회", True, f"{len(projects)}개 프로젝트")
    for p in projects[:5]:
        print(f"       - id={p['id']} | {p.get('name')} | location={p.get('location')} | status={p.get('status')}")
except Exception as e:
    check("projects 테이블 조회", False, str(e))

try:
    r = client.table("analysis_sessions").select("id, user_id, project_id, created_at").execute()
    rows = r.data or []
    check("analysis_sessions 테이블 조회", True, f"{len(rows)}행 존재")
    for row in rows[:3]:
        print(f"       - id={row['id']} | user_id={row['user_id']} | project_id={row['project_id']} | created={row.get('created_at','')[:19]}")
except Exception as e:
    check("analysis_sessions 테이블 조회", False, str(e))

try:
    r = client.table("analysis_progress").select("id, user_id, updated_at, progress_data").execute()
    rows = r.data or []
    check("analysis_progress 테이블 조회", True, f"{len(rows)}행 존재")
    for row in rows[:3]:
        pd = row.get("progress_data") or {}
        has_queue = "_queue" in pd
        has_cot = bool(pd.get("cot_results") or pd.get("cot_session"))
        flags = []
        if has_queue:
            flags.append(f"queue={pd['_queue'].get('status')}")
        if has_cot:
            flags.append("cot_results 있음")
        print(f"       - user_id={row['user_id']} | updated={row.get('updated_at','')[:19]} | {', '.join(flags) or '데이터 없음'}")
except Exception as e:
    check("analysis_progress 테이블 조회", False, str(e))


# ── C. 파일 / Storage ────────────────────────────────────────────────────────
section("C. 파일 / Storage")

try:
    r = client.table("project_files").select("id, user_id, project_id, filename, storage_path, created_at").execute()
    rows = r.data or []
    check("project_files 테이블 조회", True, f"{len(rows)}개 파일 레코드")
    for row in rows[:3]:
        print(f"       - id={row['id']} | {row.get('filename')} | path={row.get('storage_path')}")
except Exception as e:
    check("project_files 테이블 조회", False, str(e))

try:
    r = client.storage.from_("project-files").list("")
    items = r or []
    check("Storage project-files 버킷 접근", True, f"루트에 {len(items)}개 항목")
except Exception as e:
    check("Storage project-files 버킷 접근", False, str(e))


# ── D. 블록 ──────────────────────────────────────────────────────────────────
section("D. 블록")

try:
    r = client.table("blocks").select("id, owner_id, block_id, name, visibility, created_at").execute()
    rows = r.data or []
    check("blocks 테이블 조회", True, f"{len(rows)}개 블록")
    for row in rows[:5]:
        print(f"       - id={row['id']} | block_id={row.get('block_id')} | {row.get('name')} | visibility={row.get('visibility')}")
except Exception as e:
    check("blocks 테이블 조회", False, str(e))


# ── F. 문서 분석 ─────────────────────────────────────────────────────────────
section("F. 문서 분석 (analysis_runs / analysis_steps)")

try:
    r = client.table("analysis_runs").select("id, user_id, project_id, status, created_at, finished_at").order("created_at", desc=True).limit(5).execute()
    rows = r.data or []
    check("analysis_runs 테이블 조회", True, f"최근 {len(rows)}개 run")
    for row in rows:
        finished = row.get("finished_at")
        finished_str = finished[:19] if finished else "NULL [!!] (분석 미완료 또는 컬럼 미기록)"
        print(f"       - id={row['id']} | status={row.get('status')} | created={row.get('created_at','')[:19]} | finished_at={finished_str}")
except Exception as e:
    check("analysis_runs 테이블 조회", False, str(e))

try:
    r = client.table("analysis_steps").select("id, run_id, block_id, status, started_at, finished_at").order("id", desc=True).limit(10).execute()
    rows = r.data or []
    check("analysis_steps 테이블 조회", True, f"최근 {len(rows)}개 step")
    for row in rows:
        s_at = (row.get("started_at") or "NULL")[:19]
        f_at = (row.get("finished_at") or "NULL")[:19]
        print(f"       - id={row['id']} | run_id={row['run_id']} | block={row.get('block_id')} | status={row.get('status')} | started={s_at} | finished={f_at}")
except Exception as e:
    check("analysis_steps 테이블 조회", False, str(e))


# ── 요약 ─────────────────────────────────────────────────────────────────────
section("진단 완료")
print("  위 결과를 보고 ⚠️  또는 ❌ 항목을 확인하세요.")
print("  finished_at=NULL → 분석 완료 후에도 NULL이면 finalize_run() 미호출 또는 컬럼 미생성")
print("  _session 유효 상태인데 로그아웃한 경우 → delete_session() 수정 전 데이터 잔류\n")

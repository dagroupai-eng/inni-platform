# 해야 할 일 목록

## 즉시 처리

- [x] **1. 삭제/정리 변경사항 커밋 & push** ✅ `959bd6c` → push 완료

---

## Supabase 확인/설정

- [x] **2. Supabase 테이블 확인** ✅
  - 11개 테이블 모두 존재 확인
  - blocks, user_settings 신규 생성 완료

- [x] **2-1. Supabase 스키마 보완 (SQL 실행 완료)** ✅
  - `analysis_runs.finished_at` 컬럼 추가
  - `blocks.block_id` UNIQUE 제약 추가
  - `analysis_progress` UNIQUE 제약: `user_id` 단독 → `(user_id, project_id)` 복합으로 변경 (프로젝트별 진행 상태 분리)

- [x] **2-2. analysis_progress 테이블 제거** ✅
  - `analysis_progress` 테이블 Supabase에서 DROP 완료
  - 기존 기능은 `analysis_sessions` UPSERT로 통합 (`auth/session_init.py`)
  - `analysis_sessions`에 UNIQUE(user_id, project_id) 제약 추가 완료

- [x] **2-3. analysis_queue 테이블 생성** ✅
  - Supabase에서 `[]` 응답 확인 → 테이블 존재, 빈 상태 정상

---

## Supabase 연동 기능별 동작 확인

> 실제 배포 환경에서 아래 항목을 순서대로 테스트한다.

### 진단 스크립트
- `check_supabase.py` 실행 방법:
  ```
  SUPABASE_URL=xxx SUPABASE_SERVICE_ROLE_KEY=yyy python check_supabase.py
  ```
  (환경: `da_AI_env` 사용 → `/c/Users/dA/miniconda3/envs/da_AI_env/python.exe check_supabase.py`)

### A. 인증 / 사용자

| # | 기능 | 관련 파일 | 연동 테이블 | 확인 |
|---|------|-----------|------------|------|
| A-1 | 로그인 | `auth/user_manager.py` | `users` | [x] users 24명, last_login 기록 정상 |
| A-2 | 로그아웃 | `auth/session_manager.py` | `user_settings` | [x] 코드 수정 완료 (로그아웃 시 DB _session 제거) |
| A-3 | 팀 접근 제한 | `auth/user_manager.py` | `users`, `teams` | [x] teams 6개 정상 확인 |

> user_id=4,15,23 의 `_session` 잔류분(만료됨): 코드 수정 전 데이터, 보안 무해

### B. 프로젝트 / 세션

| # | 기능 | 관련 파일 | 연동 테이블 | 확인 |
|---|------|-----------|------------|------|
| B-1 | 프로젝트 생성/조회 | `auth/project_manager.py` | `projects` | [x] projects 2개 확인. ~~status에 타임스탬프 저장 버그~~ → Supabase 직접 수정 완료 (in_progress) |
| B-2 | 작업 세션 저장/복원 | `auth/session_init.py` | `analysis_sessions` | [x] analysis_sessions 2행(project=6,7) UPSERT 정상 |
| B-3 | 분析 진행 저장/복원 | `auth/session_init.py` | `analysis_sessions` | [x] 분析 실행 → session 저장 → 재접속 복원 동작 확인 완료 |

### C. 파일 업로드 / Storage

| # | 기능 | 관련 파일 | 연동 | 확인 |
|---|------|-----------|------|------|
| C-1 | 파일 업로드 | `auth/file_storage.py` | Storage `project-files` 버킷 | [제외] 버킷 존재 확인(private). 실 테스트 생략 결정 |
| C-2 | 파일 다운로드 | `auth/file_storage.py` | Storage `project-files` 버킷 | [제외] |
| C-3 | 파일 삭제 (DB+Storage 동시) | `auth/file_storage.py` | `project_files` 테이블 + Storage | [제외] |

### D. 블록 생성

| # | 기능 | 관련 파일 | 연동 테이블 | 확인 |
|---|------|-----------|------------|------|
| D-1 | 블록 생성/저장 | `blocks/block_manager.py` | `blocks` | [x] personal/team 블록 생성 정상 |
| D-2 | 블록 조회 (등급별) | `blocks/block_manager.py` | `blocks` | [x] get_accessible_blocks 정상 (팀원 가시성 수정 포함) |
| D-3 | 블록 수정/삭제 | `blocks/block_manager.py` | `blocks` | [x] 소유자만 수정/삭제 가능 확인 |

### E. 지도 (Mapping)

| # | 기능 | 관련 파일 | 연동 | 확인 |
|---|------|-----------|------|------|
| E-1 | 필지 클릭 → 폴리곤 표시 | `pages/2_Mapping.py` | VWorld WFS API (DB 없음) | [x] 서버 IP 등록 후 정상 동작 확인 |
| E-2 | 필지 선택 → projects.location 저장 | `pages/2_Mapping.py` | `projects` 테이블 | [x] Supabase projects 테이블에 location 저장 확인 |

### F. 문서 분석

| # | 기능 | 관련 파일 | 연동 테이블 | 확인 |
|---|------|-----------|------------|------|
| F-1 | PDF/DOCX 업로드 → 텍스트 추출 | `file_analyzer.py` | (로컬 처리) | [x] 파일 업로드 후 분析 실행 확인 완료 |
| F-2 | 분析 세션 준비 | `pages/3_Document_Analysis.py` | `analysis_runs`, `analysis_steps` | [x] analysis_runs 총 6행(completed×5, cancelled×1) 확인 |
| F-3 | 블록별 분析 실행 → step 상태 업데이트 | `database/analysis_steps_manager.py` | `analysis_steps` | [x] started_at/finished_at 정상. run id=5 stuck→cancelled 처리 완료 |
| F-4 | 분析 완료 → run finalize | `database/analysis_steps_manager.py` | `analysis_runs.finished_at` | [x] run id=6 completed, finished_at=2026-04-02T04:39:57 정상 |

### G. 관리자

| # | 기능 | 관련 파일 | 연동 테이블 | 확인 |
|---|------|-----------|------------|------|
| G-1 | 사용자 목록 조회 | `pages/6_Admin.py` | `users`, `teams` | [x] users 24명, teams 6개 정상 |
| G-2 | 사용자 생성/수정/삭제 | `pages/6_Admin.py` | `users` | [x] 실 동작 확인 완료 |

---

## 코드 수정

- [x] **4. analysis_runs / analysis_steps 저장 로직 추가** ✅ `9962833`
  - INSERT 리터럴 버그 수정, finalize_run() 호출 추가

- [x] **4-추가. projects.status 타임스탬프 저장 버그 수정** ✅
  - 원인: `create_project()` SQL에 `'in_progress'` 리터럴 혼용 → `_build_values`가 컬럼-파라미터 매핑 오류로 status에 timestamp 저장
  - 수정: SQL VALUES 절의 `'in_progress'` 리터럴을 `?`로 교체, 파라미터 튜플에 `'in_progress'` 추가

- [x] **4-추가-2. analysis_progress.project_id=None 버그 수정** ✅
  - 원인: `save_analysis_progress()` INSERT에 `project_id` 컬럼 누락
  - 수정: INSERT 컬럼/VALUES에 `project_id` 추가, `current_project_id` 세션에서 읽어서 전달

- [x] **5. VWorld 필지 선택 버그 수정** ✅ `f908b2f`
  - VWorld 포털 서비스URL에 서버 IP 추가, 진단 로그 추가

- [x] **6. 분석 결과물 퀄리티 개선** ✅ `959bd6c`
  - pdf_text 50000자, blocks.json 제거, [BLOCK_SUMMARY] 태그 연계

- [x] **6-추가-5. 각 탭 저장 버튼 → 프로젝트 연동 + 자동 넘버링** ✅
  - `project_manager.py`: `save_project_from_session()` 추가 — projects 테이블 name/location 업데이트 + analysis_sessions 저장 통합
  - `project_manager.py`: `_resolve_project_name()` 추가 — 이름 중복 시 자동 (1),(2)... 넘버링
  - Tab 1 "프로젝트 정보 저장" / "파일 분석 완료 확인" → 새 함수로 교체
  - Tab 2 "블록 선택 완료" → 새 함수로 교체
  - Tab 4 "분석 결과를 프로젝트에 저장" 버튼 신규 추가

- [x] **6-추가-4. 팀 공유 블록 가시성 버그 수정** ✅
  - 원인: `team_id=None`인 사용자(관리자)가 팀 공유 블록 생성 시 `shared_with_teams=[]`로 저장 → 어떤 팀원도 조회 불가
  - 수정: `_resolve_shared_teams()` 헬퍼 추가 — team_id 없으면 전체 팀 ID 조회 후 공유
  - 적용: 블록 생성/공개범위 변경 두 곳 모두 교체
  - 기존 팀 공유 블록(id=2) `shared_with_teams=[1,2,3,4,5,6]`으로 직접 수정

- [x] **6-추가-3. location 필드 개선** ✅
  - `2_Mapping.py` `_apply_to_analysis()`: 필지 선택 시 `session_state["location"]`에 필지 주소 자동 주입
  - `2_Mapping.py`: 대표 필지 lat/lon을 `session_state["latitude"]`, `["longitude"]`에 자동 설정 (Google Maps 블록용)
  - `3_Document_Analysis.py`: 좌표 직접 입력 expander 제거, 지도 연동 안내 문구 추가

- [x] **6-추가-2. 로그아웃 시 Supabase 세션 미정리 버그 수정** ✅
  - `delete_session()`: 로컬 파일 삭제 전 `user_id` 읽어서 `_clear_session_supabase()` 호출
  - `_clear_session_supabase(user_id)` 함수 추가: `user_settings.settings_data._session` 제거
  - 기존 문제: 로그아웃해도 Supabase에 토큰 잔류 → 서버 재시작 후 만료 전 자동 로그인 가능

- [x] **6-추가. DB 버그 수정** ✅
  - `finalize_run()`: `finished_at` 타임스탬프 기록 추가
  - `set_step_status()`: `started_at`/`finished_at` 타임스탬프 기록 추가
  - `delete_project_files()`: Storage 삭제 후 DB 레코드도 함께 삭제

- [x] **6-추가-6. 페이지 초기화 버그 2개 수정** ✅ `76989d0`
  - **Bug A**: 초기화 후 autosave가 빈 세션을 최신 행으로 INSERT → "열기" 시 구 데이터 복원되는 문제
    - `page_just_reset` 플래그로 초기화 직후 첫 rerender의 autosave 1회 스킵
  - **Bug B**: 초기화 후 프로젝트가 선택된 채로 남는 문제
    - `keys_to_reset`에 `current_project_id` 추가

- [x] **6-추가-7. AI 모델 설정 버그 수정** ✅ `dad7494`
  - `dspy_analyzer.py` PROVIDER_CONFIG: Gemini 전용 최신 모델만 유지 (Anthropic/OpenAI 제거)
  - `system_instruction` 문자열 덮어쓰기 버그 수정 (Content format 유지)
  - `thinking_config` 필드 위치 수정: 최상위 → `generationConfig.thinkingConfig` (camelCase)
  - `dict.copy()` → `copy.deepcopy()` (중첩 dict 복원 버그)
  - 하드코딩된 Gemini provider 목록 체크 → `PROVIDER_CONFIG` 동적 조회로 전환

- [x] **6-추가-8. analysis_sessions UPSERT 전환 + 대역폭 절감** ✅
  - `analysis_sessions` INSERT → INSERT OR REPLACE (UPSERT) 전환 — 1행 유지 보장
  - `analysis_progress` 테이블 제거 → `save/restore_analysis_progress()` 모두 `analysis_sessions`로 위임
  - `load_project_session()` 불필요 코드 제거 (LIMIT 20 → LIMIT 1, `_fill_keys` 병합 로직 삭제)
  - `pdf_text`, `preprocessed_text`, `reference_combined_text` save_keys에서 제외 (23명 동시 사용 고려)
  - 프로젝트 로드 후 파일 재업로드 안내 메시지 추가 (파일 업로드 탭, 분석 실행 탭)
  - "☁️ 저장된 업로드 파일" expander 제거

- [x] **7. 분석 대기열(Queue) 시스템 구현** ✅

  ### 설계: analysis_queue 전용 테이블 사용 (analysis_progress 삭제됨)
  - 신규 테이블 `analysis_queue` 사용 (2-3 항목에서 생성)
  - 동시 분석 제한: processing 상태 row 수 ≤ 2

  ### 구현 항목
  - [ ] Supabase에 `analysis_queue` 테이블 생성 (→ 2-3 항목 참고)
  - [ ] `database/queue_manager.py` 생성
    - `enter_queue(user_id, project_id)` — 대기열 진입 (upsert)
    - `exit_queue(user_id)` — 대기열 제거 (delete)
    - `get_position(user_id)` — 내 대기 순서 반환
    - `get_processing_count()` — processing 수 조회
    - `can_process(user_id)` — 내 차례 여부 (processing < 2)
  - [ ] `pages/3_Document_Analysis.py` 수정
    - 🚀 버튼 클릭 시 → `enter_queue()` → 슬롯 여유 있으면 바로 시작, 없으면 대기 UI
    - 분석 완료/중단(`finally` 블록) 시 → `exit_queue()`

---

## 우선 확인 항목 (Queue 구현 전 필수)

### ① B-3: 분석 진행 복원 동작 확인 (변경됨)
- `analysis_progress` 테이블 삭제 후 `analysis_sessions`로 전환됨
- 확인 방법: 분석 세션 준비 → 중간 이탈 → 재접속 시 복원 배너 뜨는지 (사이드바 "세션 관리")
- `restore_analysis_progress()`가 `analysis_sessions`에서 1시간 이내 데이터를 올바르게 읽는지 확인
- [x] 확인 완료

### ② 페이지 초기화 버그 수정 확인
- 분석 진행 → "현재 작업 저장" → "페이지 초기화" → 프로젝트 "열기"
- 기대 동작:
  - 초기화 후 프로젝트가 선택 해제되어 있는지 확인 (Bug B)
  - "열기" 후 최신 분석 결과가 복원되는지 확인 (Bug A)
- [x] 확인 완료

### ③ F-2 → F-3 → F-4: 분석 실행 1회 end-to-end 확인
- 실제 PDF/DOCX 파일로 분석 1회 완전히 돌린 후 Supabase에서 직접 확인:
  - `analysis_runs` 행 생성 여부 + `finished_at` 값 입력 여부
  - `analysis_steps` 각 블록별 `status`, `started_at`, `finished_at` 기록 여부
- **확인 방법 (Supabase Dashboard):**
  1. Supabase Dashboard → 좌측 Table Editor
  2. `analysis_runs` 테이블 선택 → 최신 행의 `finished_at` 컬럼에 값이 있는지 확인
  3. `analysis_steps` 테이블 선택 → 해당 `run_id`로 필터 → 각 행의 `status` / `started_at` / `finished_at` 확인
- [x] 확인 완료

---

## 배포 마무리

- [x] **8. 기능 테스트** ✅ — 전 항목 확인 완료 (C-1~C-3 파일 Storage 테스트 제외 결정)

- [ ] **9. 0119 브랜치 정리**
  - master로 머지 완료됐으므로 0119 브랜치 삭제 여부 결정

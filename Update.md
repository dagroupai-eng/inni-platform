# 해야 할 일 목록

## 즉시 처리

- [x] **1. 삭제/정리 변경사항 커밋 & push** ✅ `959bd6c` → push 완료

---

## Supabase 확인/설정

- [x] **2. Supabase 테이블 확인** ✅
  - 11개 테이블 모두 존재 확인
  - blocks, user_settings 신규 생성 완료

- [ ] **2-1. Supabase 스키마 보완 (SQL 실행 필요)**
  - `analysis_runs` 테이블에 `finished_at` 컬럼 추가:
    ```sql
    ALTER TABLE public.analysis_runs ADD COLUMN IF NOT EXISTS finished_at timestamp with time zone;
    ```
  - `blocks` 테이블에 `block_id` UNIQUE 제약 추가:
    ```sql
    ALTER TABLE public.blocks ADD CONSTRAINT blocks_block_id_key UNIQUE (block_id);
    ```

- [ ] **3. project-files 버킷 Storage Policy 설정**
  - 현재 Policies: 0 → service_role 키로 우회 중이라 당장 오류는 아니지만 보안상 필요
  - Supabase Dashboard → Storage → project-files → Policies → Add policy
  - 권장 정책: 인증된 사용자만 자신의 경로(`{user_id}/`)에 읽기/쓰기 허용

---

## 코드 수정

- [x] **4. analysis_runs / analysis_steps 저장 로직 추가** ✅ `9962833`
  - INSERT 리터럴 버그 수정, finalize_run() 호출 추가

- [x] **5. VWorld 필지 선택 버그 수정** ✅ `f908b2f`
  - VWorld 포털 서비스URL에 서버 IP 추가, 진단 로그 추가

- [x] **6. 분석 결과물 퀄리티 개선** ✅ `959bd6c`
  - pdf_text 50000자, blocks.json 제거, [BLOCK_SUMMARY] 태그 연계

- [x] **6-추가. DB 버그 수정** ✅ (커밋 예정)
  - `finalize_run()`: `finished_at` 타임스탬프 기록 추가
  - `set_step_status()`: `started_at`/`finished_at` 타임스탬프 기록 추가
  - `delete_project_files()`: Storage 삭제 후 DB 레코드도 함께 삭제

- [ ] **7. 분석 대기열(Queue) 시스템 구현**

  ### 설계: analysis_progress 테이블 재활용
  - 기존 `analysis_progress` (id, user_id, project_id, progress_data jsonb) 활용
  - `progress_data` 안에 queue 상태 저장:
    ```json
    {
      "queue_status": "waiting|processing|done",
      "position": 2,
      "entered_at": "ISO시간",
      "started_at": "ISO시간"
    }
    ```
  - 장점: 신규 테이블 불필요, user_id UNIQUE로 1인 1슬롯 보장
  - 동시 분석 제한: processing 상태 row 수 ≤ 2

  ### 구현 항목
  - [ ] `database/queue_manager.py` 생성 (enter_queue, exit_queue, get_position, get_processing_count)
  - [ ] `pages/3_Document_Analysis.py` 분석 시작 시 queue 진입 → 대기 UI 표시
  - [ ] 분석 완료/취소 시 queue에서 자동 제거
  - [ ] 페이지 이탈 감지 후 queue 정리 (session_state cleanup)

---

## 배포 마무리

- [ ] **8. 기능 테스트 (배포 후 실제 동작 확인)**
  - 로그인 / 로그아웃
  - 블록 생성 및 저장
  - 지도(VWorld) 필지 클릭 → 폴리곤 표시
  - 문서 분석 (PDF, DOCX)
  - 파일 업로드 → Supabase Storage 저장 확인
  - 관리자 페이지

- [ ] **9. 0119 브랜치 정리**
  - master로 머지 완료됐으므로 0119 브랜치 삭제 여부 결정

# 해야 할 일 목록

## 즉시 처리

- [ ] **1. 삭제/정리 변경사항 커밋 & push**
  - 삭제된 파일들, gitignore 추가, user_manager.py dead code 정리
  - `git push origin master` → 두 서버 자동 배포

---

## Supabase 확인/설정

- [ ] **2. Supabase Table Editor에서 11개 테이블 모두 존재하는지 확인**
  - users, teams, api_keys, blocks, analysis_sessions, user_settings,
    analysis_progress, projects, project_files, analysis_runs, analysis_steps

- [ ] **3. project-files 버킷 Storage Policy 설정**
  - 현재 Policies: 0 → service_role 키로 우회 중이라 당장 오류는 아니지만
  - Supabase Dashboard → Storage → project-files → Policies → Add policy

---

## 코드 수정

- [ ] **4. analysis_runs / analysis_steps 저장 로직 추가**
  - 현재: 조회만 되고 저장이 안 됨 → 분석 기록이 쌓이지 않음
  - pages/3_Document_Analysis.py 분석 실행 시 create_run(), create_steps() 호출 추가

- [ ] **5. VWorld 필지 선택 버그 수정**
  - 증상: 필지 클릭 시 영역(폴리곤)이 그려지지 않고 선택도 안 됨
  - 원인 파악 필요: pages/2_Mapping.py VWorld API 호출 및 필지 레이어 처리 로직 검토
  - 서울 리전 서버에서 VWorld 직접 호출로 변경 후 발생한 문제인지 확인

- [ ] **6. 분석 결과물 퀄리티 개선**

  ### 6-1. prompt_processor.py — pdf_text 8000자 제한 해제
  - 현재 Gemini임에도 8000자로 잘리는 경로 존재
  - Gemini 감지 시 제한 해제 (최대 500,000자)
  - 수정 위치: `prompt_processor.py:152`

  ### 6-2. prompt_processor.py — load_blocks() blocks.json 참조 정리
  - 삭제된 blocks.json 참조 제거
  - DB 블록만 로드하도록 정리
  - 수정 위치: `prompt_processor.py:97`

  ### 6-3. 블록 간 연계 참조 개선 (핵심)
  - **현재 문제**: `_extract_key_insights()`가 정규식으로 300자 자름 → 맥락 빈약
  - **개선 방식**: 프롬프트 끝에 요약 섹션 추가 → Gemini가 분석+요약 한 번에 출력
  - **요약 포맷** (프롬프트에 삽입):
    ```
    [BLOCK_SUMMARY]
    • 핵심 발견 1
    • 핵심 발견 2
    • 핵심 발견 3
    [/BLOCK_SUMMARY]
    ```
  - **파싱**: `_extract_key_insights()` → 태그 파싱으로 교체 (추가 API 호출 없음)
  - 수정 위치:
    - `prompt_processor.py` — UNIFIED_PROMPT_TEMPLATE 하단에 요약 섹션 추가
    - `dspy_analyzer.py:3212` — `_build_cot_context()` CoT 프롬프트에도 추가
    - `dspy_analyzer.py:5401` — `_extract_key_insights()` 태그 파싱으로 교체

- [ ] **7. 분석 대기열(Queue) 시스템 구현**
  - Supabase에 `analysis_queue` 테이블 생성
    - 컬럼: id, user_id, project_id, status(waiting/processing/done), created_at
  - 분석 시작 시 queue에 insert → 처리 중인 사람 있으면 대기
  - 유저에게 대기 순서 실시간 표시 (st.rerun() polling 방식)
  - 페이지 이탈 시 queue에서 자동 제거 처리
  - 동시 분석 최대 인원 제한 (권장: 2~3명) → $12 플랜으로 안정적 운영

---

## 배포 마무리

- [ ] **8. 기능 테스트 (배포 후 실제 동작 확인)**
  - 로그인 / 로그아웃
  - 블록 생성 및 저장
  - 지도(VWorld) 표시
  - 문서 분석 (PDF, DOCX)
  - 파일 업로드 → Supabase Storage 저장 확인
  - 관리자 페이지

- [ ] **9. 0119 브랜치 정리**
  - master로 머지 완료됐으므로 0119 브랜치 삭제 여부 결정

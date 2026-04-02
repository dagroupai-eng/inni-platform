# inni-platform 작업 현황

## 완료 항목 요약

| 항목 | 내용 |
|------|------|
| Supabase 테이블 | 11개 전체 확인, blocks/user_settings 신규 생성 |
| analysis_queue | 테이블 생성 완료 (Supabase) |
| analysis_progress | 삭제 → analysis_sessions UPSERT로 통합 |
| 인증/로그인 | users 24명, teams 6개, 로그아웃 세션 정리 버그 수정 |
| 프로젝트 | projects.status 타임스탬프 버그 수정 |
| 블록 | 팀 공유 가시성 버그 수정 |
| 지도 | VWorld WFS IP 등록, location 자동 주입 |
| 문서 분析 | analysis_runs/steps 저장, RAG, 세션 복원, 페이지 초기화 버그 2개 수정 |
| AI 모델 | Gemini 전용 PROVIDER_CONFIG, thinkingConfig 위치 버그, deepcopy 버그 수정 |
| 배포 | AWS Lightsail × 2 (teamA/teamB), GitHub Actions 자동 배포 |
| 0119 브랜치 | 삭제 완료 (로컬/원격) |

---

## 남은 작업

### Queue 재설계

**현재 상태 (잘못됨)**
- Queue가 `▶️ 블록 실행` 시점에 걸려 있음
- 블록 실행은 Gemini API I/O 대기 → CPU/RAM 거의 없음 → **Queue 의미 없음**
- 정작 무거운 PDF 파싱(pymupdf4llm, CPU 스파이크)에는 Queue 없음
- 추가 버그: `if uploaded_file is not None:` 블록에 파싱 가드 없음 → **매 rerun마다 파싱 반복**

**목표 상태**
- Queue를 파일 업로드 → 파싱 시점으로 이동
- 블록 실행에서 Queue 완전 제거
- 같은 파일 재파싱 방지 가드 추가

---

#### [x] 1단계: 재파싱 가드 추가 ✅

파일 `pages/3_Document_Analysis.py` 수정

```python
# 현재 (문제)
if uploaded_file is not None:
    analyze_file_from_bytes(...)   # 매 rerun마다 실행됨

# 수정 후
if uploaded_file is not None:
    file_hash = f"{uploaded_file.name}_{len(file_bytes)}"
    if st.session_state.get('_parsed_file_hash') != file_hash:
        # 새 파일일 때만 파싱
        analyze_file_from_bytes(...)
        st.session_state['_parsed_file_hash'] = file_hash
    # 같은 파일이면 스킵 (session_state에 이미 텍스트 있음)
```

> 이 가드 없이 파싱 Queue를 추가하면 대기 중 3초 rerun마다 파싱이 반복 시도됨

---

#### [x] 2단계: 파싱 Queue 추가 ✅

파일 `pages/3_Document_Analysis.py` 수정 — 1단계 가드 블록 바깥에서 Queue 처리

```python
if uploaded_file is not None:
    file_hash = f"{uploaded_file.name}_{len(file_bytes)}"
    
    if st.session_state.get('_parsed_file_hash') != file_hash:
        # 대기열 진입
        enter_queue(user_id, project_id)
        
        if not can_process(user_id):
            info = get_queue_info(user_id)
            st.warning(f"⏳ {info['position']}번째 대기 중... 잠시 후 자동 시작")
            time.sleep(3)
            st.rerun()
        else:
            start_processing(user_id)
            try:
                analyze_file_from_bytes(...)
                st.session_state['_parsed_file_hash'] = file_hash
            finally:
                exit_queue(user_id)
```

---

#### [x] 3단계: 블록 실행 Queue 제거 ✅

파일 `pages/3_Document_Analysis.py` 수정

- `queue_waiting = st.session_state.get('_queue_waiting', False)` 제거
- `if run_clicked or queue_waiting:` → `if run_clicked:` 로 복원
- `enter_queue / can_process / start_processing / exit_queue` 호출 전부 제거
- `_queue_waiting` 세션 플래그 관련 코드 전부 제거
- `stop_clicked` 핸들러에서 `exit_queue()` + `_queue_waiting` 초기화 제거

파일 `database/queue_manager.py`
- `MAX_CONCURRENT` 값 재확인 (파싱 기준: 2~3 적정)

---

### 기타

- [ ] `AWS 배포.md` "향후 구현 예정" 항목 → Queue 구현 완료로 업데이트

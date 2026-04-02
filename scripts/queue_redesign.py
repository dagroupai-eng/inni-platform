"""
Queue 재설계 스크립트 — 세 가지 변경을 순서대로 적용:
  A. 블록 실행 Queue 래퍼 제거 + else: 블록 de-indent (가장 뒤 → 먼저 처리)
  B. stop_clicked Queue 코드 제거
  C. 업로드 섹션 재파싱 가드 + 파싱 Queue 추가
"""
import os

TARGET = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                      'pages', '3_Document_Analysis.py')

with open(TARGET, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"원본 총 라인: {len(lines)}")


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def find_line(lines, text, start=0):
    """strip 기준으로 정확히 일치하는 첫 줄의 0-indexed 번호 반환."""
    for i in range(start, len(lines)):
        if lines[i].rstrip() == text:
            return i
    return None

def find_line_contains(lines, text, start=0):
    for i in range(start, len(lines)):
        if text in lines[i]:
            return i
    return None


# ═════════════════════════════════════════════════════════════════════════════
# A. 블록 실행 Queue 래퍼 제거
#    queue_waiting 선언(3259) ~ else: 줄(3293) 을 "        if run_clicked:\n" 한 줄로 교체
#    이후 else: 블록 내용은 4칸 de-indent
#    finally 안의 exit_queue 6줄도 제거
# ═════════════════════════════════════════════════════════════════════════════

q_decl = find_line_contains(lines, "_queue_waiting', False)")
assert q_decl is not None, "queue_waiting 선언 못 찾음"
q_else = find_line(lines, '            else:', q_decl)
assert q_else is not None, "else: 못 찾음"
block_end = find_line(lines, '    if not active_plan:', q_else)
assert block_end is not None, "active_plan 못 찾음"

print(f"A: queue_waiting={q_decl+1}, else:={q_else+1}, block_end={block_end+1}")

# else: 블록 내용 (q_else+1 ~ block_end-1) 을 4칸 de-indent
else_content = lines[q_else + 1 : block_end]
deindented = []
for ln in else_content:
    if ln.startswith('                '):   # 16칸 → 12칸
        deindented.append(ln[4:])
    elif ln.strip() == '':
        deindented.append(ln)
    else:
        deindented.append(ln)  # 예외 처리: 그대로 유지

# exit_queue 6줄 제거 (de-indent 후 기준으로 찾기)
EXIT_MARKER = "# 대기열에서 제거 (완료/중단/오류 모두)"
exit_start = None
for i, ln in enumerate(deindented):
    if EXIT_MARKER in ln:
        exit_start = i
        break

if exit_start is not None:
    # 해당 줄 + 이후 5줄 (총 6줄) 제거
    deindented = deindented[:exit_start] + deindented[exit_start + 6:]
    print(f"  A-2: exit_queue 6줄 제거 완료")

# 조립: queue_wrapper 전체를 "if run_clicked:" + de-indent 내용으로 교체
new_run_block = ['        if run_clicked:\n'] + deindented
lines = lines[:q_decl] + new_run_block + lines[block_end:]
print(f"  A 완료. 현재 총 라인: {len(lines)}")


# ═════════════════════════════════════════════════════════════════════════════
# B. stop_clicked Queue 코드 제거
#    - st.session_state['_queue_waiting'] = False  (1줄)
#    - # 대기열에서 제거 ~ print(f"[Queue] stop exit_queue") (8줄)
# ═════════════════════════════════════════════════════════════════════════════

stop_q_wait = find_line_contains(lines, "_queue_waiting'] = False")
assert stop_q_wait is not None, "_queue_waiting=False 못 찾음"
stop_exit_comment = find_line_contains(lines, "# 대기열에서 제거", stop_q_wait)
assert stop_exit_comment is not None, "stop exit_queue 주석 못 찾음"

# _queue_waiting=False 줄 제거 (1줄)
# + "# 대기열에서 제거" 시작 8줄 제거
lines = lines[:stop_q_wait] + lines[stop_q_wait + 1:]  # _queue_waiting 제거
# 인덱스 재계산 후
stop_exit_comment = find_line_contains(lines, "# 대기열에서 제거")
lines = lines[:stop_exit_comment] + lines[stop_exit_comment + 8:]
print(f"  B 완료. 현재 총 라인: {len(lines)}")


# ═════════════════════════════════════════════════════════════════════════════
# C. 업로드 섹션 재파싱 가드 + 파싱 Queue 추가
#    "    if uploaded_file is not None:" ~ "    # 입력값 최신화" (exclusive) 를 교체
# ═════════════════════════════════════════════════════════════════════════════

up_start = find_line(lines, '    if uploaded_file is not None:')
assert up_start is not None, "uploaded_file 블록 못 찾음"
up_end = find_line(lines, '    # 입력값 최신화', up_start)
assert up_end is not None, "입력값 최신화 못 찾음"

print(f"C: upload_start={up_start+1}, upload_end={up_end+1}")

NEW_UPLOAD = (
    "    if uploaded_file is not None:\n"
    "        st.success(f\"파일 업로드 완료: {uploaded_file.name}\")\n"
    "\n"
    "        file_extension = uploaded_file.name.split('.')[-1].lower()\n"
    "        file_bytes = uploaded_file.getvalue()\n"
    "        file_hash = f\"{uploaded_file.name}_{len(file_bytes)}\"\n"
    "        already_parsed = st.session_state.get('_parsed_file_hash') == file_hash\n"
    "\n"
    "        if not already_parsed:\n"
    "            # ── 파싱 Queue 진입 ──────────────────────────────────────────────\n"
    "            _pq_uid = (st.session_state.get('pms_current_user') or {}).get('id')\n"
    "            _pq_pid = st.session_state.get('current_project_id')\n"
    "            _pq_can_go = True\n"
    "            try:\n"
    "                from database.queue_manager import (\n"
    "                    enter_queue, can_process, get_queue_info,\n"
    "                    start_processing, exit_queue as _pq_exit,\n"
    "                )\n"
    "                if _pq_uid:\n"
    "                    enter_queue(_pq_uid, _pq_pid)\n"
    "                    _pq_can_go = can_process(_pq_uid)\n"
    "            except Exception as _pqe:\n"
    "                print(f'[Queue] 파싱 Queue 오류: {_pqe}')\n"
    "\n"
    "            if not _pq_can_go:\n"
    "                try:\n"
    "                    _pq_info = get_queue_info(_pq_uid) if _pq_uid else {}\n"
    "                except Exception:\n"
    "                    _pq_info = {}\n"
    "                st.warning(\n"
    "                    f\"⏳ 파일 파싱 대기 중 ({_pq_info.get('position', '?')}번째). \"\n"
    "                    \"잠시 후 자동 시작됩니다...\"\n"
    "                )\n"
    "                time.sleep(3)\n"
    "                st.rerun()\n"
    "            else:\n"
    "                if _pq_uid:\n"
    "                    try:\n"
    "                        start_processing(_pq_uid)\n"
    "                    except Exception as _pqe:\n"
    "                        print(f'[Queue] start_processing 오류: {_pqe}')\n"
    "\n"
    "                _parse_ok = False\n"
    "                try:\n"
    "                    # 이미지 파일: Gemini Vision으로 내용 읽기 → 텍스트 컨텍스트로 저장\n"
    "                    if file_extension in [\"png\", \"jpg\", \"jpeg\", \"webp\"]:\n"
    "                        try:\n"
    "                            from google import genai\n"
    "                            from google.genai import types\n"
    "                            from pdf_analyzer import _get_gemini_api_key\n"
    "\n"
    "                            api_key = _get_gemini_api_key()\n"
    "                            if not api_key:\n"
    "                                st.error(\"이미지 읽기를 위해 `GEMINI_API_KEY`가 필요합니다. (설정/환경변수 또는 UI 키)\")\n"
    "                            else:\n"
    "                                client = genai.Client(api_key=api_key)\n"
    "                                prompt = (\n"
    "                                    \"이 이미지를 '도시/건축 프로젝트 분析' 관점에서 읽고, \"\n"
    "                                    \"보이는 핵심 요소(텍스트/도면/표/지도/다이어그램)를 구조화해 한국어로 요약해줘.\\n\\n\"\n"
    "                                    \"출력 형식:\\n\"\n"
    "                                    \"1) 한줄 요약\\n\"\n"
    "                                    \"2) 관찰된 요소(불릿)\\n\"\n"
    "                                    \"3) 이미지 내 텍스트(OCR 느낌으로 최대한)\\n\"\n"
    "                                    \"4) 분析에 유용한 키워드(10개)\\n\"\n"
    "                                )\n"
    "                                with st.spinner(\"🖼️ 이미지 내용 읽는 중(Gemini Vision)...\"):\n"
    "                                    resp = client.models.generate_content(\n"
    "                                        model=\"gemini-2.5-flash\",\n"
    "                                        contents=[\n"
    "                                            types.Content(\n"
    "                                                role=\"user\",\n"
    "                                                parts=[\n"
    "                                                    types.Part.from_text(prompt),\n"
    "                                                    types.Part.from_bytes(data=file_bytes, mime_type=uploaded_file.type or \"image/png\"),\n"
    "                                                ],\n"
    "                                            )\n"
    "                                        ],\n"
    "                                    )\n"
    "                                text = (getattr(resp, \"text\", None) or \"\").strip()\n"
    "                                if text:\n"
    "                                    st.session_state[\"pdf_text\"] = text\n"
    "                                    st.session_state[\"pdf_uploaded\"] = True\n"
    "                                    st.session_state[\"file_type\"] = \"image\"\n"
    "                                    st.session_state[\"file_analysis\"] = {\n"
    "                                        \"success\": True,\n"
    "                                        \"file_type\": \"image\",\n"
    "                                        \"text\": text,\n"
    "                                        \"char_count\": len(text),\n"
    "                                        \"word_count\": len(text.split()),\n"
    "                                        \"preview\": text[:500] + \"...\" if len(text) > 500 else text,\n"
    "                                    }\n"
    "                                    st.session_state[\"uploaded_file\"] = uploaded_file\n"
    "                                    _parse_ok = True\n"
    "                                else:\n"
    "                                    st.error(\"이미지 읽기 결과가 비어 있습니다.\")\n"
    "                        except Exception as _img_err:\n"
    "                            st.error(f\"이미지 읽기 실패: {_img_err}\")\n"
    "\n"
    "                    else:\n"
    "                        # 메모리에서 직접 파일 분析 (임시 파일 생성 없음)\n"
    "                        file_analyzer = UniversalFileAnalyzer()\n"
    "                        with st.spinner(f\"{file_extension.upper()} 파일 분析 중...\"):\n"
    "                            analysis_result = file_analyzer.analyze_file_from_bytes(\n"
    "                                file_bytes,\n"
    "                                file_extension,\n"
    "                                uploaded_file.name\n"
    "                            )\n"
    "\n"
    "                        if analysis_result['success']:\n"
    "                            st.success(f\"{file_extension.upper()} 파일 분析 완료!\")\n"
    "                            file_size_mb = len(file_bytes) / (1024 * 1024)\n"
    "                            st.info(f\"파일 정보: {file_size_mb:.2f}MB, {analysis_result['word_count']}단어, {analysis_result['char_count']}문자\")\n"
    "                            if analysis_result.get('truncated'):\n"
    "                                orig = analysis_result.get('original_char_count', 0)\n"
    "                                st.warning(f\"파일이 너무 커서 앞부분 {analysis_result['char_count']:,}자만 분析에 사용됩니다. (원본: {orig:,}자)\")\n"
    "                            if analysis_result['file_type'] == 'excel':\n"
    "                                st.info(f\"Excel 시트: {', '.join(analysis_result['sheet_names'])} ({analysis_result['sheet_count']}개 시트)\")\n"
    "                            elif analysis_result['file_type'] == 'csv':\n"
    "                                enc = analysis_result.get('encoding', 'utf-8')\n"
    "                                st.info(f\"CSV 데이터: {analysis_result['shape'][0]}행 × {analysis_result['shape'][1]}열 | 인코딩: {enc}\")\n"
    "                            elif analysis_result['file_type'] == 'pdf':\n"
    "                                method = analysis_result.get('method', 'pymupdf')\n"
    "                                quality = analysis_result.get('quality_score', '-')\n"
    "                                st.info(f\"PDF 추출 방법: {method} | 품질 점수: {quality}/100\")\n"
    "                                if analysis_result.get('is_scanned'):\n"
    "                                    st.warning(\"스캔된 PDF로 감지되었습니다. Gemini API 키가 있으면 자동으로 OCR 처리됩니다.\")\n"
    "                            elif analysis_result['file_type'] == 'docx':\n"
    "                                h = analysis_result.get('heading_count', 0)\n"
    "                                t = analysis_result.get('table_count', 0)\n"
    "                                st.info(f\"Word 문서: 헤딩 {h}개, 표 {t}개\")\n"
    "                            elif analysis_result['file_type'] == 'json':\n"
    "                                if analysis_result.get('summarized'):\n"
    "                                    st.info(\"JSON 파일이 크기가 커서 구조 요약 모드로 변환되었습니다. (키 목록 + 샘플 항목)\")\n"
    "\n"
    "                            # 세션에 저장\n"
    "                            st.session_state['pdf_text'] = analysis_result['text']\n"
    "                            st.session_state['pdf_uploaded'] = True\n"
    "                            st.session_state['file_type'] = analysis_result['file_type']\n"
    "                            st.session_state['file_analysis'] = analysis_result\n"
    "                            st.session_state['uploaded_file'] = uploaded_file\n"
    "\n"
    "                            # ── Supabase Storage 업로드 ────────────────────────────────────────\n"
    "                            try:\n"
    "                                from auth.file_storage import upload_project_file, save_file_meta\n"
    "                                from auth.project_manager import get_or_create_current_project\n"
    "                                _uid_fs = st.session_state.pms_current_user.get('id') if st.session_state.get('pms_current_user') else None\n"
    "                                if _uid_fs:\n"
    "                                    _pid_fs = get_or_create_current_project(_uid_fs)\n"
    "                                    _storage_path = upload_project_file(\n"
    "                                        user_id=_uid_fs,\n"
    "                                        project_id=_pid_fs,\n"
    "                                        filename=uploaded_file.name,\n"
    "                                        file_bytes=file_bytes,\n"
    "                                    )\n"
    "                                    if _storage_path:\n"
    "                                        st.session_state['file_storage_path'] = _storage_path\n"
    "                                        save_file_meta(\n"
    "                                            project_id=_pid_fs,\n"
    "                                            user_id=_uid_fs,\n"
    "                                            filename=uploaded_file.name,\n"
    "                                            file_type=analysis_result['file_type'],\n"
    "                                            storage_path=_storage_path,\n"
    "                                            char_count=analysis_result.get('char_count', 0),\n"
    "                                            file_size_bytes=len(file_bytes),\n"
    "                                            file_meta={\n"
    "                                                'quality_score': analysis_result.get('quality_score'),\n"
    "                                                'method': analysis_result.get('method'),\n"
    "                                            },\n"
    "                                        )\n"
    "                                        st.caption(\"☁️ 파일이 저장소에 업로드되었습니다.\")\n"
    "                            except Exception as _fs_err:\n"
    "                                print(f\"[FileStorage] 업로드 오류: {_fs_err}\")\n"
    "\n"
    "                            # 텍스트 미리보기\n"
    "                            with st.expander(f\"{file_extension.upper()} 내용 미리보기\"):\n"
    "                                st.text(analysis_result['preview'])\n"
    "\n"
    "                            _parse_ok = True\n"
    "                        else:\n"
    "                            st.error(f\"{file_extension.upper()} 파일 분析에 실패했습니다: {analysis_result.get('error', '알 수 없는 오류')}\")\n"
    "\n"
    "                finally:\n"
    "                    try:\n"
    "                        if _pq_uid:\n"
    "                            _pq_exit(_pq_uid)\n"
    "                    except Exception as _pqe:\n"
    "                        print(f'[Queue] exit_queue 오류: {_pqe}')\n"
    "\n"
    "                if _parse_ok:\n"
    "                    st.session_state['_parsed_file_hash'] = file_hash\n"
    "\n"
    "        else:\n"
    "            # 이미 파싱된 파일 → 재파싱 스킵, UI만 표시\n"
    "            _cached = st.session_state.get('file_analysis', {})\n"
    "            if _cached.get('success'):\n"
    "                if _cached.get('file_type') == 'image':\n"
    "                    st.success(\"이미지 읽기 완료! 추출된 텍스트를 분析에 사용합니다.\")\n"
    "                    with st.expander(\"이미지 읽기 결과(미리보기)\"):\n"
    "                        st.text(_cached.get('preview', ''))\n"
    "                else:\n"
    "                    file_size_mb = len(file_bytes) / (1024 * 1024)\n"
    "                    st.info(f\"파일 정보: {file_size_mb:.2f}MB, {_cached.get('word_count', 0)}단어, {_cached.get('char_count', 0)}문자\")\n"
    "                    with st.expander(f\"{file_extension.upper()} 내용 미리보기\"):\n"
    "                        st.text(_cached.get('preview', ''))\n"
    "\n"
    "        # 파일 분析 완료 확인 버튼\n"
    "        if st.session_state.get('pdf_uploaded') and st.session_state.get('_parsed_file_hash') == file_hash:\n"
    "            if st.button(\"✅ 파일 분析 완료 확인\", use_container_width=True, type=\"primary\", key=\"confirm_file_upload\"):\n"
    "                try:\n"
    "                    from auth.project_manager import save_project_from_session\n"
    "                    from auth.session_init import save_analysis_progress\n"
    "                    original_name = (st.session_state.get(\"project_name\") or \"\").strip()\n"
    "                    final_name = save_project_from_session()\n"
    "                    save_analysis_progress(force=True)\n"
    "                    st.session_state['_notify'] = {\n"
    "                        'type': 'save',\n"
    "                        'project_name': final_name,\n"
    "                        'renamed': final_name != original_name,\n"
    "                    }\n"
    "                    st.rerun()\n"
    "                except Exception as e:\n"
    "                    st.warning(f\"저장 중 오류: {e}\")\n"
    "                    st.success(\"파일 분析이 확인되었습니다. '분析 블록 선택' 탭으로 이동하세요.\")\n"
    "\n"
)

lines = lines[:up_start] + [NEW_UPLOAD] + lines[up_end:]
print(f"  C 완료. 현재 총 라인: {len(lines)}")


# ─────────────────────────────────────────────────────────────────────────────
# 저장 & 검증
# ─────────────────────────────────────────────────────────────────────────────
with open(TARGET, 'w', encoding='utf-8') as f:
    f.writelines(lines)

# 문법 검사
import ast
with open(TARGET, 'r', encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
    print("\n✅ Syntax OK")
except SyntaxError as e:
    print(f"\n❌ SyntaxError: {e}")

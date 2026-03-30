# inni-platform 프로젝트 업무 매뉴얼

## 프로젝트 개요
도시 개발 프로젝트 분석을 위한 Streamlit 멀티페이지 앱.
- DB: Supabase PostgreSQL
- 배포 환경: Streamlit Cloud (또는 로컬)
- 현재 작업 브랜치: `0119` → 메인 브랜치 `master`로 머지

## 페이지 구성
| 파일 | 역할 |
|------|------|
| `pages/1_Block_Generator.py` | 블록 생성 |
| `pages/2_Mapping.py` | 필지 매핑 / 지도 시각화 |
| `pages/3_Document_Analysis.py` | 문서 분석 (PDF, DOCX, Excel 등) |
| `pages/4_AI_Image_Prompt_Generator.py` | AI 이미지 프롬프트 생성 |
| `pages/5_Video_Storyboard_Generator.py` | 영상 스토리보드 생성 |
| `pages/6_Admin.py` | 관리자 페이지 |

## 핵심 모듈
- `file_analyzer.py` — `UniversalFileAnalyzer` 클래스, PDF/DOCX/Excel 등 파싱
- `pdf_analyzer.py` — Gemini 기반 스캔 PDF 추출
- `database/` — Supabase 연결 및 쿼리 관련
- `auth/` — 인증 관련

## 작업 규칙

### 코드 수정 전
- 반드시 계획을 먼저 설명하고 확인을 받은 후 실행한다.
- 수정 대상 파일을 먼저 읽고 이해한 뒤 제안한다.

### 위험 작업 (반드시 확인 후 진행)
- 파일 삭제
- DB 직접 수정 (Supabase 테이블 데이터 변경)
- `requirements.txt` 패키지 제거
- `master` 브랜치 push

### DB 관련
- Supabase PostgreSQL 사용 중 (SQLite 아님)
- UPDATE/DELETE 쿼리는 WHERE 조건 누락 여부를 반드시 확인한다.
- SQL 파싱 레이어를 우회하는 직접 실행 방식 사용 중 (주의)

### 코드 품질
- 기존 코드 스타일(한글 주석, Streamlit 패턴)을 따른다.
- 요청하지 않은 리팩터링이나 기능 추가는 하지 않는다.
- 과도한 추상화 금지 — 필요한 최소한의 변경만 한다.

## 의존성
주요 라이브러리:
- `streamlit` — UI 프레임워크
- `supabase` — DB 클라이언트
- `pymupdf4llm` — PDF Markdown 추출 (v0.3.4)
- `python-docx` — DOCX 파싱
- `google-generativeai` — Gemini API (스캔 PDF 폴백)
- `folium` / `streamlit-folium` — 지도 시각화

새 패키지 추가 시 `requirements.txt`에 반드시 기록한다.

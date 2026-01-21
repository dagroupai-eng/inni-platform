# PMS 기술 구조도 (실제 구현 기반)
## Urban ArchInsight - 현재 시스템의 실제 기능 구조

> **설계 원칙**: 페이지 단위로 진입하여 해당 페이지 안에서 핵심 기능들을 즉시 수행
>
> 이 문서는 실제 구현된 코드를 기반으로 작성되었습니다.

---

## 📱 페이지 1: 메인 페이지 (app.py)

**목적**: AI 모델 선택 및 API 키 관리, 시스템 소개

### 핵심 기능

1. **AI 모델 선택**
   - Gemini 2.5 Pro (gemini_25flash)
   - OpenAI GPT-4 (gpt4)
   - Vertex AI
   - 기타 PROVIDER_CONFIG에 정의된 모델
   - 모델별 display_name 및 파라미터 표시

2. **API 키 관리**
   - API 키 입력 (비밀번호 형식)
   - ✅ 확인 버튼 (세션에 저장)
   - 🗑️ 삭제 버튼 (세션에서 제거)
   - 키 길이 표시
   - 키 출처 표시 (웹 입력 / Streamlit Secrets / 환경변수)

3. **시스템 상태 확인**
   - 필수 모듈 자동 확인 (dspy_analyzer 등)
   - API 키 설정 상태 표시 (설정됨/미설정)
   - 경고 메시지 및 해결 방법 안내
   - 설치 가이드 (install.bat 실행)

4. **주요 기능 소개**
   - PDF 분석 소개
   - 지도 분석 소개
   - Midjourney 프롬프트 생성기 소개

5. **사용법 안내**
   - PDF 분석 사용법
   - 통계 확인 방법
   - 지도 사용법
   - 사이트 데이터 수집 방법

6. **에러 처리**
   - ImportError 처리 (모듈 부재 시)
   - UnicodeDecodeError 처리 (.env 인코딩 문제)
   - 안전한 환경변수 로드

---

## 📄 페이지 2: 문서 분석 (1_📄_Document_Analysis.py)

**목적**: 프로젝트 문서 업로드 및 AI 기반 다단계 분석

### 핵심 기능

1. **프로젝트 기본 정보 입력**
   - 프로젝트명 입력
   - 위치 입력
   - 위도/경도 입력 (Google Maps 좌표)
   - 프로젝트 목표 입력 (텍스트 영역)
   - 추가 정보 입력 (텍스트 영역)
   - 세션 상태에 자동 저장

2. **파일 업로드 및 분석**
   - 다중 포맷 지원: PDF, DOCX, XLSX, CSV, TXT, JSON
   - UniversalFileAnalyzer로 텍스트 자동 추출
   - 파일 정보 표시 (단어 수, 문자 수)
   - 파일 미리보기 (최대 500자)
   - 참고 URL 추가 (URL 입력, 추가 버튼, 삭제 버튼)
   - 업로드된 파일을 session_state에 저장

3. **분석 블록 선택 및 관리**
   - blocks.json에서 블록 로드
   - 카테고리별 블록 표시
   - 체크박스로 블록 선택
   - 블록 순서 조정 (위로/아래로 이동 버튼)
   - 블록 상세 정보 표시 (role, instructions, steps)
   - 선택한 블록 카운트 표시

4. **Chain-of-Thought 분석 실행**
   - 단계별 분석 세션 준비
   - 선택한 블록 순서대로 실행
   - 실시간 진행 상황 표시
   - 각 단계별 요약 표시
   - CoT 히스토리 저장
   - 분석 결과를 session_state에 저장

5. **Phase 1-1 요구사항 관리**
   - 고정 프로그램 사양 입력 (삼척 스포츠아카데미)
   - 프로그램 소개 입력
   - 교육 시설 입력
   - 스포츠 지원시설 입력
   - 컨벤션 시설 입력
   - 재활/웰니스 시설 입력
   - 기타 시설 입력
   - Markdown 형식 자동 생성

6. **Felo 후보지 데이터 처리**
   - Shapefile ZIP 업로드
   - geo_data_loader로 Shapefile 자동 로드
   - Felo AI 결과 텍스트 붙여넣기
   - 텍스트 파싱 (후보지 정보 추출)
   - 구조화된 데이터 변환
   - 후보지 목록 표시
   - 지도 시각화 (Folium)

7. **블록별 개별 실행**
   - **블록 1 실행**: 요구사항 파싱 (AI)
   - **블록 2 실행**: 필요 데이터 목록 생성 (AI)
   - **블록 5 실행**: 시설 목록 AI 제안
   - **블록 6 실행**: 면적 기준 조사
   - **블록 7 실행**: 면적 산정
   - 각 블록마다 AI 분석 결과 즉시 표시
   - 결과를 JSON으로 저장 가능

8. **분석 결과 조회 및 관리**
   - 탭 형식으로 결과 표시
   - 각 블록별 결과 탭
   - 전체 결과 종합 탭
   - 인용문 및 출처 표시
   - 피드백 입력 및 재분석
   - 분석 히스토리 표시

9. **결과 다운로드**
   - Word 문서 생성 (python-docx 사용)
   - 프로젝트 정보 포함
   - 각 블록 결과 섹션별로 구성
   - 다운로드 버튼
   - 파일명: "분석결과_{프로젝트명}_{날짜}.docx"

10. **세션 관리**
    - 분석 세션 초기화 버튼
    - 모든 입력값 리셋
    - 업로드 파일 초기화
    - CoT 히스토리 초기화
    - [DEBUG] 세션 상태 확인 (Expander)

11. **고급 설정**
    - LLM 파라미터 설정 (Temperature, Max Tokens)
    - 전처리 옵션 설정
    - 참고 문서 활용 설정
    - RAG 활용 설정

---

## 🏙️ 페이지 3: 사이트 데이터 수집 (2_🏙️_Site Data Collection.py)

**목적**: 좌표 기반 도시 데이터 자동 수집 및 시각화

### 핵심 기능

1. **좌표 입력**
   - 위도 입력 (number_input, 기본값: 37.5665)
   - 경도 입력 (number_input, 기본값: 126.9780)
   - 수집 반경 설정 (100m ~ 5000m)
   - 사이트 ID 입력 (기본값: S001)

2. **수집 설정**
   - OSM POI 수집 체크박스 (기본값: True)
   - V-World 용도지역 수집 (향후 확장)
   - KOSIS 통계 수집 (향후 확장)
   - 공공시설 데이터 수집 (향후 확장)

3. **데이터 수집 실행**
   - "데이터 수집 시작" 버튼 (primary)
   - UrbanDataCollector 초기화
   - 진행 상황 표시 (progress_bar)
   - 상태 텍스트 표시 (수집 중: 사이트명)
   - 수집 완료 메시지
   - 에러 처리 및 메시지 표시

4. **수집 결과 요약**
   - 사이트별 데이터 개수 테이블
   - 위치 정보 표시 (위도, 경도)
   - OSM POI 개수
   - V-World 용도지역 개수
   - KOSIS 통계 개수
   - 공공시설 개수
   - DataFrame으로 표시

5. **지역별 상세 데이터 조회**
   - 지역 선택 드롭다운 ("전체 보기" 또는 사이트별)
   - OSM POI 데이터 테이블 표시
     - 이름, POI 타입, 거리 (m), 위도, 경도
     - 최대 500행까지 표시 (자동 샘플링)
   - POI 타입별 통계
     - 막대 차트 (Plotly)
     - 타입별 개수 집계
   - V-World 용도지역 데이터 (향후)
   - KOSIS 통계 데이터 (향후)

6. **POI 지도 시각화**
   - "POI 지도 표시" 체크박스
   - Folium 지도 생성
   - 사이트 중심 마커 (빨간색, "사이트 중심")
   - 수집 반경 원 표시 (파란색)
   - POI 타입별 색상 구분 마커
   - POI 팝업 (이름, 타입, 거리)
   - 지도 성능을 위한 자동 샘플링 (최대 100개)
   - 레이어 컨트롤

7. **한국어 이름 매핑**
   - V-World 레이어 한국어 이름 자동 변환
   - POI 타입 한국어 표시
   - 용도지역 한국어 표시

8. **데이터 저장**
   - 수집 데이터를 session_state에 저장
   - 다운로드 기능 (향후 확장: Excel, GeoJSON)

9. **성능 최적화**
   - 대용량 데이터 자동 샘플링
   - MAX_DISPLAY_ROWS = 500
   - MAX_MAP_POIS = 100
   - 샘플링 시 경고 메시지 표시

---

## 🗺️ 페이지 4: 지도 분석 (3_🗺️_Mapping.py)

**목적**: 연속 지적도 조회 및 공간 정보 시각화

### 탭 구조 (st.tabs 사용)

#### 탭 1: 연속 지적도

##### 핵심 기능

1. **지도 위치 설정**
   - 위도 입력 (number_input, 기본값: 37.5665)
   - 경도 입력 (number_input, 기본값: 126.9780)
   - "위치로 이동" 버튼
   - 줌 레벨 선택 (5 ~ 19, 기본값: 17)
   - 주요 도시 선택 (서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종)
   - "선택 도시로 이동" 버튼

2. **연속 지적도 레이어 선택**
   - 본번 레이어 체크박스
   - 부번 레이어 체크박스
   - 선택한 레이어만 지도에 표시

3. **지역지구 레이어 선택**
   - 용도지역 카테고리:
     - 도시지역 (빨간색)
     - 관리지역 (청록색)
     - 농림지역 (초록색)
     - 자연환경보전지역 (파란색)
   - 용도지구 카테고리:
     - 경관지구
     - 개발제한구역
   - 도시계획시설 카테고리:
     - 도시계획(도로)
     - 도시계획(교통시설)
     - 도시계획(공간시설)
     - 도시계획(공공문화체육시설)
     - 도시계획(방재시설)
     - 도시계획(환경기초시설)
     - 지구단위계획
   - 각 레이어별 색상 구분 표시

4. **연속 지적도 지도 표시**
   - Folium 지도 생성
   - VWorld WMS 타일 레이어
     - 기본지도 (base 레이어)
     - 위성지도 (satellite 레이어)
   - 연속 지적도 WMS 레이어
     - 본번 레이어 (투명도 지원)
     - 부번 레이어 (투명도 지원)
   - 지역지구 WMS 레이어
     - 선택한 레이어만 표시
     - 색상 구분 및 투명도
   - 현재 위치 마커 (빨간색)
   - 레이어 컨트롤 (LayersControl)
   - 줌 컨트롤
   - streamlit-folium으로 표시

5. **지적 정보 조회**
   - "이 위치의 지적 정보 조회" 버튼
   - VWorld WMS GetFeatureInfo API 호출
   - 조회 결과 표시:
     - PNU (필지고유번호)
     - 지번 (본번, 부번)
     - 지목
     - 공시지가
     - 면적
     - 소유 구분
     - 주소 정보 (시도, 시군구, 읍면동, 리)
   - 한글 필드명으로 변환하여 표시
   - 에러 처리 (조회 실패 시 메시지)

6. **WFS 고급 조회**
   - "WFS로 영역 내 데이터 조회" Expander
   - 조회 영역 설정 (BBOX):
     - 최소 위도, 최대 위도
     - 최소 경도, 최대 경도
   - 조회 레이어 선택 (본번/부번)
   - 최대 피처 수 설정 (10 ~ 1000, 기본값: 100)
   - "WFS 데이터 조회" 버튼
   - VWorld WFS GetFeature API 호출
   - 조회 결과 테이블 표시
   - GeoJSON 다운로드 (향후 확장)

7. **VWorld API 정보**
   - "VWorld API 정보" Expander
   - WMS GetMap 설명
   - WMS GetFeatureInfo 설명
   - WFS GetFeature 설명
   - 사용 예시 코드 표시
   - API 키 표시 (일부 마스킹)

#### 탭 2: Shapefile 업로드 (개발 중)

##### 핵심 기능

1. **Shapefile 업로드**
   - ZIP 파일 업로드 (file_uploader)
   - geo_data_loader로 Shapefile 자동 로드
   - CRS 자동 변환 (EPSG:4326)
   - 업로드 성공 메시지

2. **레이어 정보 표시**
   - Feature 개수
   - Bounds (경계)
   - Geometry 타입
   - CRS 정보

3. **통합 지도 표시**
   - Folium 지도 생성
   - 업로드된 GeoDataFrame 시각화
   - 레이어 스타일 커스터마이징
   - 속성 정보 팝업
   - 레이어 컨트롤

4. **원본 데이터 미리보기**
   - GeoDataFrame을 DataFrame으로 변환
   - 최대 10행 표시
   - 전체 컬럼 표시

#### 탭 3: 입지 후보지 시각화 (개발 중)

##### 핵심 기능

1. **Document Analysis 결과 로드**
   - session_state에서 uploaded_gdf 로드
   - 후보지 정보 표시

2. **후보지 지도 표시**
   - Folium 지도 생성
   - 후보지 마커 표시
   - 후보지 정보 팝업
   - 후보지 비교 표시

---

## 🔧 페이지 5: 블록 생성기 (5_🔧_Block_Generator.py)

**목적**: 커스텀 분석 블록 생성 및 DSPy Signature 자동 생성

### 핵심 기능

1. **기본 정보 입력**
   - 블록 이름 (text_input, 필수)
   - 블록 설명 (text_area, 필수)
   - 카테고리 선택 (selectbox: 기존 카테고리 또는 "새 카테고리 추가")
   - 새 카테고리 입력 (text_input, 조건부 표시)
   - 커스텀 ID 입력 (text_input, 고급 옵션)

2. **RISEN 프롬프트 구조 입력**
   - **역할 (Role)** (text_area, 필수)
     - AI의 전문가 역할 정의
     - 예시: "당신은 도시 계획 전문가입니다..."
   - **지시 (Instructions)** (text_area, 필수)
     - 구체적인 작업 지시
     - 예시: "다음 문서에서..."
   - **단계 (Steps)** (선택 가능, 1~10단계)
     - 단계 개수 선택 (number_input, 기본값: 3)
     - 각 단계별 내용 입력 (text_input)
     - 단계별 라벨 (단계 1, 단계 2, ...)
   - **최종 목표 (End Goal)** (text_area, 필수)
     - 달성하고자 하는 결과
     - 예시: "구조화된 분석 결과를 제공하여..."

3. **구체화/제약 조건 (Narrowing)**
   - **출력 형식** (text_area)
   - **필수 항목/섹션** (text_area)
   - **제약 조건** (text_area)
   - **품질 기준** (text_area)
   - **평가 기준/분석 영역** (text_area, 선택사항)
   - **점수 체계/계산 방법** (text_area, 선택사항)

4. **블록 생성**
   - "블록 생성" 버튼 (primary)
   - 입력값 검증 (필수 필드 체크)
   - 블록 ID 자동 생성 (또는 커스텀 ID 사용)
   - 중복 ID 체크
   - blocks.json 파일 업데이트
   - DSPy Signature 코드 자동 생성
   - dspy_analyzer.py 파일 업데이트
   - 성공/실패 메시지 표시

5. **생성된 블록 정보 표시**
   - 생성된 블록 정보 (JSON 형식)
   - 생성된 DSPy Signature 코드 (Python 코드)
   - Code 블록으로 표시

6. **블록 생성기 리셋**
   - "🔄 블록 생성기 리셋" 버튼
   - 모든 입력값 초기화
   - session_state 리셋

7. **기존 블록 관리 (사이드바)**
   - 기존 블록 목록 표시
   - 블록 ID, 이름, 카테고리 표시
   - 블록 설명 표시
   - 개별 블록 삭제 버튼
   - 삭제 확인 메시지
   - blocks.json 및 dspy_analyzer.py 업데이트

8. **작성 가이드라인 (우측 패널)**
   - 블록 이름 작성 요령
   - 역할 작성 가이드
   - 지시 작성 가이드
   - 단계 작성 가이드
   - 최종 목표 작성 가이드
   - 구체화 작성 가이드
   - 실제 사용 예시 3가지

9. **고급 기능**
   - DSPy Signature 자동 생성
   - 블록 ID 자동 생성 (snake_case)
   - 중복 ID 자동 체크
   - 파일 자동 업데이트 (blocks.json, dspy_analyzer.py)
   - 에러 처리 및 상세 메시지

---

## 🎨 페이지 6: Midjourney 프롬프트 생성기 (6_🎨_Midjourney_Prompt_Generator.py)

**목적**: 건축 프로젝트 분석 결과를 기반으로 Midjourney 이미지 생성 프롬프트 자동 생성

### 핵심 기능

1. **데이터 소스 선택 (사이드바)**
   - 라디오 버튼 선택:
     - "PDF 파일 업로드"
     - "Document Analysis 결과 활용"
     - "직접 입력"

2. **PDF 파일 업로드 (데이터 소스 1)**
   - PDF 파일 업로드 (file_uploader)
   - UniversalFileAnalyzer로 PDF 텍스트 추출
   - 분석 진행 상황 표시 (spinner)
   - 분석 완료 메시지 (파일명, 페이지 수, 문자 수)
   - session_state에 저장
   - PDF 내용 미리보기 (최대 1000자)

3. **Document Analysis 결과 활용 (데이터 소스 2)**
   - session_state에서 데이터 로드:
     - project_info (프로젝트명, 유형, 위치, 규모)
     - cot_history (Chain-of-Thought 히스토리)
     - pdf_text (PDF 내용)
     - analysis_results (분석 결과)
   - 프로젝트 정보 표시
   - 분석 단계 요약 표시 (최근 3개 단계)
   - CoT 히스토리 상세 표시 (Expander)
   - 데이터 로드 성공/실패 메시지

4. **직접 입력 (데이터 소스 3)**
   - 프로젝트명 (text_input)
   - 건물 유형 (selectbox: 사무용, 주거용, 상업용, 문화시설, 교육시설, 의료시설, 기타)
   - 대지 위치 (text_input)
   - 건축주 (text_input)
   - 대지 면적 (text_input)
   - session_state에 저장 (manual_input)

5. **이미지 설정 (사이드바)**
   - **이미지 유형** (selectbox):
     - 외관 렌더링
     - 내부 공간
     - 마스터플랜
     - 상세도
     - 컨셉 이미지
     - 조감도
   - **스타일 선호도** (multiselect):
     - 현대적, 미니멀, 자연친화적
     - 고급스러운, 기능적, 예술적, 상업적
   - **추가 설명** (text_area)
     - 특별히 강조하고 싶은 요소나 요구사항

6. **데이터 미리보기 (메인 컨텐츠)**
   - 현재 선택된 데이터 소스에 따라 표시:
     - PDF: PDF 내용 미리보기 (Expander)
     - Document Analysis: CoT 히스토리 표시 (Expander)
     - 직접 입력: 입력한 프로젝트 정보 표시
   - 데이터 로드 상태 메시지

7. **프롬프트 생성**
   - "Midjourney 프롬프트 생성" 버튼 (primary)
   - 입력 데이터 검증
   - AI 프롬프트 생성 (generate_midjourney_prompt 함수):
     - 프로젝트 정보 + 분석 결과 + 이미지 설정 통합
     - EnhancedArchAnalyzer 사용
     - 건축 이미지 생성 전문가 관점 적용
     - 이미지 유형별 키워드 자동 적용
     - 스타일별 키워드 자동 적용
     - 기술적 키워드 자동 포함
   - 로딩 표시 (spinner)

8. **생성 결과 표시**
   - **한글 설명**:
     - 건축적 특징, 분위기, 핵심 요소
     - Markdown 형식으로 표시
   - **English Midjourney Prompt**:
     - 구체적이고 실행 가능한 영어 프롬프트
     - Code 블록으로 표시 (복사 용이)
   - **프롬프트 복사** 버튼
     - 클립보드 복사 기능
   - **전체 분석 결과** (Expander)
     - 상세한 분석 과정 표시
   - **생성 모델 정보** (caption)
     - 사용된 AI 모델 표시

9. **프롬프트 구조**
   - 이미지 종류 + 건축 스타일 + 공간 유형
   - + 재료/텍스처 + 조명/분위기
   - + 환경/맥락 + 기술적 키워드 + 이미지 비율

10. **사용 팁 (하단)**
    - PDF 파일 업로드 설명
    - Document Analysis 결과 활용 설명
    - 직접 입력 설명
    - 이미지 설정 설명

11. **내장된 프롬프트 가이드라인**
    - **이미지 유형별 키워드**:
      - 외관 렌더링: building facade, exterior view, architectural elevation
      - 내부 공간: interior space, indoor lighting, furniture arrangement
      - 마스터플랜: master plan, site layout, landscape design
      - 상세도: architectural detail, construction detail
      - 컨셉 이미지: concept visualization, mood board
      - 조감도: aerial view, bird's eye view
    - **스타일별 키워드**:
      - 현대적: modern, contemporary, clean lines, minimalist
      - 미니멀: minimal, simple, uncluttered
      - 자연친화적: sustainable, green building, organic
      - 고급스러운: luxury, premium, sophisticated
      - 기능적: functional, practical, efficient
      - 예술적: artistic, creative, expressive
      - 상업적: commercial, business-oriented
    - **기술적 키워드**:
      - architectural photography, professional rendering
      - hyperrealistic, 8k, high quality
      - wide angle, natural lighting, golden hour

12. **중요 지시사항**
    - 분석 결과 반영 (건축적 특징을 프롬프트에 반영)
    - 구체성 (추상적이 아닌 구체적인 프롬프트)
    - 건축적 정확성 (실제 건축물의 구조와 형태)
    - 시각적 임팩트 (조형적 아름다움과 상징성)
    - 환경적 맥락 (주변 환경과의 조화)

---

## 🔗 페이지 간 데이터 연동

### Session State 공유 데이터

```python
# 프로젝트 기본 정보
st.session_state.project_name
st.session_state.location
st.session_state.latitude
st.session_state.longitude
st.session_state.project_goals
st.session_state.additional_info

# 파일 및 텍스트
st.session_state.uploaded_file
st.session_state.pdf_text
st.session_state.pdf_uploaded

# AI 분석 관련
st.session_state.llm_provider
st.session_state.llm_temperature
st.session_state.llm_max_tokens
st.session_state.selected_blocks
st.session_state.analysis_results

# Chain of Thought
st.session_state.cot_session
st.session_state.cot_results
st.session_state.cot_history
st.session_state.cot_analyzer
st.session_state.cot_citations

# 공간 데이터
st.session_state.geo_layers
st.session_state.uploaded_gdf
st.session_state.uploaded_layer_info

# 참고 문서
st.session_state.reference_documents
st.session_state.reference_combined_text

# Site Data Collection
st.session_state.collected_data
st.session_state.collection_status

# API 키
st.session_state.user_api_key_{api_key_env}
```

### 페이지 간 연동 흐름

```
app.py (API 키 설정)
    ↓
1_Document_Analysis.py
    → 문서 업로드 및 분석
    → CoT 히스토리 저장
    → session_state에 저장
    ↓
    ├→ 3_Mapping.py (입지 후보지 시각화 탭)
    │   → uploaded_gdf 로드
    │   → Felo 데이터 지도 표시
    │
    └→ 6_Midjourney_Prompt_Generator.py
        → Document Analysis 결과 로드
        → 프롬프트 생성

2_Site Data Collection.py
    → 좌표 기반 데이터 수집
    → collected_data 저장
    ↓
    └→ 3_Mapping.py
        → 수집된 데이터 지도 표시 (향후)

3_Mapping.py
    → Shapefile 업로드
    → uploaded_gdf 저장
    ↓
    └→ 1_Document_Analysis.py
        → Shapefile 로드 및 분석

5_Block_Generator.py
    → 새 블록 생성
    → blocks.json 업데이트
    ↓
    └→ 1_Document_Analysis.py
        → 새 블록 사용 가능
```

---

## 📦 핵심 모듈 및 의존성

### 핵심 분석 엔진
- **dspy_analyzer.py** (4,345줄)
  - EnhancedArchAnalyzer 클래스
  - PROVIDER_CONFIG (AI 모델 설정)
  - DSPy Signatures (20+ 개)
  - Chain-of-Thought 분석 엔진

### 파일 분석
- **file_analyzer.py** (488줄)
  - UniversalFileAnalyzer 클래스
  - PDF/DOCX/XLSX/CSV/JSON 지원

### 도시 데이터 수집
- **urban_data_collector.py** (462줄)
  - UrbanDataCollector 클래스
  - OSM POI 수집
  - V-World API 연동
  - KOSIS 통계 수집

### 지리 정보 처리
- **geo_data_loader.py**
  - GeoDataLoader 클래스
  - Shapefile 로드 및 변환
  - Folium 지도 생성

### 프롬프트 처리
- **prompt_processor.py**
  - load_blocks() 함수
  - blocks.json 로드 및 파싱

### 주요 라이브러리
- **Streamlit** 1.39.0+ (웹 UI)
- **DSPy-ai** 3.0.3+ (AI 파이프라인)
- **Folium** + streamlit-folium 0.25.1+ (지도)
- **GeoPandas** 0.14.0 (공간 데이터)
- **PyMuPDF** 1.24.14 (PDF 처리)
- **python-docx** 1.1.2 (Word 문서 생성)
- **requests** (API 호출)

---

## 🎯 실제 구현 기반 요약

이 기술 구조도는 **실제 코드를 분석하여 작성**되었으며, 다음과 같은 특징이 있습니다:

1. **6개의 실제 페이지**: 모든 페이지가 실제로 구현되어 있음
2. **페이지별 즉시 실행**: 각 페이지에서 모든 핵심 기능을 바로 수행 가능
3. **Session State 기반**: 페이지 간 데이터 공유
4. **AI 기반 분석**: DSPy 프레임워크 활용
5. **지도 시각화**: Folium 기반 인터랙티브 지도
6. **파일 다운로드**: Word, Excel, GeoJSON 등 다양한 형식 지원
7. **API 통합**: VWorld, OSM, KOSIS 등 외부 API 활용

### 현재 개발 상태
- ✅ 완전 구현: app.py, Document Analysis, Site Data Collection, Block Generator, Midjourney Prompt Generator
- ✅ 부분 구현: Mapping (연속 지적도 탭)
- 🚧 개발 중: Mapping (Shapefile 업로드 탭, 입지 후보지 시각화 탭)

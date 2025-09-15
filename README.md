# 🏗️ Simple Arch Insight - 건축 프로젝트 AI 분석 도구

> **학생들을 위한 건축 프로젝트 PDF 문서 분석 및 시각화 도구**

## 📋 목차

- [🎯 프로젝트 소개](#-프로젝트-소개)
- [✨ 주요 기능](#-주요-기능)
- [🛠️ 설치 가이드](#️-설치-가이드)
- [🚀 사용 방법](#-사용-방법)
- [🔧 문제 해결](#-문제-해결)
- [📞 지원](#-지원)

---

## 🎯 프로젝트 소개

**Simple Arch Insight**는 건축 프로젝트 PDF 문서를 AI로 분석하고, 통계 및 지도 시각화를 제공하는 교육용 도구입니다.

### 🎨 주요 특징
- **AI 기반 분석**: Claude Sonnet 4 모델을 사용한 고품질 분석
- **다양한 분석 블록**: 기본 정보, 요구사항, 설계 제안 등
- **시각화**: 통계 차트 및 지도 기반 데이터 분석
- **사용자 친화적**: 직관적인 웹 인터페이스

---

## ✨ 주요 기능

### 📄 PDF 분석
- 건축 프로젝트 PDF 문서 업로드
- AI 기반 자동 분석 (Chain of Thought)
- 구조화된 분석 결과 제공
- Word 문서로 결과 내보내기

### 📊 통계 대시보드
- 프로젝트 유형별 통계
- 월별 분석 추이
- 분석 블록 사용 현황
- 지역별 프로젝트 분포

### 🗺️ 지도 분석
- 프로젝트 위치 정보 표시
- 서울 지역 상세 지도
- 전국 프로젝트 분포
- 프로젝트 유형별 지도 시각화

---

## 🛠️ 설치 가이드

> **⚠️ 중요**: 이 가이드는 Windows 10/11 기준으로 작성되었습니다. macOS/Linux 사용자는 일부 명령어가 다를 수 있습니다.

### 1단계: Miniconda 설치

#### 1-1. Miniconda 다운로드
1. **웹브라우저**에서 https://docs.conda.io/en/latest/miniconda.html 접속
2. **Windows** 섹션에서 **Python 3.9** 버전 다운로드
3. 다운로드된 `.exe` 파일 실행

#### 1-2. Miniconda 설치
1. **"Next"** 클릭하여 설치 시작
2. **라이선스 동의** 체크 후 **"Next"**
3. **설치 경로** 확인 (기본값 권장: `C:\Users\[사용자명]\miniconda3`)
4. **"Add Miniconda3 to my PATH environment variable"** 체크
5. **"Install"** 클릭하여 설치 완료

#### 1-3. 설치 확인
1. **시작 메뉴**에서 **"Anaconda Prompt (miniconda3)"** 실행
2. 다음 명령어 입력하여 설치 확인:
```bash
conda --version
```
3. 버전 정보가 표시되면 설치 성공!

### 2단계: Git 설치

#### 2-1. Git 다운로드
1. **웹브라우저**에서 https://git-scm.com/download/win 접속
2. **"Download for Windows"** 클릭
3. 다운로드된 `.exe` 파일 실행

#### 2-2. Git 설치
1. **"Next"** 클릭하여 설치 시작
2. **설치 경로** 확인 (기본값 권장)
3. **"Git from the command line and also from 3rd-party software"** 선택
4. **"Use the OpenSSL library"** 선택
5. **"Checkout Windows-style, commit Unix-style line endings"** 선택
6. **"Use Windows' default console window"** 선택
7. **"Install"** 클릭하여 설치 완료

#### 2-3. 설치 확인
1. **Anaconda Prompt**에서 다음 명령어 입력:
```bash
git --version
```
2. 버전 정보가 표시되면 설치 성공!

### 3단계: 프로젝트 다운로드

#### 3-1. 프로젝트 클론
**Anaconda Prompt**에서 다음 명령어들을 순서대로 입력:

```bash
# 1. 원하는 폴더로 이동 (예: 바탕화면)
cd Desktop

# 2. 프로젝트 다운로드
git clone https://github.com/dagroupai-eng/inni-platform.git

# 3. 프로젝트 폴더로 이동
cd inni-platform
```

#### 3-2. 다운로드 확인
```bash
# 현재 폴더의 파일 목록 확인
dir
```
다음과 같은 파일들이 보이면 성공:
- `app.py`
- `requirements.txt`
- `README.md`
- `pages/` 폴더
- 기타 파일들

### 4단계: Python 환경 설정

#### 4-1. Conda 환경 생성
```bash
# Python 3.9 환경 생성
conda create -n inni-platform python=3.9 -y
```

#### 4-2. 환경 활성화
```bash
# 환경 활성화
conda activate inni-platform
```
성공하면 프롬프트 앞에 `(inni-platform)`이 표시됩니다.

#### 4-3. 환경 확인
```bash
# Python 버전 확인
python --version
```
`Python 3.9.x`가 표시되면 성공!

### 5단계: 필요한 패키지 설치

#### 5-1. 패키지 설치
```bash
# 모든 필요한 패키지 설치
pip install -r requirements.txt
```

#### 5-2. 설치 확인
```bash
# Streamlit 설치 확인
streamlit --version
```

### 6단계: API 키 설정

#### 6-1. Anthropic API 키 발급
1. **웹브라우저**에서 https://console.anthropic.com/ 접속
2. **계정 생성** 또는 **로그인**
3. **API Keys** 섹션으로 이동
4. **"Create Key"** 클릭
5. **키 이름** 입력 (예: "Simple Arch Insight")
6. **생성된 API 키** 복사 (sk-ant-로 시작하는 긴 문자열)

#### 6-2. API 키 설정
**Anaconda Prompt**에서 다음 명령어 입력:

```bash
# .env 파일 생성 (Windows PowerShell 방식)
@"
ANTHROPIC_API_KEY=여기에_실제_API_키_붙여넣기
"@ | Out-File -FilePath ".env" -Encoding UTF8
```

**예시:**
```bash
@"
ANTHROPIC_API_KEY=sk-ant-api03-abc123def456...
"@ | Out-File -FilePath ".env" -Encoding UTF8
```

#### 6-3. 설정 확인
```bash
# .env 파일 내용 확인
type .env
```
API 키가 올바르게 저장되었는지 확인하세요.

---

## 🚀 사용 방법

### 1단계: 앱 실행

**Anaconda Prompt**에서 다음 명령어 입력:

```bash
# 환경 활성화 (필요한 경우)
conda activate inni-platform

# 프로젝트 폴더로 이동 (필요한 경우)
cd inni-platform

# Streamlit 앱 실행
streamlit run app.py
```

### 2단계: 브라우저에서 접속

1. **웹브라우저** 실행
2. 주소창에 **`http://localhost:8501`** 입력
3. **Enter** 키 누르기

### 3단계: 기능 사용

#### 📄 PDF 분석
1. 왼쪽 사이드바에서 **"📄 PDF Analysis"** 클릭
2. **"프로젝트명"** 입력
3. **"PDF 파일 업로드"** 버튼으로 파일 선택
4. **분석 블록** 선택 (기본 정보 추출, 요구사항 분석 등)
5. **"분석 시작"** 버튼 클릭
6. 분석 결과 확인 및 Word 문서 다운로드

#### 📊 통계 대시보드
1. 왼쪽 사이드바에서 **"📊 Statistics"** 클릭
2. 다양한 통계 차트 확인:
   - 프로젝트 유형별 분포
   - 월별 분석 통계
   - 분석 블록 사용 현황
   - 지역별 프로젝트 분포

#### 🗺️ 지도 분석
1. 왼쪽 사이드바에서 **"🗺️ Mapping"** 클릭
2. 지도 유형 선택:
   - 서울 상세 지도
   - 전국 프로젝트 분포
   - 프로젝트 유형별 분포
3. 지도에서 프로젝트 위치 및 정보 확인

---

## 🔧 문제 해결

### 자주 발생하는 문제들

#### 1. "conda: command not found" 오류
**해결방법:**
- Miniconda 설치 시 "Add to PATH" 옵션을 체크했는지 확인
- 컴퓨터 재시작 후 다시 시도
- 수동으로 PATH에 추가: `C:\Users\[사용자명]\miniconda3\Scripts`

#### 2. "git: command not found" 오류
**해결방법:**
- Git 설치 시 "Git from the command line" 옵션을 선택했는지 확인
- 컴퓨터 재시작 후 다시 시도

#### 3. "ANTHROPIC_API_KEY가 설정되지 않았습니다" 오류
**해결방법:**
```bash
# .env 파일 다시 생성
@"
ANTHROPIC_API_KEY=실제_API_키_여기에_입력
"@ | Out-File -FilePath ".env" -Encoding UTF8
```

#### 4. "ModuleNotFoundError" 오류
**해결방법:**
```bash
# 환경 활성화 확인
conda activate inni-platform

# 패키지 재설치
pip install -r requirements.txt --force-reinstall
```

#### 5. "Port 8501 is already in use" 오류
**해결방법:**
```bash
# 다른 포트로 실행
streamlit run app.py --server.port 8502
```

#### 6. PDF 업로드 오류
**해결방법:**
- PDF 파일 크기가 200MB 이하인지 확인
- PDF 파일이 손상되지 않았는지 확인
- 다른 PDF 파일로 시도

### 로그 확인 방법

**Anaconda Prompt**에서 오류 메시지를 자세히 확인하고, 필요시 다음 명령어로 로그 확인:

```bash
# Streamlit 로그 확인
streamlit run app.py --logger.level debug
```

---

## 📞 지원

### 도움이 필요한 경우

1. **GitHub Issues**: https://github.com/dagroupai-eng/inni-platform/issues
2. **이메일**: [지원 이메일 주소]
3. **문서**: 이 README 파일의 문제 해결 섹션 참조

### 버그 신고

버그를 발견한 경우 다음 정보와 함께 신고해주세요:
- 운영체제 (Windows 10/11, macOS, Linux)
- Python 버전
- 오류 메시지 전체 내용
- 재현 단계

### 기능 요청

새로운 기능이나 개선 사항이 있으면 GitHub Issues에 요청해주세요.

---

## 📄 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.

---

## 🙏 감사의 말

- **Anthropic**: Claude AI 모델 제공
- **Streamlit**: 웹 앱 프레임워크
- **Plotly**: 데이터 시각화
- **PyMuPDF**: PDF 처리

---

**🎉 설치가 완료되면 즐거운 건축 프로젝트 분석을 시작해보세요!**

> **마지막 체크리스트:**
> - [ ] Miniconda 설치 완료
> - [ ] Git 설치 완료
> - [ ] 프로젝트 다운로드 완료
> - [ ] Python 환경 생성 및 활성화 완료
> - [ ] 패키지 설치 완료
> - [ ] API 키 설정 완료
> - [ ] 앱 실행 성공
> - [ ] 브라우저에서 접속 성공
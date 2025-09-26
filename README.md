# 🧩 Block Based Analyzer Template - AI 기반 문서 분석 도구

> **블록 기반으로 구성된 AI 문서 분석 템플릿 도구**

## 📋 목차

- [🎯 프로젝트 소개](#-프로젝트-소개)
- [✨ 주요 기능](#-주요-기능)
- [🛠️ 설치 가이드](#️-설치-가이드)
- [🚀 사용 방법](#-사용-방법)
- [🔧 문제 해결](#-문제-해결)
- [📞 지원](#-지원)

---

## 🎯 프로젝트 소개

**Block Based Analyzer Template**은 블록 단위로 구성된 AI 분석 엔진으로, 다양한 문서를 체계적으로 분석하고 시각화하는 템플릿 도구입니다.

### 🎨 주요 특징

- **블록 기반 분석**: 재사용 가능한 분석 블록으로 체계적 분석
- **AI 기반 처리**: Claude Sonnet 4 모델을 사용한 고품질 분석
- **블록 생성기**: 사용자 정의 분석 블록 생성 및 관리
- **시각화**: 지도 기반 데이터 분석 및 시각화

---

## ✨ 주요 기능

### 📄 문서 분석

- **문서 업로드**: 다양한 PDF, Excel, CSV, 텍스트, JSON 등 문서 분석 지원
- **블록 기반 분석**: 선택한 분석 블록으로 체계적 분석
- **AI 기반 처리**: Claude Sonnet 4 모델을 사용한 Chain of Thought 분석
- **구조화된 결과**: 분석 블록별 맞춤 결과 제공

### 🗺️ 지도 분석

- 위치 정보 표시 및 시각화
- 지리적 데이터 분석

### 🔧 블록 생성기

- 새로운 분석 블록 생성
- 기존 블록 편집 및 관리
- 블록 템플릿 커스터마이징
- 블록 재사용성 향상

---

## 🛠️ 설치 가이드

> **⚠️ 중요**: 이 가이드는 Windows 10/11 기준으로 작성되었습니다. macOS/Linux 사용자는 일부 명령어가 다를 수 있습니다.

### 1단계: Visual Studio Code 확인 및 설치

#### 1-1. Visual Studio Code 확인

1. **시작 메뉴**에서 **"Visual Studio Code"** 검색
2. **Visual Studio Code**가 설치되어 있으면 **2단계**로 진행
3. 설치되어 있지 않으면 **1-2** 단계 진행

#### 1-2. Visual Studio Code 설치 (필요한 경우)

1. **웹브라우저**에서 [https://code.visualstudio.com/](https://code.visualstudio.com/) 접속
2. **"Download for Windows"** 클릭
3. 다운로드된 `.exe` 파일 실행
4. **"Next"** 클릭하여 설치 진행
5. **"Add to PATH"** 옵션 체크 후 설치 완료

### 2단계: Miniconda 설치

#### 2-1. Miniconda 다운로드

1. **웹브라우저**에서 [https://docs.conda.io/en/latest/miniconda.html](https://docs.conda.io/en/latest/miniconda.html) 접속
2. **Windows** 섹션에서 **최신 버전** 다운로드
3. 다운로드된 `.exe` 파일 실행

#### 2-2. Miniconda 설치

1. **"Next"** 클릭하여 설치 시작
2. **라이선스 동의** 체크 후 **"Next"**
3. **설치 경로** 확인 (기본값 권장: `C:\Users\[사용자명]\miniconda3` 또는 원하는 경로)
4. **"Add Miniconda3 to my PATH environment variable"** 체크
5. **"Create shortcuts"**, **"Path environment variable"**, **"Clear the package cache upon completion"** 체크
6. **"Install"** 클릭하여 설치 완료

#### 2-3. 설치 확인

1. **시작 메뉴**에서 **"Anaconda Prompt (miniconda3)"** 실행
2. 다음 명령어 입력하여 설치 확인:

```bash
conda --version
```

버전 정보가 표시되면 설치 성공!

### 3단계: 프로젝트 다운로드

#### 3-1. ZIP 파일 다운로드

1. **웹브라우저**에서 프로젝트 저장소 접속
2. **"Code"** 버튼 클릭
3. **"Download ZIP"** 선택
4. 다운로드된 ZIP 파일을 원하는 폴더에 저장

#### 3-2. ZIP 파일 압축 해제

1. 다운로드된 ZIP 파일을 **우클릭**
2. **"압축 풀기"** 또는 **"Extract Here"** 선택
3. 압축이 해제되면 폴더가 생성됩니다

#### 3-3. 폴더명 변경 및 이동

1. 압축 해제된 폴더명을 원하는 이름으로 변경
2. 원하는 위치로 폴더 이동

#### 3-4. Visual Studio Code에서 프로젝트 열기

1. **Visual Studio Code** 실행
2. **"File"** → **"Open Folder"** 클릭
3. 압축 해제한 프로젝트 폴더 선택
4. **"New Terminal"** 클릭하여 터미널 열기

#### 3-5. 다운로드 확인

```bash
# 현재 폴더의 파일 목록 확인
dir

# Conda 버전 확인
conda --version
```

다음과 같은 파일들이 보이면 성공:

- `app.py`
- `requirements.txt`
- `README.md`
- `pages/` 폴더
- 기타 파일들

### 4단계: Conda 환경 생성

#### 4-1. Conda 환경 생성

```bash
# Python 3.11 환경 생성 (환경명을 원하는 이름으로 변경 가능)
conda create -n test_analyzer python=3.11 -y
```

**환경명 설명:**

- `test_analyzer`: 생성할 환경명 (원하는 이름으로 변경 가능)
- `python=3.11`: Python 3.11 버전 사용
- `-y`: 자동으로 yes 응답

#### 4-2. Terms of Service 오류 해결

만약 다음과 같은 오류가 발생하면:

```text
CondaToSNonInteractiveError: Terms of Service have not been accepted for the following channels. Please accept or remove them before proceeding:
- https://repo.anaconda.com/pkgs/main
- https://repo.anaconda.com/pkgs/r
- https://repo.anaconda.com/pkgs/msys2
```

다음 명령어들을 **순서대로** 실행:

```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/msys2
```

그 후 다시 환경 생성:

```bash
conda create -n test_analyzer python=3.11 -y
```

#### 4-3. 환경 활성화

```bash
# 환경 활성화
conda activate test_analyzer

# 환경 비활성화 (필요한 경우)
conda deactivate
```

성공하면 프롬프트 앞에 `(test_analyzer)`이 표시됩니다.

#### 4-4. 환경 확인

```bash
# Python 버전 확인
python --version
```

`Python 3.11.x`가 표시되면 성공!

### 5단계: 필요한 패키지 설치

#### 5-1. 지오스택 패키지 설치 (conda-forge 사용)

```bash
# 바이너리/지오 스택 + madoka를 conda-forge로 설치
# (Windows에서 pip로 빌드 이슈를 피하기 위함)
conda install -c conda-forge madoka geopandas shapely pyproj -y
```

#### 5-2. pip 도구 최신화

```bash
# pip 도구 최신화
python -m pip install -U pip setuptools wheel
```

#### 5-3. 나머지 패키지 설치

```bash
# requirements.txt로 나머지 패키지 설치
pip install -r requirements.txt
```

#### 5-4. 설치 확인

```bash
# Streamlit 설치 확인
streamlit --version
```

### 6단계: API 키 설정

#### 6-1. API 키 발급

**Anthropic API 키 발급:**

1. **웹브라우저**에서 [https://console.anthropic.com/](https://console.anthropic.com/) 접속
2. **계정 생성** 또는 **로그인**
3. **API Keys** 섹션으로 이동
4. **"Create Key"** 클릭
5. **키 이름** 입력 (예: "Block Based Analyzer")
6. **생성된 API 키** 복사 (sk-ant-로 시작하는 긴 문자열)

#### 6-2. .streamlit/secrets.toml 파일 생성

1. 프로젝트 폴더에 `.streamlit` 폴더가 없으면 생성
2. `.streamlit` 폴더 안에 `secrets.toml` 파일 생성
3. 다음 내용 입력:

```toml
ANTHROPIC_API_KEY = "your_anthropic_api_key_here"
```

1. `your_anthropic_api_key_here` 부분을 실제 API 키로 교체

#### 6-3. .env 파일 생성

1. 프로젝트 루트 폴더에 `.env` 파일 생성
2. 다음 내용 입력:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

1. `your_anthropic_api_key_here` 부분을 실제 API 키로 교체
2. 파일 저장

### 7단계: 앱 실행

#### 7-1. 환경 활성화 확인

**Visual Studio Code**의 터미널에서:

```bash
# 환경 활성화 (필요한 경우)
conda activate test_analyzer
```

프롬프트 앞에 `(test_analyzer)`가 표시되어야 합니다.

#### 7-2. 앱 실행

```bash
# Streamlit 앱 실행
streamlit run app.py
```

#### 7-3. 브라우저에서 접속

1. 터미널에 표시되는 **URI** 확인 (예: `http://localhost:8501`)
2. **Ctrl + 클릭**하여 웹 브라우저에서 열기
3. 또는 브라우저 주소창에 URI 입력

> **⚠️ 보안 주의사항:**
>
> - `.env` 파일과 `secrets.toml` 파일은 절대 git에 커밋하지 마세요
> - API 키를 다른 사람과 공유하지 마세요
> - `.gitignore`에 `.env`와 `.streamlit/`이 포함되어 있는지 확인하세요

---

## 🚀 사용 방법

### 1단계: 앱 실행

**Anaconda Prompt**에서 다음 명령어 입력:

```bash
# 환경 활성화 (필요한 경우)
conda activate [환경명]

# 프로젝트 폴더로 이동 (필요한 경우)
cd [프로젝트 폴더 경로]

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

#### 🗺️ 지도 분석 기능

1. 왼쪽 사이드바에서 **"🗺️ Mapping"** 클릭
2. 지도 분석 기능:
   - 위치 정보 시각화
   - 지리적 데이터 분석
3. 지도에서 프로젝트 위치 및 정보 확인

#### 🔧 블록 생성기 사용법

1. 왼쪽 사이드바에서 **"🔧 Block Generator"** 클릭
2. 분석 블록 생성 및 관리:
   - 새로운 분석 블록 생성
   - 기존 블록 편집
   - 블록 템플릿 관리

---

## 🔧 문제 해결

### 자주 발생하는 문제들

#### 1. "conda: command not found" 오류

**해결방법:**

- Miniconda 설치 시 "Add to PATH" 옵션을 체크했는지 확인
- 컴퓨터 재시작 후 다시 시도
- 수동으로 PATH에 추가: `C:\Users\[사용자명]\miniconda3\Scripts`

#### 2. "ANTHROPIC_API_KEY가 설정되지 않았습니다" 오류

**해결방법:**

```bash
# .env 파일 다시 생성 (Windows PowerShell)
@"
ANTHROPIC_API_KEY=실제_API_키_여기에_입력
"@ | Out-File -FilePath ".env" -Encoding UTF8

# 또는 메모장으로 직접 생성
notepad .env
```

#### 3. "ModuleNotFoundError" 오류

**해결방법:**

```bash
# 환경 활성화 확인
conda activate [환경명]

# 패키지 재설치
pip install -r requirements.txt --force-reinstall
```

#### 4. "Port 8501 is already in use" 오류

**해결방법:**

```bash
# 다른 포트로 실행
streamlit run app.py --server.port 8502
```

#### 5. 파일 업로드 오류

**해결방법:**

- 파일 크기가 200MB 이하인지 확인
- 파일이 손상되지 않았는지 확인
- 지원하는 파일 형식인지 확인 (PDF, Excel, CSV, 텍스트, JSON)
- 다른 파일로 시도

### 로그 확인 방법

**Anaconda Prompt**에서 오류 메시지를 자세히 확인하고, 필요시 다음 명령어로 로그 확인:

```bash
# Streamlit 로그 확인
streamlit run app.py --logger.level debug
```

---

## 📞 지원

### 도움이 필요한 경우

1. **GitHub Issues**: [https://github.com/dagroupai-eng/snu_platform/issues](https://github.com/dagroupai-eng/snu_platform/issues)
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

**🎉 설치가 완료되면 블록 기반 문서 분석을 시작해보세요!**

> **마지막 체크리스트:**
>
> - [ ] Miniconda 설치 완료
> - [ ] 프로젝트 ZIP 다운로드 및 압축 해제 완료
> - [ ] Python 환경 생성 및 활성화 완료
> - [ ] 패키지 설치 완료
> - [ ] API 키 설정 완료
> - [ ] 앱 실행 성공
> - [ ] 브라우저에서 접속 성공

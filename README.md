# Simple Arch Insight

건축 프로젝트 분석을 위한 간단한 AI 도구입니다.

## 주요 기능
- PDF 문서 업로드 및 분석
- 프로젝트 기본 정보 입력
- **Chain of Thought** 기반 고급 AI 분석 (직접 Anthropic API 사용)
- Claude AI를 활용한 건축 분석
- 분석 결과 표시 및 Word 다운로드

## 🚀 설치 및 실행

### 📋 사전 요구사항

- **Python 3.8 이상** (권장: Python 3.9 또는 3.10)
- **Anaconda 또는 Miniconda** 설치 필요
- **Anthropic API Key** (Claude AI 사용을 위해 필요)

### 🔧 1단계: Conda 환경 생성 및 활성화

```bash
# 1. 저장소 클론
git clone https://github.com/dagroupai-eng/inni-platform.git
cd inni-platform

# 2. Conda 환경 생성 (Python 3.9 권장)
conda create -n inni-platform python=3.9 -y

# 3. 환경 활성화
conda activate inni-platform

# 4. 환경 활성화 확인 (선택사항)
conda info --envs
```

### 📦 2단계: 의존성 설치

```bash
# pip 업그레이드 (권장)
pip install --upgrade pip

# 의존성 설치
pip install -r requirements.txt
```

**⚠️ 주의사항:**
- `PyMuPDF` 설치 시 시스템에 따라 추가 패키지가 필요할 수 있습니다
- Windows 사용자는 Visual C++ Redistributable이 필요할 수 있습니다
- M1/M2 Mac 사용자는 `arch -x86_64` 접두사가 필요할 수 있습니다

### 🔑 3단계: API 키 설정

```bash
# .env 파일 생성
echo "ANTHROPIC_API_KEY=your_anthropic_api_key_here" > .env
```

**또는 직접 .env 파일 생성:**
```bash
# Windows
notepad .env

# macOS/Linux
nano .env
```

**.env 파일 내용:**
```
ANTHROPIC_API_KEY=your_actual_api_key_here
```

**🔐 API 키 획득 방법:**
1. [Anthropic Console](https://console.anthropic.com/) 방문
2. 계정 생성 또는 로그인
3. API Keys 섹션에서 새 키 생성
4. 생성된 키를 `.env` 파일에 복사

### 🎯 4단계: 애플리케이션 실행

```bash
# 환경이 활성화되어 있는지 확인
conda activate inni-platform

# Streamlit 앱 실행
streamlit run app.py
```

**✅ 성공 시:**
- 브라우저가 자동으로 열리고 `http://localhost:8501`에서 앱이 실행됩니다
- "Simple Arch Insight" 제목이 보이면 정상적으로 설치된 것입니다

### 🛠️ 문제 해결

#### Conda 환경 관련 문제
```bash
# 환경 목록 확인
conda env list

# 환경 삭제 후 재생성
conda env remove -n inni-platform
conda create -n inni-platform python=3.9 -y
```

#### 의존성 설치 문제
```bash
# pip 캐시 정리
pip cache purge

# 개별 패키지 설치 시도
pip install streamlit==1.28.1
pip install anthropic==0.7.8
pip install PyMuPDF==1.23.8
```

#### API 키 관련 문제
- `.env` 파일이 프로젝트 루트에 있는지 확인
- API 키에 따옴표나 공백이 없는지 확인
- Anthropic 계정에 충분한 크레딧이 있는지 확인

#### 포트 충돌 문제
```bash
# 다른 포트로 실행
streamlit run app.py --server.port 8502
```

### 🖥️ 시스템별 특별 주의사항

#### Windows 사용자
```bash
# PowerShell에서 실행 시
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Visual C++ Redistributable 설치 필요할 수 있음
# https://aka.ms/vs/17/release/vc_redist.x64.exe
```

#### macOS 사용자 (M1/M2 Mac)
```bash
# Rosetta 2 설치 후 x86_64 아키텍처로 실행
arch -x86_64 conda create -n inni-platform python=3.9 -y
arch -x86_64 conda activate inni-platform
```

#### Linux 사용자
```bash
# 시스템 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# 필요한 시스템 라이브러리 설치
sudo apt install -y build-essential libgl1-mesa-glx
```

### 🔍 설치 확인 방법

```bash
# Python 버전 확인
python --version

# Conda 환경 확인
conda info --envs

# 패키지 설치 확인
pip list | grep -E "(streamlit|anthropic|PyMuPDF|dspy)"

# API 키 설정 확인
cat .env
```

## 🔧 주요 개선사항 (v2.0)

- ✅ **코드 정리**: 중복된 분석기 제거, 에러 처리 강화
- ✅ **안정성 향상**: PDF 처리 및 프롬프트 처리 개선
- ✅ **의존성 관리**: 정확한 버전 명시로 호환성 보장
- ✅ **에러 처리**: 더 나은 예외 처리 및 사용자 피드백

## 🎓 교육용 기능

### 📚 예시 분석 블록 (3개) - **Chain of Thought 기반**
1. **📋 기본 정보 추출 (CoT)** - Chain of Thought로 PDF에서 프로젝트 기본 정보 추출
2. **🏗️ 건축 요구사항 분석 (CoT)** - 단계별 사고 과정으로 건축 관련 요구사항 정리  
3. **💡 설계 제안 (CoT)** - 논리적 추론으로 기본적인 설계 방향 제안

### 🧠 **Chain of Thought 특징**
- **단계별 사고 과정**: 각 분석이 명확한 단계를 거쳐 진행
- **논리적 추론**: AI가 어떻게 결론에 도달했는지 과정을 보여줌
- **직접 API 사용**: DSPy 없이 안정적인 Anthropic API 직접 사용
- **교육적 가치**: 학생들이 AI의 사고 과정을 학습할 수 있음

### 🛠️ 사용자 정의 블록 생성
- 학생들이 직접 분석 프롬프트를 작성할 수 있습니다
- `{pdf_text}` 변수를 사용하여 PDF 내용을 삽입할 수 있습니다
- 실시간으로 블록을 추가하고 테스트할 수 있습니다

## ⚡ 빠른 시작 가이드

### 🎯 처음 사용하는 경우 (5분 설정)

```bash
# 1. 저장소 클론
git clone https://github.com/dagroupai-eng/inni-platform.git
cd inni-platform

# 2. Conda 환경 생성 및 활성화
conda create -n inni-platform python=3.9 -y
conda activate inni-platform

# 3. 의존성 설치
pip install -r requirements.txt

# 4. API 키 설정 (Anthropic Console에서 발급)
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env

# 5. 앱 실행
streamlit run app.py
```

### 📝 체크리스트

- [ ] Python 3.8+ 설치됨
- [ ] Anaconda/Miniconda 설치됨
- [ ] Anthropic API 키 발급 완료
- [ ] `.env` 파일에 API 키 설정됨
- [ ] Conda 환경 활성화됨
- [ ] 모든 의존성 설치 완료
- [ ] Streamlit 앱이 정상 실행됨

## 🚀 Git 기반 사용법 (학생용)

### 1. 저장소 복제 및 설정
```bash
# 저장소 클론
git clone https://github.com/dagroupai-eng/inni-platform.git
cd inni-platform

# 의존성 설치
pip install -r requirements.txt

# API 키 설정
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
```

### 2. 개인 프로젝트로 포크
```bash
# GitHub에서 Fork 후 개인 저장소로 클론
git clone https://github.com/YOUR_USERNAME/inni-platform.git
cd inni-platform

# 원본 저장소와 연결 (선택사항)
git remote add upstream https://github.com/dagroupai-eng/inni-platform.git
```

### 3. 블록 수정 및 커스터마이징
```bash
# blocks.json 파일 수정
# - 예시 블록 3개를 원하는 대로 수정
# - 새로운 블록 추가
# - 프롬프트 개선

# 실행
streamlit run app.py
```

### 4. 변경사항 저장 및 공유
```bash
# 변경사항 커밋
git add .
git commit -m "블록 수정: 새로운 분석 블록 추가"

# 개인 저장소에 푸시
git push origin main

# 원본 저장소에 Pull Request (선택사항)
```

## 📚 블록 수정 가이드

### blocks.json 수정 방법
```json
{
  "blocks": [
    {
      "id": "your_block_id",
      "name": "🆕 새로운 분석 블록",
      "description": "블록 설명",
      "prompt": "분석 프롬프트를 여기에 작성하세요. {pdf_text}를 사용하면 PDF 내용이 삽입됩니다."
    }
  ]
}
```

### 프롬프트 작성 팁
- `{pdf_text}` 변수를 사용하여 PDF 내용 삽입
- 구체적이고 명확한 지시사항 작성
- 출력 형식을 명시 (예: "다음 형식으로 정리해주세요:")
- 한국어로 작성 권장

## 🔄 버전 관리 및 업데이트
```bash
# 원본 저장소의 최신 변경사항 가져오기
git fetch upstream
git merge upstream/main

# 충돌 해결 후
git push origin main
```

## 사용법
1. 프로젝트 기본 정보 입력
2. PDF 문서 업로드
3. 분석 블록 선택/생성
4. 분석 실행
5. 결과 다운로드

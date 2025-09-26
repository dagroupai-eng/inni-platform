# 🏗️ Simple Arch Insight - Colab 버전

> **Google Colab에서 바로 사용할 수 있는 건축 프로젝트 PDF 분석 도구**

## 🚀 빠른 시작

### 1단계: Colab에서 새 노트북 생성
1. [Google Colab](https://colab.research.google.com/) 접속
2. "새 노트북" 클릭
3. 아래 코드를 복사하여 붙여넣기

### 2단계: 코드 실행
```python
# 이 파일의 내용을 Colab 셀에 복사하여 실행
!git clone https://github.com/your-repo/snu_platform.git
%cd snu_platform/colab
!pip install -r requirements.txt
```

### 3단계: 앱 실행
```python
# 메인 앱 실행
from colab_app import run_colab_app
run_colab_app()
```

## ✨ 주요 기능

### 📄 PDF 분석
- **Gemini 1.5 Pro**: Google의 최신 AI 모델 사용
- **DSPy**: Chain of Thought 분석
- **멀티모달**: 텍스트 + 이미지 동시 분석
- **7개 분석 블록**: 기본 정보, 요구사항, 설계 제안 등

### 📊 통계 대시보드
- 프로젝트별 분석 통계
- 분석 블록 사용 현황
- 시각화 차트

### 🗺️ 지도 분석
- 프로젝트 위치 표시
- 지역별 분포 분석

## 🔧 API 키 설정

### Gemini API (권장 - 무료)
1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. Google 계정으로 로그인
3. "Create API Key" 클릭
4. 생성된 API 키 복사

### Anthropic API (선택사항)
1. [Anthropic Console](https://console.anthropic.com/) 접속
2. 계정 생성 또는 로그인
3. API Keys 섹션에서 키 생성

## 📋 분석 블록

1. **📋 기본 정보 추출**: 프로젝트명, 건축주, 위치, 규모
2. **🏗️ 건축 요구사항 분석**: 공간, 기능, 법적, 기술적 요구사항
3. **💡 설계 제안**: 설계 컨셉, 공간 계획, 기술적 제안
4. **🚶 접근성 평가**: 교통, 보행, 시설 접근성
5. **🏘️ 법규 검증**: 용도지역, 건축법규, 특별법
6. **📊 수용력 추정**: 물리적, 법적, 사회적 수용력
7. **💰 사업성 평가**: 시장성, 수익성, 위험성 분석

## 🎯 사용 방법

1. **프로젝트명 입력**
2. **분석 블록 선택** (다중 선택 가능)
3. **PDF 파일 업로드**
4. **분석 결과 확인**
5. **통계 및 지도 확인**

## ⚠️ 주의사항

- **파일 크기**: PDF 파일은 50MB 이하 권장
- **API 사용량**: Gemini는 월 1,500회 무료
- **세션 지속**: Colab 세션 종료 시 데이터 손실
- **인터넷 연결**: 안정적인 인터넷 연결 필요

## 🔗 관련 링크

- [Google Colab](https://colab.research.google.com/)
- [Google AI Studio](https://aistudio.google.com/)
- [Anthropic Console](https://console.anthropic.com/)

## 📞 지원

문제가 있으면 GitHub Issues에 문의해주세요.

---

**🎉 Colab에서 즐거운 건축 프로젝트 분석을 시작해보세요!**

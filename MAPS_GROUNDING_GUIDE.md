# Google Maps Grounding Python 적용 가이드

이 가이드는 Google Maps Grounding 기능을 프로젝트에 통합하는 방법을 설명합니다.

## 목차

1. [개요](#개요)
2. [환경 설정](#환경-설정)
3. [기본 사용법](#기본-사용법)
4. [고급 사용법](#고급-사용법)
5. [오류 처리 및 제한사항](#오류-처리-및-제한사항)
6. [프로젝트 통합](#프로젝트-통합)
7. [예제 코드](#예제-코드)

## 개요

Google Maps Grounding은 Gemini API와 Google Maps 데이터를 연결하여 위치 기반 쿼리에 대한 정확하고 최신의 응답을 제공합니다.

### 주요 기능

- **정확한 위치 기반 응답**: Google Maps의 광범위하고 최신 데이터 활용
- **향상된 개인화**: 사용자 제공 위치를 기반으로 맞춤형 추천
- **컨텍스트 정보 및 위젯**: 인터랙티브 Google Maps 위젯 렌더링 지원

### 지원 모델

- Gemini 2.5 Pro
- Gemini 2.5 Flash
- Gemini 2.5 Flash-Lite
- Gemini 2.0 Flash

**참고**: Gemini 3는 현재 Google Maps Grounding을 지원하지 않습니다.

## 환경 설정

### 1. 의존성 설치

프로젝트의 `requirements.txt`에 이미 `google-genai>=0.2.0`이 포함되어 있습니다. 
설치되지 않은 경우 다음 명령어로 설치하세요:

```bash
pip install google-genai>=0.2.0
```

### 2. API 키 설정

Google AI Studio에서 API 키를 발급받아 설정합니다.

#### 방법 1: 환경 변수 설정

```bash
# Windows (PowerShell)
$env:GEMINI_API_KEY="your_api_key_here"

# Windows (CMD)
set GEMINI_API_KEY=your_api_key_here

# Linux/Mac
export GEMINI_API_KEY="your_api_key_here"
```

#### 방법 2: .env 파일 사용

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가:

```
GEMINI_API_KEY=your_api_key_here
```

#### 방법 3: Streamlit Secrets (Streamlit 앱인 경우)

`.streamlit/secrets.toml` 파일에 추가:

```toml
GEMINI_API_KEY = "your_api_key_here"
```

## 기본 사용법

### 간단한 예제

```python
from maps_grounding_helper import generate_content_with_maps_grounding

# 위치 정보 없이 쿼리
result = generate_content_with_maps_grounding(
    prompt="타임스퀘어 근처 레스토랑 추천"
)

if result["success"]:
    print(result["text"])
    for source in result["sources"]:
        print(f"- {source['title']}: {source['uri']}")
else:
    print(f"오류: {result['error']}")
```

### 위치 정보 포함 쿼리

```python
from maps_grounding_helper import generate_content_with_maps_grounding

# 사용자 위치 정보 포함
result = generate_content_with_maps_grounding(
    prompt="15분 거리 내 최고의 이탈리안 레스토랑은?",
    latitude=34.050481,  # Los Angeles
    longitude=-118.248526
)

if result["success"]:
    print("생성된 응답:")
    print(result["text"])
    print("\n소스:")
    for source in result["sources"]:
        print(f"- [{source['title']}]({source['uri']})")
```

## 고급 사용법

### 위젯 토큰 사용

Google Maps 위젯을 표시하려면 `enable_widget=True`를 설정합니다:

```python
from maps_grounding_helper import generate_content_with_maps_grounding

result = generate_content_with_maps_grounding(
    prompt="샌프란시스코에서 하루 일정을 계획해주세요.",
    latitude=37.78193,
    longitude=-122.40476,
    model="gemini-2.5-flash",
    enable_widget=True
)

if result["success"] and result["widget_token"]:
    # HTML에서 위젯 렌더링
    widget_html = f'''
    <gmp-place-contextual context-token="{result['widget_token']}"></gmp-place-contextual>
    '''
    print(widget_html)
```

**참고**: 위젯을 실제로 렌더링하려면 Google Maps JavaScript API를 로드해야 합니다.
자세한 내용은 [Google Maps Places Widget 문서](https://developers.google.com/maps/documentation/javascript/reference/places-widget)를 참조하세요.

### 인라인 인용 표시

응답 텍스트에 소스 인용을 포함하려면:

```python
from maps_grounding_helper import (
    generate_content_with_maps_grounding,
    format_grounding_supports_for_display
)

result = generate_content_with_maps_grounding(
    prompt="서울 강남구 근처 카페 추천",
    latitude=37.4979,
    longitude=127.0276
)

if result["success"]:
    # 인용이 포함된 텍스트 생성
    text_with_citations = format_grounding_supports_for_display(
        text=result["text"],
        grounding_supports=result["grounding_supports"],
        sources=result["sources"]
    )
    print(text_with_citations)
```

### 소스 목록 포맷팅

```python
from maps_grounding_helper import (
    generate_content_with_maps_grounding,
    format_sources_for_display
)

result = generate_content_with_maps_grounding(
    prompt="타임스퀘어 근처 레스토랑"
)

if result["success"]:
    print(result["text"])
    print(format_sources_for_display(result["sources"]))
```

## 오류 처리 및 제한사항

### 오류 처리

함수는 항상 `success` 필드를 포함한 딕셔너리를 반환합니다:

```python
result = generate_content_with_maps_grounding(
    prompt="쿼리 내용"
)

if not result["success"]:
    error_message = result.get("error", "알 수 없는 오류")
    print(f"오류 발생: {error_message}")
    # 오류 처리 로직
else:
    # 성공 처리 로직
    print(result["text"])
```

### 주요 제한사항

1. **지역 제한**: 
   - 다음 지역에서는 사용할 수 없습니다:
     - 중국, 크림, 쿠바, 도네츠크 인민공화국, 이란, 루한스크 인민공화국, 북한, 시리아, 베트남

2. **모델 제한**:
   - Gemini 3는 지원하지 않습니다
   - 지원 모델: Gemini 2.5 Pro, Gemini 2.5 Flash, Gemini 2.5 Flash-Lite, Gemini 2.0 Flash

3. **멀티모달 제한**:
   - 현재 텍스트 입력/출력과 컨텍스트 맵 위젯만 지원합니다
   - 이미지나 비디오 입력은 지원하지 않습니다

4. **기본 상태**:
   - Google Maps Grounding은 기본적으로 비활성화되어 있습니다
   - 명시적으로 `tools=[GoogleMaps()]`를 설정해야 합니다

### 요금 및 할당량

- **요금**: $25 / 1K grounded prompts
- **무료 티어**: 하루 최대 500건 요청
- **할당량**: 기본적으로 Gemini 모델의 할당량과 일치합니다

**참고**: 요청은 Google Maps grounded 결과(최소 1개의 Google Maps 소스 포함)가 성공적으로 반환된 경우에만 할당량에 카운트됩니다.

## 프로젝트 통합

### 기존 코드와 통합

#### 1. urban_data_collector.py와 통합

위치 데이터 수집 후 Google Maps Grounding을 사용하여 추가 정보를 얻을 수 있습니다:

```python
from urban_data_collector import UrbanDataCollector
from maps_grounding_helper import generate_content_with_maps_grounding

collector = UrbanDataCollector()
site_data = collector.collect_site_data(
    lat=37.4979,
    lon=127.0276,
    radius_m=1000
)

# Google Maps Grounding으로 추가 정보 수집
maps_result = generate_content_with_maps_grounding(
    prompt=f"이 위치({site_data['site_info']['lat']}, {site_data['site_info']['lon']}) 주변의 주요 시설과 관광지를 추천해주세요.",
    latitude=site_data['site_info']['lat'],
    longitude=site_data['site_info']['lon']
)

if maps_result["success"]:
    # 결과를 site_data에 추가
    site_data["maps_recommendations"] = {
        "text": maps_result["text"],
        "sources": maps_result["sources"]
    }
```

#### 2. Streamlit 페이지에 통합

새로운 Streamlit 페이지를 생성하거나 기존 페이지에 추가:

```python
import streamlit as st
from maps_grounding_helper import (
    generate_content_with_maps_grounding,
    format_sources_for_display
)

st.title("Google Maps Grounding 테스트")

# 사용자 입력
prompt = st.text_input("쿼리 입력:", "타임스퀘어 근처 레스토랑 추천")
lat = st.number_input("위도 (선택사항):", value=None)
lon = st.number_input("경도 (선택사항):", value=None)

if st.button("검색"):
    with st.spinner("검색 중..."):
        result = generate_content_with_maps_grounding(
            prompt=prompt,
            latitude=lat if lat else None,
            longitude=lon if lon else None
        )
    
    if result["success"]:
        st.markdown("## 응답")
        st.markdown(result["text"])
        
        if result["sources"]:
            st.markdown(format_sources_for_display(result["sources"]))
    else:
        st.error(f"오류: {result['error']}")
```

#### 3. dspy_analyzer.py와 통합

DSPy 분석기에 Google Maps Grounding을 추가할 수 있습니다:

```python
from dspy_analyzer import EnhancedArchAnalyzer
from maps_grounding_helper import generate_content_with_maps_grounding

analyzer = EnhancedArchAnalyzer()

# 프로젝트 위치 정보가 있는 경우
project_info = {
    "project_name": "새 프로젝트",
    "location": "서울 강남구",
    "lat": 37.4979,
    "lon": 127.0276
}

# Google Maps Grounding으로 주변 환경 분석
if project_info.get("lat") and project_info.get("lon"):
    maps_result = generate_content_with_maps_grounding(
        prompt=f"{project_info['project_name']} 프로젝트 위치 주변의 도시 환경을 분석해주세요. 교통, 상업시설, 공공시설 등을 포함해주세요.",
        latitude=project_info["lat"],
        longitude=project_info["lon"]
    )
    
    if maps_result["success"]:
        # 분석 결과에 추가
        project_info["maps_analysis"] = maps_result["text"]
```

### 서비스 레이어 패턴

재사용 가능한 서비스 클래스를 만들 수 있습니다:

```python
from typing import Optional, Dict, Any
from maps_grounding_helper import generate_content_with_maps_grounding

class MapsGroundingService:
    """Google Maps Grounding 서비스 레이어"""
    
    def __init__(self, default_model: str = "gemini-2.5-flash"):
        self.default_model = default_model
    
    def get_local_recommendations(
        self,
        query: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        지역 추천을 가져옵니다.
        
        Args:
            query: 검색 쿼리
            lat: 위도
            lon: 경도
            category: 카테고리 (예: "restaurant", "cafe", "museum")
        
        Returns:
            결과 딕셔너리
        """
        prompt = query
        if category:
            prompt = f"{category} 카테고리의 {query}"
        
        return generate_content_with_maps_grounding(
            prompt=prompt,
            latitude=lat,
            longitude=lon,
            model=self.default_model
        )
    
    def plan_itinerary(
        self,
        location: str,
        lat: float,
        lon: float,
        interests: list,
        duration: str = "1일"
    ) -> Dict[str, Any]:
        """
        여행 일정을 계획합니다.
        
        Args:
            location: 위치 이름
            lat: 위도
            lon: 경도
            interests: 관심사 리스트
            duration: 기간
        
        Returns:
            결과 딕셔너리 (위젯 토큰 포함)
        """
        interests_str = ", ".join(interests)
        prompt = f"{location}에서 {duration} 일정을 계획해주세요. 관심사: {interests_str}"
        
        return generate_content_with_maps_grounding(
            prompt=prompt,
            latitude=lat,
            longitude=lon,
            model=self.default_model,
            enable_widget=True
        )

# 사용 예제
service = MapsGroundingService()

# 레스토랑 추천
result = service.get_local_recommendations(
    query="최고의 레스토랑",
    lat=37.4979,
    lon=127.0276,
    category="restaurant"
)

# 여행 일정 계획
itinerary = service.plan_itinerary(
    location="서울",
    lat=37.5665,
    lon=126.9780,
    interests=["박물관", "맛집", "공원"],
    duration="2일"
)
```

## 예제 코드

### 예제 1: 장소별 질문

```python
from maps_grounding_helper import generate_content_with_maps_grounding

result = generate_content_with_maps_grounding(
    prompt="1번가와 메인가 모퉁이 근처에 야외 좌석이 있는 카페가 있나요?",
    latitude=34.050481,  # Los Angeles
    longitude=-118.248526,
    model="gemini-2.5-flash"
)

if result["success"]:
    print("생성된 응답:")
    print(result["text"])
    print("\n소스:")
    for source in result["sources"]:
        print(f"- [{source['title']}]({source['uri']})")
```

### 예제 2: 위치 기반 개인화

```python
from maps_grounding_helper import (
    generate_content_with_maps_grounding,
    format_sources_for_display
)

result = generate_content_with_maps_grounding(
    prompt="여기 근처에서 놀이터 리뷰가 가장 좋은 가족 친화적 레스토랑은 어디인가요?",
    latitude=30.2672,  # Austin, TX
    longitude=-97.7431,
    model="gemini-2.5-flash"
)

if result["success"]:
    print("생성된 응답:")
    print(result["text"])
    print(format_sources_for_display(result["sources"]))
```

### 예제 3: 여행 일정 계획 (위젯 포함)

```python
from maps_grounding_helper import generate_content_with_maps_grounding

result = generate_content_with_maps_grounding(
    prompt="샌프란시스코에서 하루 일정을 계획해주세요. 골든게이트 브리지를 보고, 박물관을 방문하고, 좋은 저녁 식사를 하고 싶습니다.",
    latitude=37.78193,  # San Francisco
    longitude=-122.40476,
    model="gemini-2.5-flash",
    enable_widget=True
)

if result["success"]:
    print("생성된 응답:")
    print(result["text"])
    
    if result["sources"]:
        print("\n소스:")
        for source in result["sources"]:
            print(f"- [{source['title']}]({source['uri']})")
    
    if result["widget_token"]:
        print(f"\n위젯 토큰: {result['widget_token']}")
        print("\nHTML 위젯 코드:")
        print(f'<gmp-place-contextual context-token="{result["widget_token"]}"></gmp-place-contextual>')
```

## 추가 리소스

- [Google Maps Grounding 공식 문서](https://ai.google.dev/gemini-api/docs/maps-grounding)
- [Google Maps Places Widget 문서](https://developers.google.com/maps/documentation/javascript/reference/places-widget)
- [Gemini API 가격 정보](https://ai.google.dev/gemini-api/docs/pricing)
- [지원 모델 목록](https://ai.google.dev/gemini-api/docs/models)

## 문제 해결

### 일반적인 문제

1. **"GEMINI_API_KEY가 설정되지 않았습니다" 오류**
   - 환경 변수나 `.env` 파일에 API 키가 설정되어 있는지 확인
   - Streamlit을 사용하는 경우 `secrets.toml` 확인

2. **"google-genai 패키지가 설치되지 않았습니다" 오류**
   - `pip install google-genai` 실행

3. **모델이 지원되지 않는다는 오류**
   - 지원되는 모델 목록 확인: `get_supported_models()` 함수 사용
   - Gemini 3는 지원하지 않음

4. **위치 정보가 반영되지 않음**
   - `latitude`와 `longitude`가 올바른 형식인지 확인 (float 타입)
   - "near me" 쿼리는 위치 정보가 필요함

## 라이선스 및 사용 약관

Google Maps Grounding 사용 시 다음 사항을 준수해야 합니다:

1. **소스 표시 필수**: Google Maps 소스를 반드시 표시해야 합니다
2. **Google Maps 텍스트 속성**: "Google Maps" 텍스트는 수정하지 말고 지정된 스타일로 표시
3. **금지 지역**: 금지된 지역에서는 사용 불가
4. **고위험 활동 금지**: 응급 서비스 등 고위험 활동에 사용 금지

자세한 내용은 [Google Maps Grounding 서비스 사용 요구사항](https://ai.google.dev/gemini-api/docs/maps-grounding#service-usage-requirements)을 참조하세요.


"""
Google Maps Grounding을 위한 헬퍼 모듈

이 모듈은 Gemini API의 Google Maps Grounding 기능을 사용하여
위치 기반 쿼리에 대한 정확하고 최신의 응답을 제공합니다.

주요 기능:
- 위치 기반 쿼리 처리
- Google Maps 데이터 기반 응답 생성
- Grounding 메타데이터 파싱 및 표시
- 위젯 토큰 처리
"""

import os
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Streamlit 지원 (선택적)
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False


def get_gemini_api_key() -> Optional[str]:
    """
    Gemini API 키를 가져옵니다.
    
    Returns:
        API 키 문자열 또는 None
    """
    if STREAMLIT_AVAILABLE:
        try:
            # 1. 먼저 세션 상태에서 확인 (사용자가 웹에서 입력한 키)
            if 'user_api_key_GEMINI_API_KEY' in st.session_state and st.session_state['user_api_key_GEMINI_API_KEY']:
                return st.session_state['user_api_key_GEMINI_API_KEY']
            # 2. Streamlit secrets에서 확인 (secrets 파일이 없을 수 있으므로 안전하게 처리)
            # 3. 환경변수에서 확인
            try:
                api_key = st.secrets.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')
            except (FileNotFoundError, AttributeError, KeyError):
                api_key = os.environ.get('GEMINI_API_KEY')
            return api_key
        except Exception:
            api_key = os.environ.get('GEMINI_API_KEY')
            return api_key
    else:
        api_key = os.environ.get('GEMINI_API_KEY')
        return api_key


def generate_content_with_maps_grounding(
    prompt: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    model: str = "gemini-2.5-flash",
    enable_widget: bool = False,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Google Maps Grounding을 사용하여 위치 기반 콘텐츠를 생성합니다.
    
    Args:
        prompt: 사용자 쿼리 (예: "15분 거리 내 최고의 이탈리안 레스토랑은?")
        latitude: 위도 (선택사항, "near me" 쿼리에 유용)
        longitude: 경도 (선택사항, "near me" 쿼리에 유용)
        model: 사용할 Gemini 모델 (기본값: gemini-2.5-flash)
        enable_widget: Google Maps 위젯 토큰 활성화 여부
        api_key: API 키 (None이면 환경변수에서 가져옴)
    
    Returns:
        결과 딕셔너리:
        {
            "success": bool,
            "text": str,  # 생성된 응답 텍스트
            "sources": List[Dict],  # Google Maps 소스 목록
            "widget_token": Optional[str],  # 위젯 토큰 (enable_widget=True인 경우)
            "grounding_supports": List[Dict],  # 텍스트-소스 연결 정보
            "error": Optional[str]  # 오류 메시지
        }
    
    Example:
        >>> result = generate_content_with_maps_grounding(
        ...     prompt="서울 강남구 근처 카페 추천",
        ...     latitude=37.4979,
        ...     longitude=127.0276
        ... )
        >>> if result["success"]:
        ...     print(result["text"])
        ...     for source in result["sources"]:
        ...         print(f"- {source['title']}: {source['uri']}")
    """
    # API 키 확인
    if not api_key:
        api_key = get_gemini_api_key()
    
    if not api_key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY가 설정되지 않았습니다. 환경변수나 Streamlit secrets에 설정해주세요.",
            "text": "",
            "sources": [],
            "widget_token": None,
            "grounding_supports": []
        }
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        # Google Maps 도구 설정
        tools = [types.Tool(google_maps=types.GoogleMaps(enable_widget=enable_widget))]
        
        # Tool config 설정 (위치 정보가 있는 경우)
        tool_config = None
        if latitude is not None and longitude is not None:
            tool_config = types.ToolConfig(
                retrieval_config=types.RetrievalConfig(
                    lat_lng=types.LatLng(
                        latitude=latitude,
                        longitude=longitude
                    )
                )
            )
        
        # 콘텐츠 생성
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=tools,
                tool_config=tool_config
            )
        )
        
        # 응답 텍스트 추출
        response_text = response.text if hasattr(response, 'text') else ""
        
        # Grounding 메타데이터 파싱
        sources = []
        widget_token = None
        grounding_supports = []
        
        if hasattr(response, 'candidates') and len(response.candidates) > 0:
            candidate = response.candidates[0]
            
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                grounding = candidate.grounding_metadata
                
                # Grounding chunks (소스) 추출
                if hasattr(grounding, 'grounding_chunks') and grounding.grounding_chunks:
                    for chunk in grounding.grounding_chunks:
                        if hasattr(chunk, 'maps') and chunk.maps:
                            sources.append({
                                "title": chunk.maps.title if hasattr(chunk.maps, 'title') else "Unknown",
                                "uri": chunk.maps.uri if hasattr(chunk.maps, 'uri') else "",
                                "place_id": chunk.maps.place_id if hasattr(chunk.maps, 'place_id') else None
                            })
                
                # Grounding supports (텍스트-소스 연결) 추출
                if hasattr(grounding, 'grounding_supports') and grounding.grounding_supports:
                    for support in grounding.grounding_supports:
                        support_dict = {}
                        if hasattr(support, 'segment'):
                            segment = support.segment
                            support_dict["text"] = segment.text if hasattr(segment, 'text') else ""
                            support_dict["start_index"] = segment.start_index if hasattr(segment, 'start_index') else 0
                            support_dict["end_index"] = segment.end_index if hasattr(segment, 'end_index') else 0
                        if hasattr(support, 'grounding_chunk_indices'):
                            support_dict["chunk_indices"] = list(support.grounding_chunk_indices) if support.grounding_chunk_indices else []
                        grounding_supports.append(support_dict)
                
                # 위젯 토큰 추출
                if enable_widget and hasattr(grounding, 'google_maps_widget_context_token'):
                    widget_token = grounding.google_maps_widget_context_token
        
        return {
            "success": True,
            "text": response_text,
            "sources": sources,
            "widget_token": widget_token,
            "grounding_supports": grounding_supports,
            "model": model,
            "error": None
        }
    
    except ImportError:
        return {
            "success": False,
            "error": "google-genai 패키지가 설치되지 않았습니다. pip install google-genai를 실행하세요.",
            "text": "",
            "sources": [],
            "widget_token": None,
            "grounding_supports": []
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Google Maps Grounding 오류: {str(e)}",
            "text": "",
            "sources": [],
            "widget_token": None,
            "grounding_supports": []
        }


def format_sources_for_display(sources: List[Dict[str, Any]]) -> str:
    """
    소스 목록을 표시용 형식으로 포맷팅합니다.
    
    Args:
        sources: generate_content_with_maps_grounding에서 반환된 sources 리스트
    
    Returns:
        포맷팅된 마크다운 문자열
    
    Example:
        >>> sources = [
        ...     {"title": "카페 A", "uri": "https://maps.google.com/..."},
        ...     {"title": "카페 B", "uri": "https://maps.google.com/..."}
        ... ]
        >>> print(format_sources_for_display(sources))
    """
    if not sources:
        return ""
    
    formatted = "\n### 📍 Google Maps 소스\n\n"
    for i, source in enumerate(sources, 1):
        title = source.get("title", "Unknown")
        uri = source.get("uri", "")
        formatted += f"{i}. [{title}]({uri})\n"
    
    return formatted


def format_all_citations_for_display(all_citations: List[Dict[str, Any]]) -> str:
    """
    모든 소스의 citations를 통합하여 표시용 형식으로 포맷팅합니다.
    
    Args:
        all_citations: 통합된 citations 리스트 (source_type 포함)
    
    Returns:
        포맷팅된 마크다운 문자열
    
    Example:
        >>> citations = [
        ...     {"uri": "https://example.com", "title": "Example", "source_type": "google_search"},
        ...     {"uri": "file://doc.pdf", "title": "Document", "source_type": "file_search"}
        ... ]
        >>> print(format_all_citations_for_display(citations))
    """
    if not all_citations:
        return ""
    
    # 소스 타입별로 그룹화
    citations_by_type = {}
    for cit in all_citations:
        source_type = cit.get('source_type', 'unknown')
        if source_type not in citations_by_type:
            citations_by_type[source_type] = []
        citations_by_type[source_type].append(cit)
    
    formatted = "\n---\n\n## 참고 문헌\n\n"
    
    # 소스 타입별로 섹션 생성
    type_labels = {
        'google_search': '🌐 웹 검색 출처',
        'custom_search': '🔍 커스텀 검색 출처',
        'file_search': '📁 파일 검색 출처',
        'google_maps': '🗺️ 지도 출처',
        'url_context': '🔗 URL 출처',
        'unknown': '📚 기타 출처'
    }
    
    for source_type, citations in citations_by_type.items():
        label = type_labels.get(source_type, type_labels['unknown'])
        formatted += f"### {label}\n\n"
        
        for i, cit in enumerate(citations, 1):
            title = cit.get('title', cit.get('display_name', 'Unknown'))
            uri = cit.get('uri', cit.get('file_uri', ''))
            
            if uri:
                formatted += f"{i}. [{title}]({uri})\n"
            else:
                formatted += f"{i}. {title}\n"
            
            # 추가 정보 표시 (snippet 등)
            if cit.get('snippet'):
                snippet = cit['snippet']
                if len(snippet) > 100:
                    snippet = snippet[:100] + "..."
                formatted += f"   *{snippet}*\n"
        
        formatted += "\n"
    
    return formatted


def format_grounding_supports_for_display(
    text: str,
    grounding_supports: List[Dict[str, Any]],
    sources: List[Dict[str, Any]]
) -> str:
    """
    Grounding supports를 사용하여 인라인 인용을 포함한 텍스트를 생성합니다.
    
    Args:
        text: 원본 응답 텍스트
        grounding_supports: grounding_supports 리스트
        sources: sources 리스트
    
    Returns:
        인용이 포함된 마크다운 형식 텍스트
    """
    if not grounding_supports or not sources:
        return text
    
    # 텍스트를 문자 단위로 분할하여 인용 추가
    # 간단한 구현: 각 support에 대해 해당 텍스트 부분에 인용 추가
    result_text = text
    
    # 역순으로 처리하여 인덱스 변경 영향 최소화
    for support in sorted(grounding_supports, key=lambda x: x.get("start_index", 0), reverse=True):
        start_idx = support.get("start_index", 0)
        end_idx = support.get("end_index", len(text))
        chunk_indices = support.get("chunk_indices", [])
        
        if chunk_indices and start_idx < len(text) and end_idx <= len(text):
            # 해당 텍스트 부분 추출
            segment_text = text[start_idx:end_idx]
            
            # 소스 링크 생성
            source_links = []
            for idx in chunk_indices:
                if 0 <= idx < len(sources):
                    source = sources[idx]
                    title = source.get("title", "Unknown")
                    uri = source.get("uri", "")
                    if uri:
                        source_links.append(f"[{title}]({uri})")
            
            if source_links:
                # 인용 추가 (텍스트 뒤에 소스 링크 추가)
                citation = f" [{', '.join(source_links)}]"
                result_text = (
                    result_text[:end_idx] + 
                    citation + 
                    result_text[end_idx:]
                )
    
    return result_text


def get_supported_models() -> List[str]:
    """
    Google Maps Grounding을 지원하는 모델 목록을 반환합니다.
    
    Returns:
        지원 모델 이름 리스트
    """
    return [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash"
    ]


def validate_model_for_maps_grounding(model: str) -> bool:
    """
    모델이 Google Maps Grounding을 지원하는지 확인합니다.
    
    Args:
        model: 모델 이름
    
    Returns:
        지원 여부 (True/False)
    """
    supported_models = get_supported_models()
    return any(supported in model for supported in supported_models)


# 사용 예제 함수들

def example_place_specific_query():
    """
    장소별 질문 처리 예제
    """
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
    else:
        print(f"오류: {result['error']}")


def example_location_based_personalization():
    """
    위치 기반 개인화 예제
    """
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
    else:
        print(f"오류: {result['error']}")


def example_itinerary_planning():
    """
    여행 일정 계획 예제 (위젯 토큰 포함)
    """
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
        print(format_sources_for_display(result["sources"]))
        
        if result["widget_token"]:
            print(f"\n위젯 토큰: {result['widget_token']}")
            print("\nHTML 위젯 코드:")
            print(f'<gmp-place-contextual context-token="{result["widget_token"]}"></gmp-place-contextual>')
    else:
        print(f"오류: {result['error']}")


if __name__ == "__main__":
    # 예제 실행
    print("=== Google Maps Grounding 예제 ===\n")
    
    print("1. 장소별 질문 처리:")
    example_place_specific_query()
    
    print("\n" + "="*50 + "\n")
    
    print("2. 위치 기반 개인화:")
    example_location_based_personalization()
    
    print("\n" + "="*50 + "\n")
    
    print("3. 여행 일정 계획 (위젯 포함):")
    example_itinerary_planning()


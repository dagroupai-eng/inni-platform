"""
Google Maps Grounding 테스트 스크립트

이 스크립트는 maps_grounding_helper 모듈의 기능을 테스트합니다.
실행 전에 GEMINI_API_KEY 환경 변수가 설정되어 있어야 합니다.
"""

import os
from maps_grounding_helper import (
    generate_content_with_maps_grounding,
    format_sources_for_display,
    format_grounding_supports_for_display,
    get_supported_models,
    validate_model_for_maps_grounding
)


def test_basic_query():
    """기본 쿼리 테스트 (위치 정보 없음)"""
    print("=" * 60)
    print("테스트 1: 기본 쿼리 (위치 정보 없음)")
    print("=" * 60)
    
    result = generate_content_with_maps_grounding(
        prompt="타임스퀘어 근처 레스토랑 추천"
    )
    
    if result["success"]:
        print("\n✅ 성공!")
        print("\n응답:")
        print(result["text"])
        print("\n소스:")
        for source in result["sources"]:
            print(f"  - {source['title']}: {source['uri']}")
    else:
        print(f"\n❌ 실패: {result['error']}")
    
    print("\n")


def test_location_based_query():
    """위치 기반 쿼리 테스트"""
    print("=" * 60)
    print("테스트 2: 위치 기반 쿼리")
    print("=" * 60)
    
    result = generate_content_with_maps_grounding(
        prompt="15분 거리 내 최고의 이탈리안 레스토랑은?",
        latitude=34.050481,  # Los Angeles
        longitude=-118.248526
    )
    
    if result["success"]:
        print("\n✅ 성공!")
        print("\n응답:")
        print(result["text"])
        print(format_sources_for_display(result["sources"]))
    else:
        print(f"\n❌ 실패: {result['error']}")
    
    print("\n")


def test_place_specific_query():
    """장소별 질문 테스트"""
    print("=" * 60)
    print("테스트 3: 장소별 질문")
    print("=" * 60)
    
    result = generate_content_with_maps_grounding(
        prompt="1번가와 메인가 모퉁이 근처에 야외 좌석이 있는 카페가 있나요?",
        latitude=34.050481,  # Los Angeles
        longitude=-118.248526,
        model="gemini-2.5-flash"
    )
    
    if result["success"]:
        print("\n✅ 성공!")
        print("\n응답:")
        print(result["text"])
        print("\n소스:")
        for source in result["sources"]:
            print(f"  - {source['title']}: {source['uri']}")
    else:
        print(f"\n❌ 실패: {result['error']}")
    
    print("\n")


def test_widget_token():
    """위젯 토큰 테스트"""
    print("=" * 60)
    print("테스트 4: 위젯 토큰 (enable_widget=True)")
    print("=" * 60)
    
    result = generate_content_with_maps_grounding(
        prompt="샌프란시스코에서 하루 일정을 계획해주세요. 골든게이트 브리지를 보고, 박물관을 방문하고 싶습니다.",
        latitude=37.78193,  # San Francisco
        longitude=-122.40476,
        model="gemini-2.5-flash",
        enable_widget=True
    )
    
    if result["success"]:
        print("\n✅ 성공!")
        print("\n응답:")
        print(result["text"])
        
        if result["widget_token"]:
            print("\n위젯 토큰:")
            print(result["widget_token"])
            print("\nHTML 위젯 코드:")
            print(f'<gmp-place-contextual context-token="{result["widget_token"]}"></gmp-place-contextual>')
        else:
            print("\n⚠️ 위젯 토큰이 반환되지 않았습니다.")
    else:
        print(f"\n❌ 실패: {result['error']}")
    
    print("\n")


def test_model_validation():
    """모델 검증 테스트"""
    print("=" * 60)
    print("테스트 5: 모델 검증")
    print("=" * 60)
    
    print("\n지원되는 모델:")
    supported_models = get_supported_models()
    for model in supported_models:
        print(f"  - {model}")
    
    print("\n모델 검증 테스트:")
    test_models = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-3-pro",
        "gpt-4"
    ]
    
    for model in test_models:
        is_supported = validate_model_for_maps_grounding(model)
        status = "✅ 지원됨" if is_supported else "❌ 지원 안 됨"
        print(f"  - {model}: {status}")
    
    print("\n")


def test_korean_location():
    """한국 위치 테스트"""
    print("=" * 60)
    print("테스트 6: 한국 위치 (서울 강남구)")
    print("=" * 60)
    
    result = generate_content_with_maps_grounding(
        prompt="서울 강남구 근처 카페 추천",
        latitude=37.4979,  # 강남구
        longitude=127.0276,
        model="gemini-2.5-flash"
    )
    
    if result["success"]:
        print("\n✅ 성공!")
        print("\n응답:")
        print(result["text"])
        print("\n소스:")
        for source in result["sources"]:
            print(f"  - {source['title']}: {source['uri']}")
    else:
        print(f"\n❌ 실패: {result['error']}")
    
    print("\n")


def main():
    """메인 테스트 함수"""
    print("\n" + "=" * 60)
    print("Google Maps Grounding 테스트 시작")
    print("=" * 60 + "\n")
    
    # API 키 확인
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("⚠️ 경고: GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   일부 테스트가 실패할 수 있습니다.\n")
    else:
        print(f"✅ GEMINI_API_KEY 설정됨 (길이: {len(api_key)}자)\n")
    
    # 테스트 실행
    try:
        test_model_validation()
        test_basic_query()
        test_location_based_query()
        test_place_specific_query()
        test_widget_token()
        test_korean_location()
        
        print("=" * 60)
        print("모든 테스트 완료!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


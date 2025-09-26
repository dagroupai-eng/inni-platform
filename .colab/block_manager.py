"""
사용자 정의 분석 블록 관리 도구
"""

def manage_custom_blocks(app):
    """사용자 정의 블록 관리"""
    print("🔧 사용자 정의 분석 블록 관리")
    print("=" * 50)
    
    while True:
        print("\n📋 사용 가능한 작업:")
        print("1. 블록 추가")
        print("2. 블록 제거")
        print("3. 블록 목록 보기")
        print("4. 블록 저장")
        print("5. 블록 불러오기")
        print("6. 종료")
        
        choice = input("\n작업을 선택하세요 (1-6): ").strip()
        
        if choice == "1":
            add_custom_block(app)
        elif choice == "2":
            remove_custom_block(app)
        elif choice == "3":
            list_custom_blocks(app)
        elif choice == "4":
            save_custom_blocks(app)
        elif choice == "5":
            load_custom_blocks(app)
        elif choice == "6":
            print("👋 블록 관리 종료")
            break
        else:
            print("❌ 잘못된 선택입니다.")

def add_custom_block(app):
    """사용자 정의 블록 추가"""
    print("\n➕ 새로운 분석 블록 추가")
    print("-" * 30)
    
    # 블록 ID 입력
    block_id = input("블록 ID (영문, 숫자, 언더스코어만): ").strip()
    if not block_id or not block_id.replace('_', '').isalnum():
        print("❌ 올바른 블록 ID를 입력해주세요.")
        return
    
    # 기존 블록 확인
    if block_id in app.analysis_blocks.get_all_blocks():
        print(f"❌ '{block_id}' ID는 이미 존재합니다.")
        return
    
    # 블록 이름 입력
    name = input("블록 이름 (예: 🏢 건물 구조 분석): ").strip()
    if not name:
        print("❌ 블록 이름을 입력해주세요.")
        return
    
    # 블록 설명 입력
    description = input("블록 설명: ").strip()
    if not description:
        description = f"{name} 분석 블록"
    
    # 프롬프트 입력
    print("\n📝 분석 프롬프트를 입력하세요:")
    print("(PDF 내용은 {pdf_content}로 표시됩니다)")
    print("예시: 다음 건축 프로젝트 PDF를 분석해주세요:\n\n{pdf_content}")
    
    prompt = input("\n프롬프트: ").strip()
    if not prompt:
        print("❌ 프롬프트를 입력해주세요.")
        return
    
    # 블록 추가
    app.analysis_blocks.add_custom_block(block_id, name, description, prompt)
    
    print(f"\n✅ 블록 '{name}' 추가 완료!")
    print("💡 이제 PDF 분석에서 사용할 수 있습니다.")

def remove_custom_block(app):
    """사용자 정의 블록 제거"""
    print("\n➖ 사용자 정의 블록 제거")
    print("-" * 30)
    
    # 사용자 정의 블록 목록 표시
    if not app.analysis_blocks.custom_blocks:
        print("📝 제거할 사용자 정의 블록이 없습니다.")
        return
    
    print("📝 사용자 정의 블록 목록:")
    for i, (block_id, block) in enumerate(app.analysis_blocks.custom_blocks.items(), 1):
        print(f"{i}. {block_id}: {block['name']}")
    
    # 제거할 블록 선택
    try:
        choice = int(input("\n제거할 블록 번호: ")) - 1
        block_ids = list(app.analysis_blocks.custom_blocks.keys())
        
        if 0 <= choice < len(block_ids):
            block_id = block_ids[choice]
            block_name = app.analysis_blocks.custom_blocks[block_id]["name"]
            
            confirm = input(f"'{block_name}' 블록을 제거하시겠습니까? (y/N): ").strip().lower()
            if confirm == 'y':
                app.analysis_blocks.remove_custom_block(block_id)
            else:
                print("❌ 제거가 취소되었습니다.")
        else:
            print("❌ 잘못된 번호입니다.")
    except ValueError:
        print("❌ 올바른 번호를 입력해주세요.")

def list_custom_blocks(app):
    """사용자 정의 블록 목록 표시"""
    print("\n📋 사용자 정의 블록 목록")
    print("-" * 30)
    
    if not app.analysis_blocks.custom_blocks:
        print("📝 사용자 정의 블록이 없습니다.")
        return
    
    for block_id, block in app.analysis_blocks.custom_blocks.items():
        print(f"\n🔧 {block['name']}")
        print(f"   ID: {block_id}")
        print(f"   설명: {block['description']}")
        print(f"   프롬프트: {block['prompt'][:100]}...")

def save_custom_blocks(app):
    """사용자 정의 블록 저장"""
    print("\n💾 사용자 정의 블록 저장")
    print("-" * 30)
    
    if not app.analysis_blocks.custom_blocks:
        print("📝 저장할 사용자 정의 블록이 없습니다.")
        return
    
    filename = input("저장할 파일명 (기본: custom_blocks.json): ").strip()
    if not filename:
        filename = "custom_blocks.json"
    
    if not filename.endswith('.json'):
        filename += '.json'
    
    app.analysis_blocks.save_custom_blocks(filename)

def load_custom_blocks(app):
    """사용자 정의 블록 불러오기"""
    print("\n📂 사용자 정의 블록 불러오기")
    print("-" * 30)
    
    filename = input("불러올 파일명 (기본: custom_blocks.json): ").strip()
    if not filename:
        filename = "custom_blocks.json"
    
    if not filename.endswith('.json'):
        filename += '.json'
    
    app.analysis_blocks.load_custom_blocks(filename)

def show_block_templates():
    """블록 템플릿 표시"""
    print("\n📋 분석 블록 템플릿")
    print("=" * 50)
    
    templates = {
        "환경분석": {
            "name": "🌱 환경 분석",
            "description": "건축 프로젝트의 환경적 요소를 분석합니다",
            "prompt": """다음 건축 프로젝트 PDF를 환경적 관점에서 분석해주세요:

**분석 요청사항:**
1. 자연환경 요소
   - 일조, 채광, 통풍 조건
   - 주변 자연환경과의 조화
   - 기후 조건 고려사항

2. 에너지 효율성
   - 에너지 절약 방안
   - 재생에너지 활용 가능성
   - 친환경 설비 계획

3. 환경 친화적 설계
   - 친환경 재료 사용
   - 폐기물 최소화 방안
   - 생태계 보전 방안

**분석 형식:**
- 각 요소별 구체적 분석
- 개선 방안 제시
- 환경 친화성 점수 평가 (1-10점)

PDF 내용: {pdf_content}"""
        },
        "안전성분석": {
            "name": "🛡️ 안전성 분석",
            "description": "건축 프로젝트의 안전성 요소를 분석합니다",
            "prompt": """다음 건축 프로젝트 PDF를 안전성 관점에서 분석해주세요:

**분석 요청사항:**
1. 구조적 안전성
   - 내진 설계 요소
   - 화재 안전 설계
   - 구조물 안정성

2. 사용자 안전성
   - 비상 대피 계획
   - 안전 시설 배치
   - 접근성 및 편의성

3. 운영 안전성
   - 유지보수 계획
   - 안전 관리 체계
   - 위험 요소 관리

**분석 형식:**
- 각 안전 요소별 분석
- 위험도 평가 (1-10점)
- 개선 방안 제시

PDF 내용: {pdf_content}"""
        },
        "경제성분석": {
            "name": "💰 경제성 분석",
            "description": "건축 프로젝트의 경제적 타당성을 분석합니다",
            "prompt": """다음 건축 프로젝트 PDF를 경제적 관점에서 분석해주세요:

**분석 요청사항:**
1. 건설비용 분석
   - 예상 건설비용
   - 비용 구성 요소
   - 비용 절감 방안

2. 운영비용 분석
   - 유지보수 비용
   - 에너지 비용
   - 관리비용

3. 수익성 분석
   - 투자 회수 기간
   - 수익률 분석
   - 경제적 효과

**분석 형식:**
- 각 비용 요소별 분석
- 경제성 점수 평가 (1-10점)
- 개선 방안 제시

PDF 내용: {pdf_content}"""
        }
    }
    
    for template_id, template in templates.items():
        print(f"\n📋 {template['name']}")
        print(f"   설명: {template['description']}")
        print(f"   프롬프트 미리보기: {template['prompt'][:100]}...")
    
    print(f"\n💡 이 템플릿들을 참고하여 자신만의 블록을 만들어보세요!")

def quick_add_template_block(app):
    """템플릿 블록 빠른 추가"""
    print("\n⚡ 템플릿 블록 빠른 추가")
    print("=" * 50)
    
    templates = {
        "1": ("환경분석", "🌱 환경 분석"),
        "2": ("안전성분석", "🛡️ 안전성 분석"),
        "3": ("경제성분석", "💰 경제성 분석")
    }
    
    print("📋 사용 가능한 템플릿:")
    for key, (template_id, name) in templates.items():
        print(f"{key}. {name}")
    
    choice = input("\n추가할 템플릿 번호: ").strip()
    
    if choice in templates:
        template_id, name = templates[choice]
        
        # 템플릿 데이터
        template_data = {
            "환경분석": {
                "description": "건축 프로젝트의 환경적 요소를 분석합니다",
                "prompt": """다음 건축 프로젝트 PDF를 환경적 관점에서 분석해주세요:

**분석 요청사항:**
1. 자연환경 요소
   - 일조, 채광, 통풍 조건
   - 주변 자연환경과의 조화
   - 기후 조건 고려사항

2. 에너지 효율성
   - 에너지 절약 방안
   - 재생에너지 활용 가능성
   - 친환경 설비 계획

3. 환경 친화적 설계
   - 친환경 재료 사용
   - 폐기물 최소화 방안
   - 생태계 보전 방안

**분석 형식:**
- 각 요소별 구체적 분석
- 개선 방안 제시
- 환경 친화성 점수 평가 (1-10점)

PDF 내용: {pdf_content}"""
            },
            "안전성분석": {
                "description": "건축 프로젝트의 안전성 요소를 분석합니다",
                "prompt": """다음 건축 프로젝트 PDF를 안전성 관점에서 분석해주세요:

**분석 요청사항:**
1. 구조적 안전성
   - 내진 설계 요소
   - 화재 안전 설계
   - 구조물 안정성

2. 사용자 안전성
   - 비상 대피 계획
   - 안전 시설 배치
   - 접근성 및 편의성

3. 운영 안전성
   - 유지보수 계획
   - 안전 관리 체계
   - 위험 요소 관리

**분석 형식:**
- 각 안전 요소별 분석
- 위험도 평가 (1-10점)
- 개선 방안 제시

PDF 내용: {pdf_content}"""
            },
            "경제성분석": {
                "description": "건축 프로젝트의 경제적 타당성을 분석합니다",
                "prompt": """다음 건축 프로젝트 PDF를 경제적 관점에서 분석해주세요:

**분석 요청사항:**
1. 건설비용 분석
   - 예상 건설비용
   - 비용 구성 요소
   - 비용 절감 방안

2. 운영비용 분석
   - 유지보수 비용
   - 에너지 비용
   - 관리비용

3. 수익성 분석
   - 투자 회수 기간
   - 수익률 분석
   - 경제적 효과

**분석 형식:**
- 각 비용 요소별 분석
- 경제성 점수 평가 (1-10점)
- 개선 방안 제시

PDF 내용: {pdf_content}"""
            }
        }
        
        data = template_data[template_id]
        app.analysis_blocks.add_custom_block(template_id, name, data["description"], data["prompt"])
        
        print(f"\n✅ 템플릿 블록 '{name}' 추가 완료!")
    else:
        print("❌ 잘못된 선택입니다.")

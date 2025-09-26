"""
분석 실행 도우미 함수들
"""

def run_pdf_analysis(app):
    """PDF 분석 실행"""
    print("📄 PDF 분석을 시작합니다!")
    print("=" * 50)

    # 앱 상태 확인
    if not app:
        print("❌ 앱이 초기화되지 않았습니다.")
        print("💡 먼저 'app = run_simple_arch_insight()'를 실행해주세요.")
        return
    
    if not app.current_analyzer:
        print("❌ AI 모델이 설정되지 않았습니다.")
        print("💡 앱을 다시 실행하고 API 키를 설정해주세요.")
        return

    # 프로젝트명 입력
    project_name = input("프로젝트명을 입력하세요: ")

    # 분석 블록 선택
    print("\n📋 사용 가능한 분석 블록:")
    all_blocks = app.analysis_blocks.get_all_blocks()
    blocks = list(all_blocks.keys())
    for i, block_id in enumerate(blocks, 1):
        block_name = all_blocks[block_id]["name"]
        block_type = "🔧" if block_id in app.analysis_blocks.custom_blocks else "📋"
        print(f"{i}. {block_type} {block_name}")

    print("\n분석할 블록을 선택하세요 (번호 입력, 여러 개는 쉼표로 구분):")
    selected_input = input("예: 1,2,3 또는 1: ")

    # 선택된 블록 처리
    try:
        if ',' in selected_input:
            selected_indices = [int(x.strip()) - 1 for x in selected_input.split(',')]
        else:
            selected_indices = [int(selected_input.strip()) - 1]
        
        selected_blocks = [blocks[i] for i in selected_indices if 0 <= i < len(blocks)]
        
        if not selected_blocks:
            print("❌ 잘못된 선택입니다. 기본 정보 추출만 실행합니다.")
            selected_blocks = ['basic_info']
        
        print(f"\n✅ 선택된 분석 블록: {[all_blocks[block_id]['name'] for block_id in selected_blocks]}")
        
        # 분석 실행
        app.run_analysis(project_name, selected_blocks)
        
    except ValueError:
        print("❌ 잘못된 입력입니다. 기본 정보 추출만 실행합니다.")
        app.run_analysis(project_name, ['basic_info'])

def show_analysis_statistics(app):
    """분석 통계 표시"""
    if hasattr(app, 'stats_manager') and app.stats_manager.analysis_history:
        app.show_statistics()
    else:
        print("📊 분석 기록이 없습니다. 먼저 PDF를 분석해주세요.")

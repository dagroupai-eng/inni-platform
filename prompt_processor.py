import json
import os
from typing import List, Dict, Any

def load_blocks() -> List[Dict[str, Any]]:
    """blocks.json에서 블록들을 로드합니다."""
    try:
        with open('blocks.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('blocks', [])
    except FileNotFoundError:
        print("blocks.json 파일을 찾을 수 없습니다.")
        return []
    except json.JSONDecodeError:
        print("blocks.json 파일 형식이 올바르지 않습니다.")
        return []

def process_prompt(block: Dict[str, Any], pdf_text: str) -> str:
    """블록의 프롬프트에 PDF 텍스트를 삽입합니다."""
    try:
        if not isinstance(block, dict):
            raise ValueError("블록 데이터가 올바르지 않습니다.")
        
        if 'prompt' not in block:
            raise KeyError("블록에 'prompt' 키가 없습니다.")
        
        if not isinstance(pdf_text, str):
            pdf_text = str(pdf_text)
        
        # PDF 텍스트 길이 제한 (토큰 제한 고려)
        if len(pdf_text) > 8000:
            pdf_text = pdf_text[:8000] + "\n\n[내용이 길어 일부만 표시됩니다...]"
        
        # RISEN 구조 블록인지 확인
        if 'role' in block and 'instructions' in block and 'steps' in block:
            return _process_risen_prompt(block, pdf_text)
        else:
            # 기존 구조 블록
            return block['prompt'].format(pdf_text=pdf_text)
        
    except KeyError as e:
        print(f"프롬프트 처리 오류: {e}")
        return block.get('prompt', '')
    except Exception as e:
        print(f"프롬프트 처리 중 예상치 못한 오류: {e}")
        return block.get('prompt', '')

def _process_risen_prompt(block: Dict[str, Any], pdf_text: str) -> str:
    """RISEN 구조의 프롬프트를 처리합니다."""
    try:
        # 단계들을 포맷팅
        steps_formatted = ""
        for i, step in enumerate(block.get('steps', []), 1):
            steps_formatted += f"{i}. **{step}**\n"
        
        # narrowing 객체 처리
        narrowing = block.get('narrowing', {})
        narrowing_formatted = ""
        
        # narrowing의 각 항목을 처리
        for key, value in narrowing.items():
            if isinstance(value, list):
                value_str = ", ".join(value)
            else:
                value_str = str(value)
            narrowing_formatted += f"- **{key.replace('_', ' ').title()}:** {value_str}\n"
        
        # 프롬프트 템플릿에 값들 삽입
        prompt_template = block['prompt']
        
        # narrowing 필드들을 문자열로 변환
        def format_narrowing_value(value):
            if isinstance(value, list):
                return ", ".join(value)
            return str(value)
        
        # 기본 필드들
        formatted_prompt = prompt_template.format(
            role=block.get('role', ''),
            instructions=block.get('instructions', ''),
            steps_formatted=steps_formatted,
            end_goal=block.get('end_goal', ''),
            narrowing_output_format=format_narrowing_value(narrowing.get('output_format', '')),
            narrowing_required_items=format_narrowing_value(narrowing.get('required_items', '')),
            narrowing_classification_criteria=format_narrowing_value(narrowing.get('classification_criteria', '')),
            narrowing_evaluation_scale=format_narrowing_value(narrowing.get('evaluation_scale', '')),
            narrowing_constraints=format_narrowing_value(narrowing.get('constraints', '')),
            narrowing_quality_standards=format_narrowing_value(narrowing.get('quality_standards', '')),
            # 추가 narrowing 필드들
            narrowing_required_sections=format_narrowing_value(narrowing.get('required_sections', '')),
            narrowing_design_focus=format_narrowing_value(narrowing.get('design_focus', '')),
            narrowing_required_metrics=format_narrowing_value(narrowing.get('required_metrics', '')),
            narrowing_calculation_method=format_narrowing_value(narrowing.get('calculation_method', '')),
            narrowing_evaluation_criteria=format_narrowing_value(narrowing.get('evaluation_criteria', '')),
            narrowing_scoring_system=format_narrowing_value(narrowing.get('scoring_system', '')),
            narrowing_verification_scope=format_narrowing_value(narrowing.get('verification_scope', '')),
            narrowing_risk_assessment=format_narrowing_value(narrowing.get('risk_assessment', '')),
            narrowing_analysis_areas=format_narrowing_value(narrowing.get('analysis_areas', '')),
            pdf_text=pdf_text
        )
        
        # 디버깅을 위한 출력 (개발 시에만)
        print(f"=== {block.get('id', 'unknown')} 블록 프롬프트 생성 완료 ===")
        print(f"블록 ID: {block.get('id', 'unknown')}")
        print(f"블록 이름: {block.get('name', 'unknown')}")
        print(f"프롬프트 길이: {len(formatted_prompt)}자")
        
        # 프롬프트의 핵심 부분들 출력
        if "역할 (Role):" in formatted_prompt:
            role_start = formatted_prompt.find("역할 (Role):")
            role_end = formatted_prompt.find("**지시 (Instructions):**", role_start)
            if role_end > role_start:
                role_text = formatted_prompt[role_start:role_end].strip()
                print(f"역할 섹션: {role_text[:100]}...")
        
        if "지시 (Instructions):" in formatted_prompt:
            inst_start = formatted_prompt.find("지시 (Instructions):")
            inst_end = formatted_prompt.find("**단계 (Steps):**", inst_start)
            if inst_end > inst_start:
                inst_text = formatted_prompt[inst_start:inst_end].strip()
                print(f"지시 섹션: {inst_text[:100]}...")
        
        # 프롬프트 해시 생성 (고유성 확인용)
        import hashlib
        prompt_hash = hashlib.md5(formatted_prompt.encode()).hexdigest()[:8]
        print(f"프롬프트 해시: {prompt_hash}")
        
        # 프롬프트가 제대로 생성되었는지 확인
        if "역할 (Role):" not in formatted_prompt:
            print("❌ ERROR: 프롬프트에 '역할 (Role):' 섹션이 없습니다!")
        if "지시 (Instructions):" not in formatted_prompt:
            print("❌ ERROR: 프롬프트에 '지시 (Instructions):' 섹션이 없습니다!")
        if "단계 (Steps):" not in formatted_prompt:
            print("❌ ERROR: 프롬프트에 '단계 (Steps):' 섹션이 없습니다!")
        
        print(f"✅ 프롬프트 구조 검증 완료")
        print("=" * 50)
        
        return formatted_prompt
        
    except Exception as e:
        print(f"RISEN 프롬프트 처리 오류: {e}")
        # 오류 발생 시 기본 프롬프트 반환
        return block.get('prompt', '').format(pdf_text=pdf_text)

def get_block_by_id(block_id: str) -> Dict[str, Any]:
    """ID로 특정 블록을 찾습니다."""
    blocks = load_blocks()
    for block in blocks:
        if block.get('id') == block_id:
            return block
    return {}

def save_custom_block(block_data: Dict[str, Any]) -> bool:
    """사용자 정의 블록을 저장합니다."""
    try:
        # 사용자 정의 블록들을 별도 파일에 저장
        custom_blocks_file = 'custom_blocks.json'
        
        # 기존 사용자 정의 블록들 로드
        if os.path.exists(custom_blocks_file):
            with open(custom_blocks_file, 'r', encoding='utf-8') as f:
                custom_blocks = json.load(f)
        else:
            custom_blocks = {"blocks": []}
        
        # 새 블록 추가
        custom_blocks["blocks"].append(block_data)
        
        # 저장
        with open(custom_blocks_file, 'w', encoding='utf-8') as f:
            json.dump(custom_blocks, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"사용자 정의 블록 저장 오류: {e}")
        return False

def load_custom_blocks() -> List[Dict[str, Any]]:
    """사용자 정의 블록들을 로드합니다."""
    try:
        with open('custom_blocks.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('blocks', [])
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print("custom_blocks.json 파일 형식이 올바르지 않습니다.")
        return []

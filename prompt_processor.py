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
        if len(pdf_text) > 5000:
            pdf_text = pdf_text[:5000] + "\n\n[내용이 길어 일부만 표시됩니다...]"
        
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
        
        # 기본 필드들
        formatted_prompt = prompt_template.format(
            role=block.get('role', ''),
            instructions=block.get('instructions', ''),
            steps_formatted=steps_formatted,
            end_goal=block.get('end_goal', ''),
            narrowing_output_format=narrowing.get('output_format', ''),
            narrowing_required_items=narrowing.get('required_items', ''),
            narrowing_classification_criteria=narrowing.get('classification_criteria', ''),
            narrowing_evaluation_scale=narrowing.get('evaluation_scale', ''),
            narrowing_constraints=narrowing.get('constraints', ''),
            narrowing_quality_standards=narrowing.get('quality_standards', ''),
            # 추가 narrowing 필드들
            narrowing_required_sections=narrowing.get('required_sections', ''),
            narrowing_design_focus=narrowing.get('design_focus', ''),
            narrowing_required_metrics=narrowing.get('required_metrics', ''),
            narrowing_calculation_method=narrowing.get('calculation_method', ''),
            narrowing_evaluation_criteria=narrowing.get('evaluation_criteria', ''),
            narrowing_scoring_system=narrowing.get('scoring_system', ''),
            narrowing_verification_scope=narrowing.get('verification_scope', ''),
            narrowing_risk_assessment=narrowing.get('risk_assessment', ''),
            narrowing_analysis_areas=narrowing.get('analysis_areas', ''),
            pdf_text=pdf_text
        )
        
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

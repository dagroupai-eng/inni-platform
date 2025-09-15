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
        
        return block['prompt'].format(pdf_text=pdf_text)
        
    except KeyError as e:
        print(f"프롬프트 처리 오류: {e}")
        return block.get('prompt', '')
    except Exception as e:
        print(f"프롬프트 처리 중 예상치 못한 오류: {e}")
        return block.get('prompt', '')

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

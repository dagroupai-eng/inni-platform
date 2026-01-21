import json
import os
from typing import List, Dict, Any

UNIFIED_PROMPT_TEMPLATE = """
## 역할 (Role)
{role}

## 지시 (Instructions)
{instructions}

## 단계 (Steps)
{steps_formatted}

## 최종 목표 (End Goal)
{end_goal}

## 구체화/제약 조건 (Narrowing)
{narrowing_formatted}

## 작성 지침 (General Guidelines)
1. 표/코드 블록을 제시하기 전에 200-400자 이상의 서술형 분석을 작성하세요.
2. 모든 표 아래에는 4-8문장(300-600자) 해설을 추가하고, 수치·근거·추론 과정을 명확히 밝히세요.
3. 가능한 한 구체적인 수치·단위·산정 근거를 제시하고, 불확실한 정보는 \"추가 확인 필요\"라고 표시하세요.
4. 단계별 논리 전개가 드러나도록 Chain-of-Thought 방식으로 설명하고, 추상적 표현보다는 구체적 사례와 데이터를 사용하세요.
5. 결과물은 Markdown 구조를 유지하되, 사용자가 바로 검토할 수 있도록 명확하고 일관된 섹션 구성을 지키세요.

## 분석할 입력 텍스트
{pdf_text}
""".strip()


def _format_steps(steps: List[str]) -> str:
    if not steps:
        return "1. **단계 정보가 제공되지 않았습니다. 제공된 데이터를 기반으로 합리적인 절차를 구성하세요.**"
    lines = []
    for i, step in enumerate(steps, 1):
        clean_step = step.strip() or "세부 단계 설명 없음"
        lines.append(f"{i}. **{clean_step}**")
    return "\n".join(lines)


def _format_narrowing(narrowing: Dict[str, Any]) -> str:
    if not narrowing:
        return "- 해당 블록에 특화된 추가 제약 조건이 제공되지 않았습니다. 기본 작성 지침을 충실히 따르세요."

    lines = []
    for key, value in narrowing.items():
        label = key.replace("_", " ").strip().title()
        if isinstance(value, list):
            if not value:
                value_text = "없음"
            else:
                bullet_items = "\n  - ".join(str(item) for item in value)
                value_text = f"\n  - {bullet_items}"
                lines.append(f"- **{label}:**{value_text}")
                continue
        value_text = str(value).strip()
        if not value_text:
            value_text = "없음"
        lines.append(f"- **{label}:** {value_text}")
    return "\n".join(lines)

def load_blocks(include_user_blocks: bool = True) -> List[Dict[str, Any]]:
    """
    blocks.json에서 블록들을 로드합니다.
    사용자 인증이 되어 있으면 접근 가능한 DB 블록도 함께 로드합니다.

    Args:
        include_user_blocks: True면 현재 사용자가 접근 가능한 DB 블록도 포함

    Returns:
        블록 목록
    """
    blocks = []

    # 1. blocks.json에서 시스템 블록 로드
    try:
        with open('blocks.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            blocks = data.get('blocks', [])
    except FileNotFoundError:
        print("blocks.json 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError:
        print("blocks.json 파일 형식이 올바르지 않습니다.")

    # 2. 사용자 DB 블록 로드 (인증된 경우만)
    if include_user_blocks:
        try:
            from auth.authentication import is_authenticated, get_current_user
            from blocks.block_manager import get_accessible_blocks

            if is_authenticated():
                user = get_current_user()
                if user:
                    user_id = user.get("id")
                    team_id = user.get("team_id")

                    # 접근 가능한 블록 조회
                    db_blocks = get_accessible_blocks(user_id, team_id)

                    # block_data 필드를 블록 형태로 변환
                    for db_block in db_blocks:
                        block_data = db_block.get("block_data", {})
                        if isinstance(block_data, dict):
                            # DB 메타데이터 추가
                            block_data["_db_id"] = db_block.get("id")
                            block_data["_owner_id"] = db_block.get("owner_id")
                            block_data["_visibility"] = db_block.get("visibility")
                            blocks.append(block_data)
        except ImportError:
            pass  # 인증 모듈이 없으면 시스템 블록만 사용
        except Exception as e:
            print(f"사용자 블록 로드 오류: {e}")

    return blocks

def process_prompt(block: Dict[str, Any], pdf_text: str) -> str:
    """블록의 프롬프트에 PDF 텍스트를 삽입합니다."""
    try:
        if not isinstance(block, dict):
            raise ValueError("블록 데이터가 올바르지 않습니다.")
        
        if not isinstance(pdf_text, str):
            pdf_text = str(pdf_text)

        def _safe_template(template: str, values: Dict[str, Any]) -> str:
            class _Safe(dict):
                def __missing__(self, key):
                    return ""
            return template.format_map(_Safe(values))
        
        # PDF 텍스트 길이 제한 (토큰 제한 고려)
        if len(pdf_text) > 8000:
            pdf_text = pdf_text[:8000] + "\n\n[내용이 길어 일부만 표시됩니다...]"
        
        # RISEN 구조 블록인지 확인
        if 'role' in block and 'instructions' in block and 'steps' in block:
            return _process_risen_prompt(block, pdf_text)
        else:
            fallback_template = block.get('prompt') or UNIFIED_PROMPT_TEMPLATE
            return _safe_template(fallback_template, {"pdf_text": pdf_text})
        
    except Exception as e:
        print(f"프롬프트 처리 중 예상치 못한 오류: {e}")
        fallback_template = block.get('prompt') or UNIFIED_PROMPT_TEMPLATE
        class _Safe(dict):
            def __missing__(self, key):
                return ""
        return fallback_template.format_map(_Safe({"pdf_text": pdf_text}))

def _process_risen_prompt(block: Dict[str, Any], pdf_text: str) -> str:
    """RISEN 구조의 프롬프트를 처리합니다."""
    try:
        # 단계들을 포맷팅
        steps_formatted = _format_steps(block.get('steps', []))
        
        # narrowing 객체 처리
        narrowing = block.get('narrowing', {}) or {}
        narrowing_formatted = _format_narrowing(narrowing)
        
        prompt_template = block.get('prompt') or UNIFIED_PROMPT_TEMPLATE
        
        def format_narrowing_value(value):
            if isinstance(value, list):
                return ", ".join(str(v) for v in value)
            return "" if value is None else str(value)

        format_payload = {
            "role": block.get('role', ''),
            "instructions": block.get('instructions', ''),
            "steps_formatted": steps_formatted,
            "end_goal": block.get('end_goal', ''),
            "pdf_text": pdf_text,
            "narrowing_formatted": narrowing_formatted,
            "block_name": block.get('name', ''),
            "block_description": block.get('description', '')
        }

        for key, value in narrowing.items():
            format_payload[f"narrowing_{key}"] = format_narrowing_value(value)

        format_payload.setdefault("narrowing_output_format", "")
        format_payload.setdefault("narrowing_constraints", "")
        format_payload.setdefault("narrowing_quality_standards", "")

        class _SafeFormatDict(dict):
            def __missing__(self, key):
                return ""

        formatted_prompt = prompt_template.format_map(_SafeFormatDict(format_payload))
        
        # 디버깅을 위한 출력 (개발 시에만)
        print(f"=== {block.get('id', 'unknown')} 블록 프롬프트 생성 완료 ===")
        print(f"블록 ID: {block.get('id', 'unknown')}")
        print(f"블록 이름: {block.get('name', 'unknown')}")
        print(f"프롬프트 길이: {len(formatted_prompt)}자")
        
        # 프롬프트의 핵심 부분들 출력
        if "역할 (Role)" in formatted_prompt:
            role_start = formatted_prompt.find("역할 (Role)")
            role_end = formatted_prompt.find("지시 (Instructions)", role_start)
            if role_end > role_start >= 0:
                role_text = formatted_prompt[role_start:role_end].strip()
                print(f"역할 섹션: {role_text[:100]}...")
        
        if "지시 (Instructions)" in formatted_prompt:
            inst_start = formatted_prompt.find("지시 (Instructions)")
            inst_end = formatted_prompt.find("단계 (Steps)", inst_start)
            if inst_end > inst_start >= 0:
                inst_text = formatted_prompt[inst_start:inst_end].strip()
                print(f"지시 섹션: {inst_text[:100]}...")
        
        # 프롬프트 해시 생성 (고유성 확인용)
        import hashlib
        prompt_hash = hashlib.md5(formatted_prompt.encode()).hexdigest()[:8]
        print(f"프롬프트 해시: {prompt_hash}")
        
        # 프롬프트가 제대로 생성되었는지 확인
        if "역할 (Role)" not in formatted_prompt:
            print("[ERROR] 프롬프트에 '역할 (Role):' 섹션이 없습니다!")
        if "지시 (Instructions)" not in formatted_prompt:
            print("[ERROR] 프롬프트에 '지시 (Instructions):' 섹션이 없습니다!")
        if "단계 (Steps)" not in formatted_prompt:
            print("[ERROR] 프롬프트에 '단계 (Steps):' 섹션이 없습니다!")
        
        print("프롬프트 구조 검증 완료")
        print("=" * 50)
        
        return formatted_prompt
        
    except Exception as e:
        print(f"RISEN 프롬프트 처리 오류: {e}")
        # 오류 발생 시 기본 프롬프트 반환
        base_prompt = block.get('prompt') or UNIFIED_PROMPT_TEMPLATE
        class _Safe(dict):
            def __missing__(self, key):
                return ""
        return base_prompt.format_map(_Safe({"pdf_text": pdf_text}))

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
    """사용자 정의 블록들을 로드합니다. blocks.json에서 created_by가 'user'인 블록들을 반환합니다."""
    try:
        # blocks.json에서 모든 블록 로드
        blocks = load_blocks()
        
        # created_by가 'user'인 블록만 필터링 (Block Generator로 생성된 블록)
        custom_blocks = [
            block for block in blocks 
            if isinstance(block, dict) and block.get('created_by') == 'user'
        ]
        
        return custom_blocks
    except Exception as e:
        print(f"사용자 정의 블록 로드 오류: {e}")
        return []

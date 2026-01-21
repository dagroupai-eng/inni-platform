import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path
from prompt_processor import load_blocks as load_blocks_from_processor

# 인증 및 블록 관리 모듈 import
try:
    from auth.authentication import is_authenticated, get_current_user, check_page_access
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False

try:
    from blocks.block_manager import (
        create_user_block,
        get_user_blocks,
        delete_user_block,
        BlockVisibility
    )
    BLOCKS_DB_AVAILABLE = True
except ImportError:
    BLOCKS_DB_AVAILABLE = False

def generate_dspy_signature(block_id, block_name, block_description):
    """블록 정보를 바탕으로 DSPy Signature 코드를 생성합니다."""
    
    # 블록 이름에서 Signature 클래스명 생성
    signature_name = ''.join(word.capitalize() for word in block_id.split('_')) + 'Signature'
    
    # 블록 설명을 기반으로 입력/출력 필드 설명 생성
    input_desc = f"{block_name}을 위한 입력 데이터"
    output_desc = f"{block_description}에 따른 분석 결과"
    
    # 문자열에서 줄바꿈과 따옴표 이스케이프 처리
    input_desc_escaped = input_desc.replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')
    output_desc_escaped = output_desc.replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')
    
    signature_code = f'''class {signature_name}(dspy.Signature):
    """{block_name}을 위한 Signature"""
    input = dspy.InputField(desc="{input_desc_escaped}")
    output = dspy.OutputField(desc="{output_desc_escaped}")'''
    
    return signature_code, signature_name

def update_dspy_analyzer(block_id, signature_code, signature_name):
    """dspy_analyzer.py 파일에 새로운 Signature를 추가합니다."""
    
    # dspy_analyzer.py 파일 경로 (명시적 경로 지정)
    current_file = Path(__file__)
    system_dir = current_file.parent.parent  # system/pages -> system
    analyzer_file = system_dir / 'dspy_analyzer.py'
    
    try:
        # 기존 파일 읽기
        with open(str(analyzer_file), 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 마지막 Signature 클래스를 찾아서 그 다음에 삽입
        import re
        # 모든 Signature 클래스 정의 찾기 (더 정확한 패턴)
        # class로 시작하고 Signature로 끝나는 클래스 정의 찾기
        signature_pattern = r'^class\s+\w+Signature\(dspy\.Signature\):'
        signature_matches = list(re.finditer(signature_pattern, content, re.MULTILINE))
        
        if signature_matches:
            # 마지막 Signature 클래스 찾기
            last_match = signature_matches[-1]
            last_match_start = last_match.start()
            
            # 마지막 Signature 클래스의 끝을 찾기 (다음 클래스 정의나 EnhancedArchAnalyzer까지)
            # 현재 위치부터 EnhancedArchAnalyzer까지 검색
            enhanced_analyzer_pos = content.find('\nclass EnhancedArchAnalyzer:', last_match_start)
            if enhanced_analyzer_pos == -1:
                enhanced_analyzer_pos = content.find('class EnhancedArchAnalyzer:', last_match_start)
            
            if enhanced_analyzer_pos > last_match_start:
                # 마지막 Signature 클래스와 EnhancedArchAnalyzer 사이의 위치
                insertion_point = enhanced_analyzer_pos
                
                # 빈 줄 확인 및 조정
                # insertion_point 이전의 공백/줄바꿈 확인
                before_insertion = content[:insertion_point].rstrip()
                # 마지막 줄바꿈 이후의 위치로 조정
                insertion_point = len(before_insertion)
                
                # 이미 빈 줄이 있는지 확인
                after_point = content[insertion_point:]
                if not after_point.startswith('\n\n'):
                    # 빈 줄 2개가 없으면 추가 (삽입 시 \n\n을 추가하므로 여기서는 확인만)
                    pass
            else:
                # EnhancedArchAnalyzer를 찾을 수 없으면 마지막 Signature 다음에 삽입
                # 마지막 Signature 클래스의 전체 내용 찾기
                next_class_pattern = r'^class\s+\w+(?:Signature\(dspy\.Signature\)|ArchAnalyzer):'
                next_match = re.search(next_class_pattern, content[last_match.end():], re.MULTILINE)
                if next_match:
                    insertion_point = last_match.end() + next_match.start()
                else:
                    insertion_point = last_match.end()
        else:
            # Signature 클래스를 찾을 수 없으면 EnhancedArchAnalyzer 앞에 삽입
            insertion_point = content.find('class EnhancedArchAnalyzer:')
            if insertion_point == -1:
                st.error("dspy_analyzer.py 파일에서 적절한 삽입 위치를 찾을 수 없습니다.")
                st.error("'class EnhancedArchAnalyzer:' 클래스를 찾을 수 없습니다. 파일 구조를 확인해주세요.")
                return False
        
        # 새로운 Signature 코드 삽입 (빈 줄 2개 포함)
        new_content = content[:insertion_point] + signature_code + '\n\n' + content[insertion_point:]
        
        # 참고: signature_map은 _build_signature_map() 메서드에서 동적으로 생성되므로
        # 하드코딩된 부분을 수정할 필요가 없습니다. 새로 생성된 Signature 클래스는
        # globals()를 통해 자동으로 발견되어 매핑됩니다.
        
        # 파일에 저장
        try:
            with open(str(analyzer_file), 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # 생성된 Signature 코드 검증 (기본적인 문법 체크)
            if signature_name not in new_content:
                st.warning(f"⚠️ 생성된 Signature 클래스 '{signature_name}'가 파일에 올바르게 추가되었는지 확인이 필요합니다.")
                st.warning("파일 저장은 완료되었지만, Signature 클래스 정의를 확인해주세요.")
                return False
            
            return True
            
        except IOError as e:
            st.error(f"파일 저장 중 오류 발생: {e}")
            st.error(f"파일 경로: {analyzer_file}")
            st.error("파일 쓰기 권한을 확인해주세요.")
            return False
        
    except FileNotFoundError:
        st.error(f"dspy_analyzer.py 파일을 찾을 수 없습니다: {analyzer_file}")
        st.error("파일 경로를 확인해주세요.")
        return False
    except Exception as e:
        st.error(f"dspy_analyzer.py 파일 업데이트 중 오류 발생: {e}")
        import traceback
        st.error("상세 오류 정보:")
        st.code(traceback.format_exc())
        return False

def remove_dspy_signature(block_id, signature_name):
    """dspy_analyzer.py 파일에서 Signature를 제거합니다."""
    
    # dspy_analyzer.py 파일 경로 (명시적 경로 지정)
    current_file = Path(__file__)
    system_dir = current_file.parent.parent  # system/pages -> system
    analyzer_file = system_dir / 'dspy_analyzer.py'
    
    try:
        # 기존 파일 읽기
        with open(str(analyzer_file), 'r', encoding='utf-8') as f:
            content = f.read()
        
        import re
        
        # Signature 클래스 제거 (더 강력한 방법)
        lines = content.split('\n')
        new_lines = []
        skip_lines = False
        
        for i, line in enumerate(lines):
            # 클래스 정의 라인 찾기
            if line.strip().startswith(f'class {signature_name}(dspy.Signature):'):
                skip_lines = True
                continue
            # 다음 클래스나 빈 줄을 만나면 스킵 중지
            elif skip_lines and (line.strip().startswith('class ') or (line.strip() == '' and i < len(lines) - 1 and lines[i+1].strip().startswith('class '))):
                skip_lines = False
                if line.strip().startswith('class '):
                    new_lines.append(line)
            # 스킵 중이 아닌 경우에만 라인 추가
            elif not skip_lines:
                new_lines.append(line)
        
        content = '\n'.join(new_lines)
        
        # 연속된 빈 줄 정리 (3개 이상 -> 2개로)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # signature_map에서 해당 블록 제거
        signature_map_pattern = r'signature_map = \{([^}]+)\}'
        match = re.search(signature_map_pattern, content, re.DOTALL)
        
        if match:
            map_content = match.group(1)
            # 해당 블록 라인 제거
            lines = map_content.split('\n')
            filtered_lines = [line for line in lines if f"'{block_id}'" not in line and line.strip()]
            
            # 딕셔너리 문법 수정: 마지막 항목의 쉼표 처리
            if filtered_lines:
                # 마지막 항목의 쉼표 제거
                last_line = filtered_lines[-1].rstrip()
                if last_line.endswith(','):
                    filtered_lines[-1] = last_line[:-1]
            
            updated_map_content = '\n'.join(filtered_lines)
            
            # signature_map 업데이트
            content = re.sub(
                signature_map_pattern,
                f'signature_map = {{{updated_map_content}\n}}',
                content,
                flags=re.DOTALL
            )
        
        # 파일에 저장
        with open(str(analyzer_file), 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        st.error(f"dspy_analyzer.py 파일에서 Signature 제거 중 오류 발생: {e}")
        return False

# load_blocks 함수는 prompt_processor에서 import하여 사용

# 블록 저장 함수
def save_blocks(blocks_data):
    """blocks.json 파일에 블록 데이터를 저장합니다."""
    # blocks.json 파일 경로 (명시적 경로 지정)
    current_file = Path(__file__)
    system_dir = current_file.parent.parent  # system/pages -> system
    blocks_file = system_dir / 'blocks.json'
    
    try:
        with open(str(blocks_file), 'w', encoding='utf-8') as f:
            json.dump(blocks_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"블록 데이터 저장 중 오류 발생: {e}")
        return False

# 블록 아이디 생성 함수
def generate_block_id(name):
    """블록 이름에서 ID를 생성합니다."""
    import re
    # 한글, 영문, 숫자, 공백을 제외한 특수문자 제거
    id_text = re.sub(r'[^\w\s가-힣]', '', name)
    # 공백을 언더스코어로 변경
    id_text = re.sub(r'\s+', '_', id_text)
    # 소문자로 변환
    return id_text.lower()

# frontend
def main():
    st.set_page_config(
        page_title="블록 생성기",
        page_icon=None,
        layout="wide"
    )

    # 세션 초기화 (로그인 + 작업 데이터 복원)
    try:
        from auth.session_init import init_page_session
        init_page_session()
    except Exception as e:
        print(f"세션 초기화 오류: {e}")

    # 로그인 체크
    if AUTH_AVAILABLE:
        check_page_access()

    st.title("분석 블록 생성기")
    st.markdown("---")
    
    # 기존 블록 로드 (prompt_processor의 함수 사용)
    existing_blocks = load_blocks_from_processor()  # 리스트 반환
    existing_categories = sorted({
        block.get("category")
        for block in existing_blocks
        if isinstance(block, dict) and block.get("category")
    })
    
    # 수정 모드 세션 상태 초기화
    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = False
    if 'edit_block_data' not in st.session_state:
        st.session_state.edit_block_data = None

    # 사이드바에 기존 블록 목록 표시
    with st.sidebar:
        st.header("기존 블록 목록")

        # 수정 모드 해제 버튼
        if st.session_state.edit_mode:
            st.info(f"📝 수정 중: {st.session_state.edit_block_data.get('name', '')}")
            if st.button("수정 취소", type="secondary"):
                st.session_state.edit_mode = False
                st.session_state.edit_block_data = None
                st.rerun()
            st.markdown("---")

        if existing_blocks:
            for i, block in enumerate(existing_blocks):
                block_name = block.get('name', 'Unknown')
                block_source = "🗄️ DB" if block.get('_db_id') else "📄 File"

                # 공개 범위 아이콘
                visibility = block.get('_visibility', 'personal')
                visibility_icons = {
                    'personal': '🔒',
                    'team': '👥',
                    'public': '🌐'
                }
                visibility_icon = visibility_icons.get(visibility, '🔒')

                with st.expander(f"{visibility_icon} {block_source} {block_name}"):
                    # 기본 정보
                    st.write(f"**ID:** {block.get('id', 'N/A')}")
                    st.write(f"**카테고리:** {block.get('category', '미지정')}")
                    st.write(f"**설명:** {block.get('description', 'N/A')}")

                    # 공개 범위 표시
                    visibility_labels = {
                        'personal': '나만 보기',
                        'team': '팀 공유',
                        'public': '전체 공개'
                    }
                    st.write(f"**공개 범위:** {visibility_labels.get(visibility, visibility)}")

                    # 블록 상세 보기 (RISEN 구조)
                    with st.expander("📋 상세 보기", expanded=False):
                        # Role
                        if block.get('role'):
                            st.markdown("**역할 (Role):**")
                            st.caption(block.get('role', ''))

                        # Instructions
                        if block.get('instructions'):
                            st.markdown("**지시 (Instructions):**")
                            st.caption(block.get('instructions', ''))

                        # Steps
                        if block.get('steps'):
                            st.markdown("**단계 (Steps):**")
                            for j, step in enumerate(block.get('steps', []), 1):
                                st.caption(f"{j}. {step}")

                        # End Goal
                        if block.get('end_goal'):
                            st.markdown("**최종 목표 (End Goal):**")
                            st.caption(block.get('end_goal', ''))

                        # Narrowing
                        narrowing = block.get('narrowing', {})
                        if narrowing:
                            st.markdown("**구체화/제약 조건 (Narrowing):**")
                            if narrowing.get('output_format'):
                                st.caption(f"• 출력 형식: {narrowing.get('output_format')}")
                            if narrowing.get('required_items'):
                                st.caption(f"• 필수 항목: {narrowing.get('required_items')}")
                            if narrowing.get('constraints'):
                                st.caption(f"• 제약 조건: {narrowing.get('constraints')}")
                            if narrowing.get('quality_standards'):
                                st.caption(f"• 품질 기준: {narrowing.get('quality_standards')}")
                            if narrowing.get('evaluation_criteria'):
                                st.caption(f"• 평가 기준: {narrowing.get('evaluation_criteria')}")
                            if narrowing.get('scoring_system'):
                                st.caption(f"• 점수 체계: {narrowing.get('scoring_system')}")

                        # 생성 정보
                        if block.get('created_at'):
                            st.caption(f"생성일: {block.get('created_at', '')[:10]}")

                    st.markdown("---")

                    # DB 블록이고 본인 소유인 경우 공개 범위 변경 가능
                    db_id = block.get('_db_id')
                    owner_id = block.get('_owner_id')

                    # 권한 체크 (본인 소유 여부)
                    is_owner = False
                    current_user_id = None

                    if AUTH_AVAILABLE:
                        try:
                            from auth.authentication import get_current_user_id
                            current_user_id = get_current_user_id()

                            if db_id:
                                # DB 블록: owner_id와 현재 사용자 ID 비교
                                if owner_id and current_user_id:
                                    is_owner = (str(owner_id) == str(current_user_id))
                                else:
                                    is_owner = False
                            else:
                                # JSON 블록: 소유권 확인 불가 - 수정 불가
                                # (JSON 블록은 로그인 시스템 도입 전 생성된 블록이므로 수정 권한 없음)
                                is_owner = False
                        except Exception as e:
                            # 인증 오류 시 수정 불가
                            is_owner = False
                    else:
                        # 인증 모듈 없으면 수정 불가
                        is_owner = False

                    # 수정 버튼 (권한 있는 경우만)
                    if is_owner:
                        col_edit, col_delete = st.columns(2)

                        with col_edit:
                            if st.button("✏️ 수정", key=f"edit_{i}"):
                                st.session_state.edit_mode = True
                                st.session_state.edit_block_data = block.copy()
                                st.session_state.edit_block_index = i
                                st.rerun()

                        with col_delete:
                            if st.button("🗑️ 삭제", key=f"delete_{i}"):
                                block_to_delete = existing_blocks[i]
                                block_id = block_to_delete.get('id')

                                delete_success = False

                                # DB 블록인 경우
                                if db_id and BLOCKS_DB_AVAILABLE:
                                    try:
                                        from blocks.block_manager import delete_user_block

                                        if delete_user_block(db_id, current_user_id):
                                            st.success(f"블록 '{block_name}'이 삭제되었습니다!")
                                            delete_success = True
                                        else:
                                            st.error("블록 삭제에 실패했습니다.")
                                    except Exception as e:
                                        st.error(f"삭제 오류: {e}")

                                # blocks.json 블록인 경우
                                else:
                                    signature_name = ''.join(word.capitalize() for word in block_id.split('_')) + 'Signature'

                                    json_blocks = []
                                    try:
                                        with open('blocks.json', 'r', encoding='utf-8') as f:
                                            data = json.load(f)
                                            json_blocks = data.get('blocks', [])
                                    except:
                                        pass

                                    json_blocks = [b for b in json_blocks if b.get('id') != block_id]
                                    blocks_data = {"blocks": json_blocks}

                                    if save_blocks(blocks_data):
                                        remove_dspy_signature(block_id, signature_name)
                                        st.success("블록이 삭제되었습니다!")
                                        delete_success = True
                                    else:
                                        st.error("블록 저장에 실패했습니다.")

                                if delete_success:
                                    st.rerun()

                        # 공개 범위 변경 (DB 블록이고 소유자인 경우)
                        if db_id and BLOCKS_DB_AVAILABLE:
                            new_visibility = st.selectbox(
                                "공개 범위",
                                options=['personal', 'team', 'public'],
                                format_func=lambda x: visibility_labels.get(x, x),
                                index=['personal', 'team', 'public'].index(visibility),
                                key=f"visibility_{i}"
                            )

                            if new_visibility != visibility:
                                if st.button("범위 변경", key=f"update_visibility_{i}"):
                                    try:
                                        from blocks.block_manager import update_user_block

                                        user = get_current_user()
                                        shared_teams = []
                                        if new_visibility == "team" and user and user.get("team_id"):
                                            shared_teams = [user["team_id"]]

                                        if update_user_block(
                                            db_id,
                                            current_user_id,
                                            visibility=new_visibility,
                                            shared_with_teams=shared_teams
                                        ):
                                            st.success("변경되었습니다!")
                                            st.rerun()
                                        else:
                                            st.error("변경 실패")
                                    except Exception as e:
                                        st.error(f"오류: {e}")
                    else:
                        # 권한 없는 경우 안내
                        if db_id:
                            st.caption("🔒 다른 사용자가 생성한 블록입니다")
                        else:
                            st.caption("🔒 기존 시스템 블록 (수정 불가)")
        else:
            st.info("생성된 블록이 없습니다.")
    
    # 메인 컨텐츠 영역
    col1, col2 = st.columns([2, 1])

    with col1:
        # 수정 모드 여부에 따라 헤더 변경
        if st.session_state.edit_mode and st.session_state.edit_block_data:
            st.header("📝 블록 수정")
            edit_block = st.session_state.edit_block_data
            st.info(f"수정 중인 블록: **{edit_block.get('name', '')}**")
        else:
            st.header("새 블록 생성")
            edit_block = None

        # 단계 개수 선택 (폼 밖에서 처리)
        st.markdown("**단계 개수 설정**")

        # 수정 모드일 때 기존 단계 수 사용
        default_steps = len(edit_block.get('steps', [])) if edit_block and edit_block.get('steps') else 3

        num_steps = st.number_input(
            "단계 개수",
            min_value=1,
            max_value=10,
            value=default_steps,
            key="num_steps",
            help="분석에 필요한 단계의 개수를 선택하세요"
        )

        # 블록 생성기 리셋 버튼 (폼 밖에 위치)
        if st.button("🔄 블록 생성기 리셋", help="모든 입력값을 초기화하고 기본 설정으로 돌아갑니다"):
            # 리셋 플래그 설정
            st.session_state['form_reset'] = True
            st.session_state.edit_mode = False
            st.session_state.edit_block_data = None
            st.rerun()

        # 블록 정보 입력 폼
        with st.form("block_creation_form"):
            # 리셋 플래그 확인 및 처리
            reset_form = st.session_state.get('form_reset', False)
            if reset_form:
                st.session_state['form_reset'] = False
                st.session_state.edit_mode = False
                st.session_state.edit_block_data = None
                # 모든 폼 관련 세션 상태 초기화
                for key in list(st.session_state.keys()):
                    if key.startswith(('step_', 'block_', 'role_', 'instructions_', 'end_goal_', 'output_format_', 'required_items_', 'constraints_', 'quality_standards_', 'evaluation_criteria_', 'scoring_system_', 'custom_id_', 'num_steps')):
                        del st.session_state[key]

            # 블록 이름 (수정 모드일 때 기존 값 표시)
            block_name = st.text_input(
                "블록 이름",
                placeholder="예: 도시 재개발 사회경제적 영향 분석",
                help="블록의 표시 이름을 입력하세요.",
                value=edit_block.get('name', '') if edit_block else ("" if reset_form else None)
            )
            
            # 블록 설명
            block_description = st.text_area(
                "블록 설명",
                placeholder="예: 도시 재개발 프로젝트의 사회경제적 영향을 종합적으로 분석하고 평가합니다",
                help="블록의 기능을 설명하는 간단한 문장을 입력하세요.",
                value=edit_block.get('description', '') if edit_block else ("" if reset_form else None)
            )
            
            category_prompt = "새 카테고리 입력"
            category_options = [category_prompt] + existing_categories

            # 수정 모드일 때 기존 카테고리 인덱스 찾기
            if edit_block and edit_block.get('category') in existing_categories:
                default_category_index = existing_categories.index(edit_block.get('category')) + 1
            else:
                default_category_index = 1 if len(category_options) > 1 else 0

            category_choice = st.selectbox(
                "카테고리",
                options=category_options,
                index=default_category_index,
                help="기존 카테고리를 선택하거나 새 카테고리를 입력하세요."
            )
            if category_choice == category_prompt:
                category_value = st.text_input(
                    "새 카테고리",
                    placeholder="예: Phase 1 · 후보지 분석",
                    help="블록을 묶을 새 카테고리를 직접 입력하세요."
                ).strip()
            else:
                category_value = category_choice.strip()
            
            # RISEN 구조 입력
            st.subheader("RISEN 프롬프트 구조")
            
            # Role (역할)
            role = st.text_area(
                "역할 (Role)",
                placeholder="도시 계획 전문가로서 도시 재개발 프로젝트의 사회경제적 영향을 종합적으로 분석하고 평가하는 역할을 수행합니다",
                height=80,
                help="AI가 수행할 전문가 역할을 정의해주세요.",
                value=edit_block.get('role', '') if edit_block else ("" if reset_form else None)
            )

            # Instructions (지시)
            instructions = st.text_area(
                "지시 (Instructions)",
                placeholder="제공된 도시 재개발 문서에서 사회경제적 영향 요인들을 식별하고, 긍정적/부정적 영향을 분류하며, 정량적 지표를 도출하여 종합 평가를 수행합니다",
                height=80,
                help="AI에게 수행해야 할 작업의 구체적인 지시사항을 작성해주세요.",
                value=edit_block.get('instructions', '') if edit_block else ("" if reset_form else None)
            )
            
            # Steps (단계)
            st.markdown("**단계 (Steps)**")

            # 수정 모드일 때 기존 단계 가져오기
            edit_steps = edit_block.get('steps', []) if edit_block else []

            # 단계 입력 필드들을 동적으로 생성
            steps = []
            for i in range(num_steps):
                # 수정 모드일 때 기존 값 사용
                if edit_block and i < len(edit_steps):
                    default_value = edit_steps[i]
                else:
                    default_value = "" if reset_form else None

                # 실제 예시 placeholder 설정
                if i == 0:
                    placeholder = "사회경제적 영향 요인 식별 - 문서에서 고용, 주거비, 상권 변화 등 관련 정보 추출"
                elif i == 1:
                    placeholder = "영향 분류 및 정량화 - 긍정적/부정적 영향을 구분하고 수치 데이터 정리"
                elif i == 2:
                    placeholder = "종합 평가 및 권고사항 도출 - 분석 결과를 바탕으로 개선 방안 제시"
                else:
                    placeholder = f"단계 {i+1} 내용 - 구체적 지시사항"

                step_text = st.text_input(
                    f"단계 {i+1}",
                    placeholder=placeholder,
                    key=f"step_{i}",
                    help=f"단계 {i+1}의 구체적인 내용을 입력하세요",
                    value=default_value
                )
                if step_text and step_text.strip():
                    steps.append(step_text.strip())
            
            # 단계 미리보기
            if steps:
                with st.expander("입력된 단계 미리보기", expanded=False):
                    for i, step in enumerate(steps, 1):
                        st.write(f"**{i}단계:** {step}")
            
            # 단계 개수 변경 안내
            if num_steps > 3:
                st.info(f"{num_steps}개의 단계를 설정했습니다. 각 단계를 구체적으로 작성해주세요.")
            
            # End Goal (최종 목표)
            end_goal = st.text_area(
                "최종 목표 (End Goal)",
                placeholder="도시 재개발 프로젝트의 사회경제적 영향을 체계적으로 분석하여 의사결정자들이 참고할 수 있는 종합적인 평가 보고서를 제공하고, 지속가능한 도시 발전을 위한 구체적인 권고사항을 제시합니다",
                height=80,
                help="이 분석을 통해 달성하고자 하는 최종 목표를 명시해주세요.",
                value=edit_block.get('end_goal', '') if edit_block else ("" if reset_form else None)
            )
            
            # Narrowing (구체화/제약 조건)
            st.markdown("**구체화/제약 조건 (Narrowing)**")

            # 수정 모드일 때 기존 narrowing 값 가져오기
            edit_narrowing = edit_block.get('narrowing', {}) if edit_block else {}

            col_narrowing1, col_narrowing2 = st.columns(2)

            with col_narrowing1:
                # 출력 형식
                default_output_format = edit_narrowing.get('output_format', '') if edit_block else ("" if reset_form else "표와 차트를 포함한 구조화된 보고서 + 각 표 하단에 상세 해설(4-8문장, 300-600자) + 모든 소제목별 서술형 설명(3-5문장, 200-400자) 필수")
                output_format = st.text_input(
                    "출력 형식",
                    value=default_output_format,
                    help="분석 결과의 출력 형식을 지정해주세요."
                )

                # 필수 항목
                default_required_items = edit_narrowing.get('required_items', '') if edit_block else ("" if reset_form else None)
                required_items = st.text_input(
                    "필수 항목/섹션",
                    placeholder="긍정적 영향, 부정적 영향, 정량적 지표, 개선 권고사항",
                    help="분석 결과에 반드시 포함되어야 할 항목들을 나열해주세요.",
                    value=default_required_items
                )

                # 제약 조건
                default_constraints = edit_narrowing.get('constraints', '') if edit_block else ("" if reset_form else "문서에 명시된 데이터만 사용, 추측 금지")
                constraints = st.text_input(
                    "제약 조건",
                    value=default_constraints,
                    help="분석 시 준수해야 할 제약 조건을 명시해주세요."
                )

            with col_narrowing2:
                # 품질 기준
                default_quality = edit_narrowing.get('quality_standards', '') if edit_block else ("" if reset_form else "각 결론에 근거 제시, 출처 명시 + 모든 표 하단에 상세 해설 필수 + 모든 소제목별 서술형 설명 필수 + 전체 분량 2000자 이상")
                quality_standards = st.text_input(
                    "품질 기준",
                    value=default_quality,
                    help="분석 결과의 품질 기준을 명시해주세요."
                )

                # 평가 기준
                default_eval = edit_narrowing.get('evaluation_criteria', '') if edit_block else ("" if reset_form else None)
                evaluation_criteria = st.text_input(
                    "평가 기준/분석 영역",
                    placeholder="고용, 주거비, 상권 변화, 교통, 환경, 사회적 영향",
                    help="평가나 분석의 기준이나 영역을 명시해주세요.",
                    value=default_eval
                )

                # 점수 체계
                default_scoring = edit_narrowing.get('scoring_system', '') if edit_block else ("" if reset_form else "정량적 지표 기반 영향도 평가 + 가중치 적용 종합 점수 산출")
                scoring_system = st.text_input(
                    "점수 체계/계산 방법",
                    value=default_scoring,
                    help="평가 점수 체계나 계산 방법을 명시해주세요."
                )
            
            # 고급 옵션
            with st.expander("고급 옵션"):
                # 수정 모드일 때는 기존 ID 표시 (수정 불가)
                if edit_block:
                    st.text_input(
                        "블록 ID (수정 불가)",
                        value=edit_block.get('id', ''),
                        disabled=True
                    )
                    custom_id = edit_block.get('id', '')
                else:
                    custom_id = st.text_input(
                        "커스텀 ID (선택사항)",
                        placeholder="자동 생성됩니다",
                        help="블록의 고유 ID를 직접 지정할 수 있습니다. 비워두면 이름에서 자동 생성됩니다.",
                        value="" if reset_form else None
                    )

                # 공개 범위 옵션 (로그인한 경우만)
                if AUTH_AVAILABLE and is_authenticated():
                    visibility_options = {
                        "personal": "나만 보기 (비공개)",
                        "team": "팀 공유",
                        "public": "전체 공개"
                    }
                    visibility = st.selectbox(
                        "공개 범위",
                        options=list(visibility_options.keys()),
                        format_func=lambda x: visibility_options[x],
                        index=0,
                        help="블록의 공개 범위를 설정합니다."
                    )
                else:
                    visibility = "personal"

            
            # 제출 버튼 (수정 모드에 따라 텍스트 변경)
            submit_label = "💾 블록 저장" if edit_block else "블록 생성"
            submitted = st.form_submit_button(submit_label, type="primary")

            if submitted:
                # 입력 검증
                if not block_name or not block_name.strip():
                    st.error("블록 이름을 입력해주세요.")
                elif not block_description or not block_description.strip():
                    st.error("블록 설명을 입력해주세요.")
                elif not category_value:
                    st.error("카테고리를 선택하거나 입력해주세요.")
                elif not role or not role.strip():
                    st.error("역할(Role)을 입력해주세요.")
                elif not instructions or not instructions.strip():
                    st.error("지시(Instructions)를 입력해주세요.")
                elif len(steps) == 0:
                    st.error("최소 하나의 단계를 입력해주세요.")
                elif not end_goal or not end_goal.strip():
                    st.error("최종 목표(End Goal)를 입력해주세요.")
                else:
                    # 수정 모드인 경우 기존 ID 사용
                    if edit_block:
                        block_id = edit_block.get('id')
                    elif custom_id and custom_id.strip():
                        block_id = custom_id.strip()
                    else:
                        block_id = generate_block_id(block_name)

                    # 블록 이름 그대로 사용
                    final_name = block_name

                    # 중복 ID 체크 (수정 모드가 아닐 때만)
                    existing_ids = [block.get('id') for block in existing_blocks]
                    if not edit_block and block_id in existing_ids:
                        st.error(f"ID '{block_id}'가 이미 존재합니다. 다른 이름을 사용하거나 커스텀 ID를 입력해주세요.")
                    else:
                        # narrowing 객체 구성
                        narrowing = {}
                        if output_format and output_format.strip():
                            narrowing['output_format'] = output_format.strip()
                        if required_items and required_items.strip():
                            narrowing['required_items'] = required_items.strip()
                        if constraints and constraints.strip():
                            narrowing['constraints'] = constraints.strip()
                        if quality_standards and quality_standards.strip():
                            narrowing['quality_standards'] = quality_standards.strip()
                        if evaluation_criteria and evaluation_criteria.strip():
                            narrowing['evaluation_criteria'] = evaluation_criteria.strip()
                        if scoring_system and scoring_system.strip():
                            narrowing['scoring_system'] = scoring_system.strip()
                        
                        # 블록 데이터 구성 (RISEN 구조)
                        updated_block = {
                            "id": block_id,
                            "name": final_name,
                            "description": block_description,
                            "category": category_value,
                            "role": role.strip(),
                            "instructions": instructions.strip(),
                            "steps": steps,
                            "end_goal": end_goal.strip(),
                            "narrowing": narrowing,
                            "updated_at": datetime.now().isoformat(),
                            "created_by": "user"
                        }

                        # 수정 모드일 때 기존 created_at 유지
                        if edit_block and edit_block.get('created_at'):
                            updated_block['created_at'] = edit_block.get('created_at')
                        else:
                            updated_block['created_at'] = datetime.now().isoformat()

                        # 저장 로직: 수정 모드와 생성 모드 분기
                        save_success = False
                        db_saved = False

                        # 수정 모드인 경우
                        if edit_block:
                            db_id = edit_block.get('_db_id')

                            # DB 블록 수정
                            if db_id and AUTH_AVAILABLE and BLOCKS_DB_AVAILABLE:
                                try:
                                    from blocks.block_manager import update_user_block
                                    from auth.authentication import get_current_user_id

                                    current_user_id = get_current_user_id()
                                    if current_user_id and update_user_block(
                                        db_id,
                                        current_user_id,
                                        name=final_name,
                                        block_data=updated_block,
                                        category=category_value
                                    ):
                                        save_success = True
                                        db_saved = True
                                        st.success(f"블록 '{final_name}'이 수정되었습니다!")
                                except Exception as e:
                                    st.error(f"블록 수정 오류: {e}")

                            # blocks.json 블록 수정
                            else:
                                json_blocks = []
                                try:
                                    with open('blocks.json', 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                        json_blocks = data.get('blocks', [])
                                except:
                                    pass

                                # 기존 블록 찾아서 업데이트
                                for idx, b in enumerate(json_blocks):
                                    if b.get('id') == block_id:
                                        json_blocks[idx] = updated_block
                                        break

                                blocks_data = {"blocks": json_blocks}
                                if save_blocks(blocks_data):
                                    save_success = True
                                    st.success(f"블록 '{final_name}'이 수정되었습니다!")

                            # 수정 모드 해제
                            if save_success:
                                st.session_state.edit_mode = False
                                st.session_state.edit_block_data = None
                                st.balloons()
                                st.rerun()

                        # 생성 모드인 경우
                        else:
                            # 로그인한 경우: DB에 저장
                            if AUTH_AVAILABLE and BLOCKS_DB_AVAILABLE and is_authenticated():
                                user = get_current_user()
                                if user:
                                    visibility_enum = BlockVisibility(visibility) if visibility else BlockVisibility.PERSONAL

                                    # 팀 공유인 경우 shared_with_teams에 현재 사용자의 팀 추가
                                    shared_teams = []
                                    if visibility == "team" and user.get("team_id"):
                                        shared_teams = [user["team_id"]]

                                    new_db_id = create_user_block(
                                        owner_id=user["id"],
                                        name=final_name,
                                        block_data=updated_block,
                                        category=category_value,
                                        visibility=visibility_enum,
                                        shared_with_teams=shared_teams,
                                        block_id=block_id
                                    )
                                    if new_db_id:
                                        save_success = True
                                        db_saved = True
                                        st.success(f"블록 '{final_name}'이 데이터베이스에 저장되었습니다!")
                                        visibility_msg = {"personal": "나만 볼 수 있음", "team": "팀 공유됨", "public": "전체 공개됨"}
                                        st.info(f"공개 범위: {visibility_msg.get(visibility, visibility)}")

                            # 비로그인 또는 DB 저장 실패: blocks.json에 저장
                            if not save_success:
                                existing_blocks.append(updated_block)
                                blocks_data = {"blocks": existing_blocks}
                                if save_blocks(blocks_data):
                                    save_success = True

                            if save_success:
                                # DSPy Signature 자동 생성 (blocks.json 저장 시에만)
                                signature_code = None
                                signature_name = None

                                if not db_saved:
                                    signature_code, signature_name = generate_dspy_signature(
                                        block_id, final_name, block_description
                                    )

                                    # dspy_analyzer.py 파일 업데이트
                                    if update_dspy_analyzer(block_id, signature_code, signature_name):
                                        st.success(f"블록 '{final_name}'이 성공적으로 생성되었습니다!")
                                        st.success(f"DSPy Signature '{signature_name}'도 자동으로 생성되었습니다!")
                                    else:
                                        st.success(f"블록 '{final_name}'이 성공적으로 생성되었습니다!")
                                        st.warning("DSPy Signature 자동 생성에 실패했습니다.")
                                else:
                                    st.success(f"블록 '{final_name}'이 데이터베이스에 저장되었습니다!")

                                st.balloons()

                                # 생성된 블록 정보 표시
                                with st.expander("생성된 블록 정보", expanded=True):
                                    st.json(updated_block)

                                # 생성된 DSPy Signature 코드 표시 (blocks.json 저장 시에만)
                                if signature_code:
                                    with st.expander("생성된 DSPy Signature", expanded=False):
                                        st.code(signature_code, language="python")

                                # 사이드바 새로고침을 위해 rerun
                                st.rerun()
                            else:
                                st.error("블록 저장 중 오류가 발생했습니다.")
    
    with col2:
        st.header("도움말")
        
        st.markdown("""
        ### RISEN 프롬프트 구조 가이드
        
        **RISEN이란?**
        - **R**ole (역할): AI가 수행할 전문가 역할
        - **I**nstructions (지시): 구체적인 작업 지시사항
        - **S**teps (단계): 단계별 분석 과정
        - **E**nd Goal (최종 목표): 달성하고자 하는 결과
        - **N**arrowing (구체화): 제약조건 및 출력 형식
        
        **🔧 자동 DSPy Signature 생성**
        - 새 블록 생성 시 자동으로 DSPy Signature 클래스가 생성됩니다
        - 블록 ID를 기반으로 고유한 Signature 클래스명이 생성됩니다
        - 예: `my_analysis` → `MyAnalysisSignature`
        - 삭제 시에도 자동으로 Signature가 제거됩니다
        
        **1. 역할 (Role) - 전문가 역할 정의**
        ```
        ✅ 좋은 예시:
        "도시 계획 전문가로서 도시 재개발 프로젝트의 사회경제적 영향을 종합적으로 분석하고 평가하는 역할을 수행합니다"
        
        ❌ 나쁜 예시:
        "분석 전문가"
        ```
        
        **2. 지시 (Instructions) - 구체적인 작업 지시**
        ```
        ✅ 좋은 예시:
        "제공된 도시 재개발 문서에서 사회경제적 영향 요인들을 식별하고, 긍정적/부정적 영향을 분류하며, 정량적 지표를 도출하여 종합 평가를 수행합니다"
        
        ❌ 나쁜 예시:
        "문서를 분석하세요"
        ```
        
        **3. 단계 (Steps) - 논리적 분석 과정**
        ```
        ✅ 좋은 예시:
        1. "사회경제적 영향 요인 식별 - 문서에서 고용, 주거비, 상권 변화 등 관련 정보 추출"
        2. "영향 분류 및 정량화 - 긍정적/부정적 영향을 구분하고 수치 데이터 정리"
        3. "종합 평가 및 권고사항 도출 - 분석 결과를 바탕으로 개선 방안 제시"
        
        ❌ 나쁜 예시:
        1. "분석하기"
        2. "결과 만들기"
        ```
        
        **4. 최종 목표 (End Goal) - 달성하고자 하는 결과**
        ```
        ✅ 좋은 예시:
        "도시 재개발 프로젝트의 사회경제적 영향을 체계적으로 분석하여 의사결정자들이 참고할 수 있는 종합적인 평가 보고서를 제공하고, 지속가능한 도시 발전을 위한 구체적인 권고사항을 제시합니다"
        
        ❌ 나쁜 예시:
        "분석 결과를 제공합니다"
        ```
        
        **5. 구체화/제약 조건 (Narrowing) - 출력 형식 및 기준**
        ```
        ✅ 좋은 예시:
        - 출력 형식: "표와 차트를 포함한 구조화된 보고서"
        - 필수 항목: "긍정적 영향, 부정적 영향, 정량적 지표, 개선 권고사항"
        - 제약 조건: "문서에 명시된 데이터만 사용, 추측 금지"
        - 품질 기준: "각 결론에 근거 제시, 출처 명시"
        
        ❌ 나쁜 예시:
        - 출력 형식: "보고서"
        - 필수 항목: "결과"
        ```
        """)
        
        st.markdown("---")
        
        st.subheader("📖 실제 사용 예시")
        
        with st.expander("도시 재개발 프로젝트 분석 예시"):
            st.markdown("""
            **블록 이름:** 도시 재개발 사회경제적 영향 분석
            
            **역할 (Role):**
            도시 계획 전문가로서 도시 재개발 프로젝트의 사회경제적 영향을 종합적으로 분석하고 평가하는 역할을 수행합니다
            
            **지시 (Instructions):**
            제공된 도시 재개발 문서에서 사회경제적 영향 요인들을 식별하고, 긍정적/부정적 영향을 분류하며, 정량적 지표를 도출하여 종합 평가를 수행합니다
            
            **단계 (Steps):**
            1. 사회경제적 영향 요인 식별 - 문서에서 고용, 주거비, 상권 변화 등 관련 정보 추출
            2. 영향 분류 및 정량화 - 긍정적/부정적 영향을 구분하고 수치 데이터 정리
            3. 종합 평가 및 권고사항 도출 - 분석 결과를 바탕으로 개선 방안 제시
            
            **최종 목표 (End Goal):**
            도시 재개발 프로젝트의 사회경제적 영향을 체계적으로 분석하여 의사결정자들이 참고할 수 있는 종합적인 평가 보고서를 제공하고, 지속가능한 도시 발전을 위한 구체적인 권고사항을 제시합니다
            
            **구체화/제약 조건 (Narrowing):**
            - 출력 형식: 표와 차트를 포함한 구조화된 보고서
            - 필수 항목: 긍정적 영향, 부정적 영향, 정량적 지표, 개선 권고사항
            - 제약 조건: 문서에 명시된 데이터만 사용, 추측 금지
            - 품질 기준: 각 결론에 근거 제시, 출처 명시
            """)
        
        with st.expander("환경 영향 평가 예시"):
            st.markdown("""
            **블록 이름:** 도시 프로젝트 환경 영향 평가
            
            **역할 (Role):**
            환경 전문가로서 도시 개발 프로젝트가 지역 환경에 미치는 영향을 과학적이고 객관적으로 평가하는 역할을 수행합니다
            
            **지시 (Instructions):**
            제공된 도시 개발 문서에서 환경 관련 정보를 추출하고, 대기질, 수질, 생태계, 소음 등 다양한 환경 요소별로 영향을 분석하여 종합적인 환경 평가를 수행합니다
            
            **단계 (Steps):**
            1. 환경 영향 요소 식별 - 대기, 수질, 토양, 생태계, 소음 등 영향 요소 파악
            2. 영향 정도 평가 - 각 환경 요소별 영향의 규모와 심각도 분석
            3. 완화 방안 도출 - 부정적 환경 영향을 최소화할 수 있는 대안 제시
            
            **최종 목표 (End Goal):**
            도시 개발 프로젝트의 환경적 지속가능성을 확보할 수 있도록 환경 영향 평가 결과를 제공하고, 친환경적인 개발 방향을 제시합니다
            
            **구체화/제약 조건 (Narrowing):**
            - 출력 형식: 환경 영향 매트릭스와 개선 방안 목록
            - 필수 항목: 영향 요소별 분석, 영향 정도 평가, 완화 방안
            - 제약 조건: 객관적 데이터 기반 평가, 환경 기준 준수
            - 품질 기준: 환경 법규 및 기준 참조, 전문가 의견 반영
            """)
        
        with st.expander("교통 영향 분석 예시"):
            st.markdown("""
            **블록 이름:** 도시 프로젝트 교통 영향 분석
            
            **역할 (Role):**
            교통 전문가로서 도시 개발 프로젝트가 지역 교통 체계에 미치는 영향을 분석하고 교통 개선 방안을 제시하는 역할을 수행합니다
            
            **지시 (Instructions):**
            제공된 도시 개발 문서에서 교통 관련 정보를 분석하고, 교통량 변화, 접근성 개선, 교통 혼잡도 등 다양한 교통 요소를 평가하여 종합적인 교통 영향 분석을 수행합니다
            
            **단계 (Steps):**
            1. 교통 현황 파악 - 기존 교통 인프라 및 교통량 분석
            2. 개발 영향 평가 - 프로젝트로 인한 교통량 변화 및 접근성 변화 분석
            3. 교통 개선 방안 제시 - 교통 혼잡 완화 및 접근성 향상 방안 도출
            
            **최종 목표 (End Goal):**
            도시 개발 프로젝트가 지역 교통 체계에 미치는 영향을 체계적으로 분석하여 교통 효율성을 높이고 주민들의 이동 편의성을 개선할 수 있는 구체적인 교통 개선 방안을 제시합니다
            
            **구체화/제약 조건 (Narrowing):**
            - 출력 형식: 교통 영향 분석표와 개선 방안 도표
            - 필수 항목: 교통량 변화, 접근성 분석, 혼잡도 평가, 개선 방안
            - 제약 조건: 교통 데이터 기반 분석, 현실적 개선 방안
            - 품질 기준: 교통 전문 지식 반영, 실현 가능성 검토
            """)
        
        st.markdown("---")
        
        st.subheader("📝 작성 가이드라인")
        
        st.markdown("""
        ### ✅ 효과적인 블록 작성 팁
        
        **1. 구체적이고 명확하게 작성하세요**
        - 모호한 표현보다는 구체적인 용어 사용
        - "분석하세요" → "식별하고 분류하며 평가하세요"
        
        **2. 도시 프로젝트에 특화된 내용으로 작성하세요**
        - 건축 중심이 아닌 도시 계획 관점에서 접근
        - 사회적, 경제적, 환경적 영향 고려
        
        **3. 단계는 논리적 순서로 구성하세요**
        - 정보 수집 → 분석 → 평가 → 결론 도출
        - 각 단계가 다음 단계의 기반이 되도록
        
        **4. 출력 형식을 구체적으로 명시하세요**
        - "보고서" → "표와 차트를 포함한 구조화된 보고서"
        - "분석 결과" → "긍정적/부정적 영향 분석표와 개선 권고사항"
        
        **5. 제약 조건을 명확히 하세요**
        - 문서 기반 분석인지, 추가 조사가 필요한지
        - 추측이나 가정의 범위 설정
        
        ### ❌ 피해야 할 표현들
        
        - "분석하세요", "검토하세요" (너무 일반적)
        - "자세히", "구체적으로" (구체성이 부족)
        - "적절한", "합리적인" (기준이 모호)
        - "가능한 한", "최대한" (범위가 불분명)
        """)

if __name__ == "__main__":
    main()

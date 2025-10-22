import streamlit as st
import json
import os
from datetime import datetime

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
    
    # dspy_analyzer.py 파일 경로
    analyzer_file = 'dspy_analyzer.py'
    
    try:
        # 기존 파일 읽기
        with open(analyzer_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Signature 클래스들을 찾을 위치 (SimpleAnalysisSignature 다음)
        insertion_point = content.find('class EnhancedArchAnalyzer:')
        
        if insertion_point == -1:
            st.error("dspy_analyzer.py 파일에서 적절한 삽입 위치를 찾을 수 없습니다.")
            return False
        
        # 새로운 Signature 코드 삽입
        new_content = content[:insertion_point] + signature_code + '\n\n' + content[insertion_point:]
        
        # signature_map에 새 블록 추가
        signature_map_pattern = r'signature_map = \{([^}]+)\}'
        import re
        match = re.search(signature_map_pattern, new_content, re.DOTALL)
        
        if match:
            # 기존 signature_map 내용
            map_content = match.group(1)
            
            # 기존 내용에서 마지막 쉼표 확인 및 추가
            map_content_stripped = map_content.rstrip()
            if not map_content_stripped.endswith(','):
                # 마지막 항목에 쉼표가 없으면 추가
                map_content_stripped += ','
            
            # 새 블록 추가 (항상 쉼표 포함)
            new_map_entry = f"                '{block_id}': {signature_name},"
            updated_map_content = map_content_stripped + '\n' + new_map_entry + '\n'
            
            # signature_map 업데이트
            new_content = re.sub(
                signature_map_pattern,
                f'signature_map = {{{updated_map_content}}}',
                new_content,
                flags=re.DOTALL
            )
        
        # 파일에 저장
        with open(analyzer_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
        
    except Exception as e:
        st.error(f"dspy_analyzer.py 파일 업데이트 중 오류 발생: {e}")
        return False

def remove_dspy_signature(block_id, signature_name):
    """dspy_analyzer.py 파일에서 Signature를 제거합니다."""
    
    analyzer_file = 'dspy_analyzer.py'
    
    try:
        # 기존 파일 읽기
        with open(analyzer_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        import re
        
        # Signature 클래스 제거
        signature_pattern = rf'class {signature_name}\(dspy\.Signature\):[^}}]+}}\n\n'
        content = re.sub(signature_pattern, '', content, flags=re.DOTALL)
        
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
        with open(analyzer_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        st.error(f"dspy_analyzer.py 파일에서 Signature 제거 중 오류 발생: {e}")
        return False

def load_blocks():
    """blocks.json 파일에서 블록 데이터를 로드합니다."""
    try:
        with open('blocks.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"blocks": []}
    except Exception as e:
        st.error(f"블록 데이터 로드 중 오류 발생: {e}")
        return {"blocks": []}

def save_blocks(blocks_data):
    """blocks.json 파일에 블록 데이터를 저장합니다."""
    try:
        with open('blocks.json', 'w', encoding='utf-8') as f:
            json.dump(blocks_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"블록 데이터 저장 중 오류 발생: {e}")
        return False

def generate_block_id(name):
    """블록 이름에서 ID를 생성합니다."""
    import re
    # 한글, 영문, 숫자, 공백을 제외한 특수문자 제거
    id_text = re.sub(r'[^\w\s가-힣]', '', name)
    # 공백을 언더스코어로 변경
    id_text = re.sub(r'\s+', '_', id_text)
    # 소문자로 변환
    return id_text.lower()

def main():
    st.set_page_config(
        page_title="블록 생성기",
        page_icon=None,
        layout="wide"
    )
    
    st.title("분석 블록 생성기")
    st.markdown("---")
    
    # 기존 블록 로드
    blocks_data = load_blocks()
    existing_blocks = blocks_data.get("blocks", [])
    
    # 사이드바에 기존 블록 목록 표시
    with st.sidebar:
        st.header("기존 블록 목록")
        if existing_blocks:
            for i, block in enumerate(existing_blocks):
                with st.expander(f"{block.get('name', 'Unknown')}"):
                    st.write(f"**ID:** {block.get('id', 'N/A')}")
                    st.write(f"**설명:** {block.get('description', 'N/A')}")
                    if st.button(f"삭제", key=f"delete_{i}"):
                        # 삭제할 블록 정보
                        block_to_delete = existing_blocks[i]
                        block_id = block_to_delete.get('id')
                        block_name = block_to_delete.get('name')
                        
                        # Signature 이름 생성
                        signature_name = ''.join(word.capitalize() for word in block_id.split('_')) + 'Signature'
                        
                        # 블록 삭제
                        existing_blocks.pop(i)
                        blocks_data["blocks"] = existing_blocks
                        
                        if save_blocks(blocks_data):
                            # DSPy Signature도 제거
                            if remove_dspy_signature(block_id, signature_name):
                                st.success("블록과 DSPy Signature가 삭제되었습니다!")
                            else:
                                st.success("블록이 삭제되었습니다!")
                                st.warning("DSPy Signature 제거에 실패했습니다. 수동으로 제거해주세요.")
                            st.rerun()
        else:
            st.info("생성된 블록이 없습니다.")
    
    # 메인 컨텐츠 영역
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("새 블록 생성")
        
        # 단계 업데이트 버튼 (폼 밖에 위치)
        if st.button("단계 필드 새로고침", help="단계 개수를 변경한 후 이 버튼을 클릭하세요"):
            st.rerun()
        
        # 블록 정보 입력 폼
        with st.form("block_creation_form"):
            # 블록 이름
            block_name = st.text_input(
                "블록 이름",
                placeholder="예: 도시 재개발 사회경제적 영향 분석",
                help="블록의 표시 이름을 입력하세요."
            )
            
            # 블록 설명
            block_description = st.text_area(
                "블록 설명",
                placeholder="예: 도시 재개발 프로젝트의 사회경제적 영향을 종합적으로 분석하고 평가합니다",
                help="블록의 기능을 설명하는 간단한 문장을 입력하세요."
            )
            
            # RISEN 구조 입력
            st.subheader("RISEN 프롬프트 구조")
            
            # Role (역할)
            role = st.text_area(
                "역할 (Role)",
                placeholder="도시 계획 전문가로서 도시 재개발 프로젝트의 사회경제적 영향을 종합적으로 분석하고 평가하는 역할을 수행합니다",
                height=80,
                help="AI가 수행할 전문가 역할을 정의해주세요."
            )
            
            # Instructions (지시)
            instructions = st.text_area(
                "지시 (Instructions)",
                placeholder="제공된 도시 재개발 문서에서 사회경제적 영향 요인들을 식별하고, 긍정적/부정적 영향을 분류하며, 정량적 지표를 도출하여 종합 평가를 수행합니다",
                height=80,
                help="AI에게 수행해야 할 작업의 구체적인 지시사항을 작성해주세요."
            )
            
            # Steps (단계)
            st.markdown("**단계 (Steps)**")
            
            # 단계 개수 선택
            num_steps = st.number_input(
                "단계 개수", 
                min_value=1, 
                max_value=10, 
                value=3, 
                key="num_steps",
                help="분석에 필요한 단계의 개수를 선택하세요"
            )
            
            # 단계 입력 필드들을 동적으로 생성
            steps = []
            for i in range(num_steps):
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
                    help=f"단계 {i+1}의 구체적인 내용을 입력하세요"
                )
                if step_text.strip():
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
                help="이 분석을 통해 달성하고자 하는 최종 목표를 명시해주세요."
            )
            
            # Narrowing (구체화/제약 조건)
            st.markdown("**구체화/제약 조건 (Narrowing)**")
            
            col_narrowing1, col_narrowing2 = st.columns(2)
            
            with col_narrowing1:
                output_format = st.text_input(
                    "출력 형식",
                    value="표와 차트를 포함한 구조화된 보고서 + 각 표 하단에 상세 해설(4-8문장, 300-600자) + 모든 소제목별 서술형 설명(3-5문장, 200-400자) 필수",
                    help="분석 결과의 출력 형식을 지정해주세요."
                )
                
                required_items = st.text_input(
                    "필수 항목/섹션",
                    placeholder="긍정적 영향, 부정적 영향, 정량적 지표, 개선 권고사항",
                    help="분석 결과에 반드시 포함되어야 할 항목들을 나열해주세요."
                )
                
                constraints = st.text_input(
                    "제약 조건",
                    value="문서에 명시된 데이터만 사용, 추측 금지",
                    help="분석 시 준수해야 할 제약 조건을 명시해주세요."
                )
            
            with col_narrowing2:
                quality_standards = st.text_input(
                    "품질 기준",
                    value="각 결론에 근거 제시, 출처 명시 + 모든 표 하단에 상세 해설 필수 + 모든 소제목별 서술형 설명 필수 + 전체 분량 2000자 이상",
                    help="분석 결과의 품질 기준을 명시해주세요."
                )
                
                evaluation_criteria = st.text_input(
                    "평가 기준/분석 영역",
                    placeholder="고용, 주거비, 상권 변화, 교통, 환경, 사회적 영향",
                    help="평가나 분석의 기준이나 영역을 명시해주세요."
                )
                
                scoring_system = st.text_input(
                    "점수 체계/계산 방법",
                    value="정량적 지표 기반 영향도 평가 + 가중치 적용 종합 점수 산출",
                    help="평가 점수 체계나 계산 방법을 명시해주세요."
                )
            
            # 고급 옵션
            with st.expander("고급 옵션"):
                custom_id = st.text_input(
                    "커스텀 ID (선택사항)",
                    placeholder="자동 생성됩니다",
                    help="블록의 고유 ID를 직접 지정할 수 있습니다. 비워두면 이름에서 자동 생성됩니다."
                )
                
            
            # 제출 버튼
            submitted = st.form_submit_button("블록 생성", type="primary")
            
            if submitted:
                # 입력 검증
                if not block_name.strip():
                    st.error("블록 이름을 입력해주세요.")
                elif not block_description.strip():
                    st.error("블록 설명을 입력해주세요.")
                elif not role.strip():
                    st.error("역할(Role)을 입력해주세요.")
                elif not instructions.strip():
                    st.error("지시(Instructions)를 입력해주세요.")
                elif len(steps) == 0:
                    st.error("최소 하나의 단계를 입력해주세요.")
                elif not end_goal.strip():
                    st.error("최종 목표(End Goal)를 입력해주세요.")
                else:
                    # 블록 ID 생성
                    if custom_id.strip():
                        block_id = custom_id.strip()
                    else:
                        block_id = generate_block_id(block_name)
                    
                    # 블록 이름 그대로 사용
                    final_name = block_name
                    
                    # 중복 ID 체크
                    existing_ids = [block.get('id') for block in existing_blocks]
                    if block_id in existing_ids:
                        st.error(f"ID '{block_id}'가 이미 존재합니다. 다른 이름을 사용하거나 커스텀 ID를 입력해주세요.")
                    else:
                        # narrowing 객체 구성
                        narrowing = {}
                        if output_format.strip():
                            narrowing['output_format'] = output_format.strip()
                        if required_items.strip():
                            narrowing['required_items'] = required_items.strip()
                        if constraints.strip():
                            narrowing['constraints'] = constraints.strip()
                        if quality_standards.strip():
                            narrowing['quality_standards'] = quality_standards.strip()
                        if evaluation_criteria.strip():
                            narrowing['evaluation_criteria'] = evaluation_criteria.strip()
                        if scoring_system.strip():
                            narrowing['scoring_system'] = scoring_system.strip()
                        
                        # 간단한 프롬프트 템플릿 생성 (blocks.json과 동일한 구조)
                        prompt_template = "**역할 (Role):** {role}\n\n**지시 (Instructions):** {instructions}\n\n**반드시 다음 단계를 순서대로 수행하세요:**\n{steps_formatted}\n\n**최종 목표 (End Goal):** {end_goal}\n\n**구체화/제약 조건 (Narrowing):**\n- **출력 형식:** {narrowing_output_format}\n- **분류 기준:** {narrowing_classification_criteria}\n- **평가 척도:** {narrowing_evaluation_scale}\n- **제약 조건:** {narrowing_constraints}\n- **품질 기준:** {narrowing_quality_standards}\n\n**중요:** 위의 단계들을 순서대로 수행하여 분석 결과를 제시하세요.\n\n**분석할 문서 내용:**\n{pdf_text}"
                        
                        # 새 블록 생성 (RISEN 구조)
                        new_block = {
                            "id": block_id,
                            "name": final_name,
                            "description": block_description,
                            "role": role.strip(),
                            "instructions": instructions.strip(),
                            "steps": steps,
                            "end_goal": end_goal.strip(),
                            "narrowing": narrowing,
                            "prompt": prompt_template,
                            "created_at": datetime.now().isoformat(),
                            "created_by": "user"
                        }
                        
                        # 블록 추가
                        existing_blocks.append(new_block)
                        blocks_data["blocks"] = existing_blocks
                        
                        # 저장
                        if save_blocks(blocks_data):
                            # DSPy Signature 자동 생성
                            signature_code, signature_name = generate_dspy_signature(
                                block_id, final_name, block_description
                            )
                            
                            # dspy_analyzer.py 파일 업데이트
                            if update_dspy_analyzer(block_id, signature_code, signature_name):
                                st.success(f"블록 '{final_name}'이 성공적으로 생성되었습니다!")
                                st.success(f"DSPy Signature '{signature_name}'도 자동으로 생성되었습니다!")
                                st.balloons()
                            else:
                                st.success(f"블록 '{final_name}'이 성공적으로 생성되었습니다!")
                                st.warning("DSPy Signature 자동 생성에 실패했습니다. 수동으로 추가해주세요.")
                            
                            # 생성된 블록 정보 표시
                            with st.expander("생성된 블록 정보", expanded=True):
                                st.json(new_block)
                            
                            # 생성된 DSPy Signature 코드 표시
                            with st.expander("생성된 DSPy Signature", expanded=False):
                                st.code(signature_code, language="python")
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

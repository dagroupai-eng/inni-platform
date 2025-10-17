import streamlit as st
import json
import os
from datetime import datetime

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
                        # 블록 삭제
                        existing_blocks.pop(i)
                        blocks_data["blocks"] = existing_blocks
                        if save_blocks(blocks_data):
                            st.success("블록이 삭제되었습니다!")
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
                placeholder="예: 건축 요구사항 분석 (CoT)",
                help="블록의 표시 이름을 입력하세요."
            )
            
            # 블록 설명
            block_description = st.text_area(
                "블록 설명",
                placeholder="예: Chain of Thought로 건축 관련 요구사항을 분석하고 정리합니다",
                help="블록의 기능을 설명하는 간단한 문장을 입력하세요."
            )
            
            # RISEN 구조 입력
            st.subheader("RISEN 프롬프트 구조")
            
            # Role (역할)
            role = st.text_area(
                "역할 (Role)",
                placeholder="건축 설계 전문가로서 프로젝트의 모든 요구사항을 종합적으로 분석하고 우선순위를 설정하는 역할을 수행합니다",
                height=80,
                help="AI가 수행할 전문가 역할을 정의해주세요."
            )
            
            # Instructions (지시)
            instructions = st.text_area(
                "지시 (Instructions)",
                placeholder="제공된 문서에서 건축 프로젝트의 모든 요구사항을 식별하고, 분류하며, 우선순위를 평가하여 설계 방향을 제시합니다",
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
                    placeholder = "요구사항 식별 및 수집 - 문서에서 명시적/암시적 요구사항 모두 식별"
                elif i == 1:
                    placeholder = "요구사항 상세 분석 - 각 요구사항의 구체적 내용 및 기준 명확화"
                elif i == 2:
                    placeholder = "우선순위 평가 및 순위화 - 중요도, 긴급도, 실행 가능성 기준으로 평가"
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
                placeholder="설계팀이 참고할 수 있는 완전하고 우선순위가 명확한 요구사항 목록을 제공하여 효율적인 설계 의사결정을 지원합니다",
                height=80,
                help="이 분석을 통해 달성하고자 하는 최종 목표를 명시해주세요."
            )
            
            # Narrowing (구체화/제약 조건)
            st.markdown("**구체화/제약 조건 (Narrowing)**")
            
            col_narrowing1, col_narrowing2 = st.columns(2)
            
            with col_narrowing1:
                output_format = st.text_input(
                    "출력 형식",
                    placeholder="요구사항 매트릭스 표 + 우선순위 도표",
                    help="분석 결과의 출력 형식을 지정해주세요."
                )
                
                required_items = st.text_input(
                    "필수 항목/섹션",
                    placeholder="프로젝트명, 건축주, 대지위치, 건물용도, 주요 요구사항",
                    help="분석 결과에 반드시 포함되어야 할 항목들을 나열해주세요."
                )
                
                constraints = st.text_input(
                    "제약 조건",
                    placeholder="문서에 명시되지 않은 정보는 추측하지 말고 '정보 없음'으로 표시",
                    help="분석 시 준수해야 할 제약 조건을 명시해주세요."
                )
            
            with col_narrowing2:
                quality_standards = st.text_input(
                    "품질 기준",
                    placeholder="각 정보의 출처(문서 내 위치)를 명시",
                    help="분석 결과의 품질 기준을 명시해주세요."
                )
                
                evaluation_criteria = st.text_input(
                    "평가 기준/분석 영역",
                    placeholder="공간/기능/법적/기술적/경제적 요구사항",
                    help="평가나 분석의 기준이나 영역을 명시해주세요."
                )
                
                scoring_system = st.text_input(
                    "점수 체계/계산 방법",
                    placeholder="1-5점 척도로 중요도 및 긴급도 평가",
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
                        
                        # 프롬프트 템플릿 생성
                        prompt_template = f"""**역할 (Role):** {role}

**지시 (Instructions):** {instructions}

**단계 (Steps):**
{chr(10).join([f"{i+1}. **{step}**" for i, step in enumerate(steps)])}

**최종 목표 (End Goal):** {end_goal}

**구체화/제약 조건 (Narrowing):**
{chr(10).join([f"- **{key.replace('_', ' ').title()}:** {value}" for key, value in narrowing.items()])}

**분석할 문서 내용:**
{{pdf_text}}"""
                        
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
                            st.success(f"블록 '{final_name}'이 성공적으로 생성되었습니다!")
                            st.balloons()
                            
                            # 생성된 블록 정보 표시
                            with st.expander("생성된 블록 정보", expanded=True):
                                st.json(new_block)
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
        
        **1. 역할 (Role)**
        - AI가 어떤 전문가 역할을 할지 명확히 정의
        - 예: "건축 설계 전문가로서..."
        
        **2. 지시 (Instructions)**
        - 수행해야 할 작업의 구체적인 지시사항
        - 명확하고 실행 가능한 내용으로 작성
        
        **3. 단계 (Steps)**
        - 분석 과정을 논리적 순서로 나누어 제시
        - 각 단계는 구체적이고 명확해야 함
        
        **4. 최종 목표 (End Goal)**
        - 이 분석을 통해 달성하고자 하는 결과
        - 사용자에게 어떤 가치를 제공할지 명시
        
        **5. 구체화/제약 조건 (Narrowing)**
        - 출력 형식, 필수 항목, 제약 조건 등
        - 품질 기준과 평가 방법 명시
        """)
        
        st.markdown("---")
        
        st.subheader("📖 예시 프롬프트")
        
        with st.expander("기본 정보 추출 예시"):
            st.code("""
다음 단계별로 분석해주세요:

1단계: 문서 스캔
- PDF 내용을 읽고 건축 프로젝트 관련 정보 식별

2단계: 정보 분류
- 프로젝트명, 건축주, 대지위치, 건물용도, 주요 요구사항으로 분류

3단계: 정보 정리
- 각 항목별로 명확하게 정리하여 제시

각 단계별 사고 과정을 보여주세요.

PDF 내용: {pdf_text}
            """, language="text")
        
        with st.expander("요구사항 분석 예시"):
            st.code("""
다음 단계별로 요구사항을 분석해주세요:

1단계: 요구사항 식별
- PDF에서 건축 관련 요구사항을 찾아내기

2단계: 요구사항 분류
- 공간 요구사항, 기능적 요구사항, 법적 요구사항, 기술적 요구사항으로 분류

3단계: 우선순위 평가
- 각 요구사항의 중요도와 우선순위 평가

4단계: 종합 정리
- 분류된 요구사항을 명확하게 정리하여 제시

각 단계별 사고 과정을 보여주세요.

PDF 내용: {pdf_text}
            """, language="text")

if __name__ == "__main__":
    main()

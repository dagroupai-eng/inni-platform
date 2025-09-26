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
        page_icon="🔧",
        layout="wide"
    )
    
    st.title("🔧 분석 블록 생성기")
    st.markdown("---")
    
    # 기존 블록 로드
    blocks_data = load_blocks()
    existing_blocks = blocks_data.get("blocks", [])
    
    # 사이드바에 기존 블록 목록 표시
    with st.sidebar:
        st.header("📋 기존 블록 목록")
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
        st.header("🆕 새 블록 생성")
        
        # 블록 정보 입력 폼
        with st.form("block_creation_form"):
            # 블록 이름
            block_name = st.text_input(
                "블록 이름",
                placeholder="예: 🏗️ 건축 요구사항 분석 (CoT)",
                help="블록의 표시 이름을 입력하세요. 이모지를 포함할 수 있습니다."
            )
            
            # 블록 설명
            block_description = st.text_area(
                "블록 설명",
                placeholder="예: Chain of Thought로 건축 관련 요구사항을 분석하고 정리합니다",
                help="블록의 기능을 설명하는 간단한 문장을 입력하세요."
            )
            
            # 프롬프트 템플릿
            st.subheader("📝 프롬프트 템플릿")
            st.markdown("**사용 가능한 변수:** `{pdf_text}` - PDF 텍스트 내용이 자동으로 삽입됩니다.")
            
            prompt_template = st.text_area(
                "프롬프트 템플릿",
                height=300,
                placeholder="""다음 단계별로 분석해주세요:

1단계: 문서 스캔
- PDF 내용을 읽고 관련 정보 식별

2단계: 정보 분류
- 주요 항목별로 분류

3단계: 정보 정리
- 각 항목별로 명확하게 정리하여 제시

각 단계별 사고 과정을 보여주세요.

PDF 내용: {pdf_text}""",
                help="AI가 분석할 때 사용할 프롬프트를 작성하세요. {pdf_text} 변수를 포함해야 합니다."
            )
            
            # 고급 옵션
            with st.expander("⚙️ 고급 옵션"):
                custom_id = st.text_input(
                    "커스텀 ID (선택사항)",
                    placeholder="자동 생성됩니다",
                    help="블록의 고유 ID를 직접 지정할 수 있습니다. 비워두면 이름에서 자동 생성됩니다."
                )
                
                block_icon = st.selectbox(
                    "블록 아이콘",
                    ["📋", "🏗️", "💡", "🚶", "🏘️", "📊", "💰", "🔍", "📈", "🎯", "⚡", "🔧"],
                    help="블록 이름 앞에 표시될 아이콘을 선택하세요."
                )
            
            # 제출 버튼
            submitted = st.form_submit_button("✅ 블록 생성", type="primary")
            
            if submitted:
                # 입력 검증
                if not block_name.strip():
                    st.error("❌ 블록 이름을 입력해주세요.")
                elif not block_description.strip():
                    st.error("❌ 블록 설명을 입력해주세요.")
                elif not prompt_template.strip():
                    st.error("❌ 프롬프트 템플릿을 입력해주세요.")
                elif "{pdf_text}" not in prompt_template:
                    st.error("❌ 프롬프트 템플릿에 '{pdf_text}' 변수를 포함해주세요.")
                else:
                    # 블록 ID 생성
                    if custom_id.strip():
                        block_id = custom_id.strip()
                    else:
                        block_id = generate_block_id(block_name)
                    
                    # 아이콘이 이름에 포함되어 있지 않으면 추가
                    if not any(icon in block_name for icon in ["📋", "🏗️", "💡", "🚶", "🏘️", "📊", "💰", "🔍", "📈", "🎯", "⚡", "🔧"]):
                        final_name = f"{block_icon} {block_name}"
                    else:
                        final_name = block_name
                    
                    # 중복 ID 체크
                    existing_ids = [block.get('id') for block in existing_blocks]
                    if block_id in existing_ids:
                        st.error(f"❌ ID '{block_id}'가 이미 존재합니다. 다른 이름을 사용하거나 커스텀 ID를 입력해주세요.")
                    else:
                        # 새 블록 생성
                        new_block = {
                            "id": block_id,
                            "name": final_name,
                            "description": block_description,
                            "prompt": prompt_template,
                            "created_at": datetime.now().isoformat(),
                            "created_by": "user"
                        }
                        
                        # 블록 추가
                        existing_blocks.append(new_block)
                        blocks_data["blocks"] = existing_blocks
                        
                        # 저장
                        if save_blocks(blocks_data):
                            st.success(f"✅ 블록 '{final_name}'이 성공적으로 생성되었습니다!")
                            st.balloons()
                            
                            # 생성된 블록 정보 표시
                            with st.expander("📋 생성된 블록 정보", expanded=True):
                                st.json(new_block)
                        else:
                            st.error("❌ 블록 저장 중 오류가 발생했습니다.")
    
    with col2:
        st.header("📚 도움말")
        
        st.markdown("""
        ### 블록 생성 가이드
        
        **1. 블록 이름**
        - 사용자가 보게 될 이름
        - 이모지 포함 가능
        - 예: "🏗️ 건축 요구사항 분석"
        
        **2. 블록 설명**
        - 블록의 기능을 간단히 설명
        - 사용자가 블록을 선택할 때 참고
        
        **3. 프롬프트 템플릿**
        - AI가 분석할 때 사용할 지시사항
        - `{pdf_text}` 변수 필수 포함
        - 단계별 분석 구조 권장
        
        **4. 프롬프트 작성 팁**
        - 명확하고 구체적인 지시사항
        - 단계별 분석 구조 사용
        - "Chain of Thought" 방식 권장
        - 출력 형식 명시
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

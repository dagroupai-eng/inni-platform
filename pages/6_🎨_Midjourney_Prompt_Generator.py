import streamlit as st
import json
from datetime import datetime
import os
from file_analyzer import UniversalFileAnalyzer
from dspy_analyzer import EnhancedArchAnalyzer

# 페이지 설정
st.set_page_config(
    page_title="Midjourney 프롬프트 생성기",
    page_icon=None,
    layout="wide"
)

def generate_midjourney_prompt(user_inputs, cot_history, image_settings):
    """Midjourney 프롬프트 생성 함수"""
    from dspy_analyzer import EnhancedArchAnalyzer
    
    # 분석 결과 요약
    analysis_results = []
    if cot_history:
        for i, history in enumerate(cot_history, 1):
            analysis_results.append({
                'step': history.get('step', f'단계 {i}'),
                'summary': history.get('summary', ''),
                'insight': history.get('insight', ''),
                'result': history.get('result', '')
            })
    
    # 분석 결과 텍스트 생성
    if analysis_results:
        internal_analysis = "\n\n".join([
            f"**{h['step']}**: {h.get('summary', '')}"
            for h in analysis_results
        ])
    else:
        internal_analysis = ""
    
    # PDF 내용과 내부 분석을 결합
    pdf_content = image_settings.get('pdf_content', '')
    if pdf_content and internal_analysis:
        analysis_summary = f"**PDF 문서 내용:**\n{pdf_content[:2000]}...\n\n**내부 분석 결과:**\n{internal_analysis}"
    elif pdf_content:
        analysis_summary = f"**PDF 문서 내용:**\n{pdf_content[:2000]}..."
    elif internal_analysis:
        analysis_summary = f"**내부 분석 결과:**\n{internal_analysis}"
    else:
        analysis_summary = "분석 결과가 없습니다. 프로젝트 정보만을 기반으로 이미지 프롬프트를 생성합니다."
    
    # 개선된 이미지 생성 프롬프트
    image_prompt = f"""
당신은 건축 이미지 생성 전문가입니다. 분석 결과를 바탕으로 Midjourney에서 사용할 수 있는 구체적이고 효과적인 프롬프트를 생성해주세요.

##  프로젝트 정보
- 프로젝트명: {user_inputs.get('project_name', '')}
- 건물 유형: {user_inputs.get('building_type', '')}
- 대지 위치: {user_inputs.get('site_location', '')}
- 건축주: {user_inputs.get('owner', '')}
- 대지 면적: {user_inputs.get('site_area', '')}

## 분석 결과
{analysis_summary}

##  이미지 생성 요청
- 이미지 유형: {image_settings.get('image_type', '')}
- 스타일: {', '.join(image_settings.get('style_preference', [])) if image_settings.get('style_preference') else '기본'}
- 추가 설명: {image_settings.get('additional_description', '')}

##  출력 형식

**한글 설명:**
[이미지에 대한 한글 설명 - 건축적 특징, 분위기, 핵심 요소 등]

**English Midjourney Prompt:**
[구체적이고 실행 가능한 영어 프롬프트]

##  프롬프트 생성 가이드라인

**이미지 유형별 키워드:**
- **외관 렌더링**: building facade, exterior view, architectural elevation, material texture
- **내부 공간**: interior space, indoor lighting, furniture arrangement, spatial atmosphere
- **마스터플랜**: master plan, site layout, landscape design, circulation plan
- **상세도**: architectural detail, construction detail, material junction
- **컨셉 이미지**: concept visualization, mood board, artistic expression
- **조감도**: aerial view, bird's eye view, overall building form, site context

**스타일별 키워드:**
- **현대적**: modern, contemporary, clean lines, minimalist
- **미니멀**: minimal, simple, uncluttered, essential elements
- **자연친화적**: sustainable, green building, organic, eco-friendly
- **고급스러운**: luxury, premium, sophisticated, elegant
- **기능적**: functional, practical, efficient, user-friendly
- **예술적**: artistic, creative, expressive, innovative
- **상업적**: commercial, business-oriented, professional

**기술적 키워드:**
- architectural photography, professional rendering, hyperrealistic, 8k, high quality
- wide angle, natural lighting, golden hour, dramatic shadows, ambient lighting
- architectural visualization, photorealistic, modern design

**프롬프트 구조:**
[이미지 종류] + [건축 스타일] + [공간 유형] + [재료/텍스처] + [조명/분위기] + [환경/맥락] + [기술적 키워드] + [이미지 비율]

## 중요 지시사항
1. **분석 결과 반영**: 반드시 분석 결과의 건축적 특징을 프롬프트에 반영
2. **구체성**: 추상적이 아닌 구체적이고 실행 가능한 프롬프트 생성
3. **건축적 정확성**: 실제 건축물의 구조와 형태를 정확히 반영
4. **시각적 임팩트**: 조형적 아름다움과 상징성을 강조
5. **환경적 맥락**: 주변 환경과의 조화로운 관계 표현

위 가이드라인에 따라 한글 설명과 영어 Midjourney 프롬프트를 생성해주세요.
"""
    
    try:
        # DSPy 분석기 사용
        analyzer = EnhancedArchAnalyzer()
        result = analyzer.analyze_custom_block(image_prompt, "")
        
        if result['success']:
            # 결과를 파싱하여 구조화된 형태로 반환
            analysis_text = result['analysis']
            
            # 한글 설명과 영어 프롬프트 추출 시도
            korean_description = ""
            english_prompt = ""
            
            # 간단한 파싱 로직
            if "**한글 설명:**" in analysis_text:
                parts = analysis_text.split("**한글 설명:**")
                if len(parts) > 1:
                    korean_part = parts[1].split("**English Midjourney Prompt:**")[0].strip()
                    korean_description = korean_part
            
            if "**English Midjourney Prompt:**" in analysis_text:
                parts = analysis_text.split("**English Midjourney Prompt:**")
                if len(parts) > 1:
                    english_prompt = parts[1].strip()
            
            return {
                'success': True,
                'korean_description': korean_description,
                'english_prompt': english_prompt,
                'full_analysis': analysis_text,
                'model': result['model']
            }
        else:
            return {
                'success': False,
                'error': result.get('error', '알 수 없는 오류'),
                'model': result.get('model', 'Unknown')
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'model': 'DSPy Error'
        }

def load_analysis_data():
    """분석 데이터 로드"""
    try:
        if os.path.exists('blocks.json'):
            with open('blocks.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
    return {}

def main():
    st.title("Midjourney 프롬프트 생성기")
    st.markdown("**PDF 문서나 Document Analysis 결과를 활용한 건축 이미지 프롬프트 생성**")
    st.markdown("---")
    
    # Session state 초기화
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None
    if 'pdf_text' not in st.session_state:
        st.session_state.pdf_text = ""
    if 'analysis_data' not in st.session_state:
        st.session_state.analysis_data = {}
    
    # 사이드바 - 데이터 소스 선택
    with st.sidebar:
        st.header("데이터 소스")
        
        data_source = st.radio(
            "데이터 소스 선택",
            ["PDF 파일 업로드", "Document Analysis 결과 활용", "직접 입력"]
        )
        
        st.markdown("---")
        
        if data_source == "PDF 파일 업로드":
            st.header("PDF 파일 업로드")
            uploaded_file = st.file_uploader(
                "PDF 파일을 업로드하세요",
                type=['pdf'],
                help="건축 프로젝트 관련 PDF 문서를 업로드하세요"
            )
            
            if uploaded_file is not None:
                st.session_state.uploaded_file = uploaded_file
                with st.spinner("PDF를 분석하고 있습니다..."):
                    try:
                        # UniversalFileAnalyzer 사용
                        analyzer = UniversalFileAnalyzer()
                        
                        # 파일을 바이트로 읽기
                        pdf_bytes = uploaded_file.read()
                        
                        # PDF 분석 실행
                        result = analyzer.analyze_file_from_bytes(
                            pdf_bytes, 
                            "pdf", 
                            uploaded_file.name
                        )
                        
                        if result['success']:
                            pdf_text = result['text']
                            if pdf_text and len(pdf_text.strip()) > 0:
                                st.session_state.pdf_text = pdf_text.strip()
                                st.success(f"PDF 분석 완료! ({len(pdf_text.strip())}자)")
                                st.info(f"파일명: {uploaded_file.name}")
                                
                                # 추가 정보 표시
                                if 'metadata' in result:
                                    metadata = result['metadata']
                                    st.info(f"페이지 수: {metadata.get('page_count', 'N/A')}")
                            else:
                                st.error("PDF에서 텍스트를 추출할 수 없습니다. 이미지 기반 PDF이거나 텍스트가 없는 PDF일 수 있습니다.")
                        else:
                            st.error(f"PDF 분석 실패: {result.get('error', '알 수 없는 오류')}")
                            
                    except Exception as e:
                        st.error(f"PDF 분석 실패: {str(e)}")
                        st.info("파일이 손상되었거나 지원하지 않는 형식일 수 있습니다.")
        
        elif data_source == "Document Analysis 결과 활용":
            st.header("Document Analysis 결과")
            
            # blocks.json에서 분석 결과 로드
            analysis_data = load_analysis_data()
            if analysis_data:
                st.success("Document Analysis 결과가 로드되었습니다!")
                
                # 프로젝트 정보 표시
                if 'project_info' in analysis_data:
                    st.subheader("프로젝트 정보")
                    project_info = analysis_data['project_info']
                    st.write(f"**프로젝트명**: {project_info.get('project_name', 'N/A')}")
                    st.write(f"**프로젝트 유형**: {project_info.get('project_type', 'N/A')}")
                    st.write(f"**위치**: {project_info.get('location', 'N/A')}")
                    st.write(f"**규모**: {project_info.get('scale', 'N/A')}")
                
                # CoT 히스토리 요약
                if 'cot_history' in analysis_data:
                    st.subheader("분석 단계")
                    for i, history in enumerate(analysis_data['cot_history'][:3], 1):  # 최근 3개만 표시
                        st.write(f"**{i}단계**: {history.get('step', '분석 단계')}")
            else:
                st.warning("Document Analysis 결과가 없습니다. 먼저 Document Analysis 페이지에서 분석을 진행하세요.")
        
        else:  # 직접 입력
            st.header("프로젝트 정보 직접 입력")
            
            project_name = st.text_input("프로젝트명", value="", placeholder="예: 서울시청 신청사")
            building_type = st.selectbox(
                "건물 유형",
                ["", "사무용", "주거용", "상업용", "문화시설", "교육시설", "의료시설", "기타"]
            )
            site_location = st.text_input("대지 위치", value="", placeholder="예: 서울시 중구")
            owner = st.text_input("건축주", value="", placeholder="예: 서울특별시")
            site_area = st.text_input("대지 면적", value="", placeholder="예: 15,000㎡")
            
            # 직접 입력한 정보를 session state에 저장
            st.session_state.manual_input = {
                'project_name': project_name,
                'building_type': building_type,
                'site_location': site_location,
                'owner': owner,
                'site_area': site_area
            }
        
        st.markdown("---")
        st.header("이미지 설정")
        
        image_type = st.selectbox(
            "이미지 유형",
            ["", "외관 렌더링", "내부 공간", "마스터플랜", "상세도", "컨셉 이미지", "조감도"]
        )
        
        style_preference = st.multiselect(
            "스타일 선호도",
            ["현대적", "미니멀", "자연친화적", "고급스러운", "기능적", "예술적", "상업적"]
        )
        
        additional_description = st.text_area(
            "추가 설명",
            value="",
            placeholder="특별히 강조하고 싶은 요소나 요구사항을 입력하세요.",
            height=100
        )
    
    # 메인 컨텐츠
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("데이터 미리보기")
        
        # 현재 선택된 데이터 소스에 따른 미리보기
        if data_source == "PDF 파일 업로드":
            if st.session_state.pdf_text:
                st.success("PDF 텍스트가 로드되었습니다.")
                with st.expander("PDF 내용 미리보기"):
                    st.text(st.session_state.pdf_text[:1000] + "..." if len(st.session_state.pdf_text) > 1000 else st.session_state.pdf_text)
            else:
                st.info("PDF 파일을 업로드하면 내용이 여기에 표시됩니다.")
        
        elif data_source == "Document Analysis 결과 활용":
            analysis_data = load_analysis_data()
            if analysis_data:
                st.success("Document Analysis 결과가 로드되었습니다.")
                
                # CoT 히스토리 표시
                if 'cot_history' in analysis_data:
                    st.subheader("사고 과정 (Chain of Thought)")
                    for i, history in enumerate(analysis_data['cot_history'][:3], 1):  # 최근 3개만 표시
                        with st.expander(f"단계 {i}: {history.get('step', '분석 단계')}"):
                            st.write(f"**요약**: {history.get('summary', '')}")
                            st.write(f"**인사이트**: {history.get('insight', '')}")
                            st.write(f"**결과**: {history.get('result', '')}")
            else:
                st.warning("Document Analysis 결과가 없습니다.")
        
        else:  # 직접 입력
            if hasattr(st.session_state, 'manual_input'):
                manual_input = st.session_state.manual_input
                if manual_input.get('project_name'):
                    st.success("프로젝트 정보가 입력되었습니다.")
                    st.write(f"**프로젝트명**: {manual_input.get('project_name')}")
                    st.write(f"**건물 유형**: {manual_input.get('building_type')}")
                    st.write(f"**대지 위치**: {manual_input.get('site_location')}")
                else:
                    st.info("프로젝트 정보를 입력하면 여기에 표시됩니다.")
    
    with col2:
        st.header("프롬프트 생성")
        
        # 프롬프트 생성 버튼
        if st.button("Midjourney 프롬프트 생성", type="primary", use_container_width=True):
            # 데이터 소스에 따른 입력 데이터 구성
            user_inputs = {}
            cot_history = []
            pdf_content = ""
            
            if data_source == "PDF 파일 업로드":
                if not st.session_state.pdf_text:
                    st.error("PDF 파일을 먼저 업로드해주세요.")
                    return
                pdf_content = st.session_state.pdf_text
                user_inputs = {
                    'project_name': 'PDF 문서에서 추출',
                    'building_type': 'PDF 문서에서 추출',
                    'site_location': 'PDF 문서에서 추출',
                    'owner': 'PDF 문서에서 추출',
                    'site_area': 'PDF 문서에서 추출'
                }
            
            elif data_source == "Document Analysis 결과 활용":
                analysis_data = load_analysis_data()
                if not analysis_data:
                    st.error("Document Analysis 결과가 없습니다.")
                    return
                
                # Document Analysis 결과에서 정보 추출
                if 'project_info' in analysis_data:
                    project_info = analysis_data['project_info']
                    user_inputs = {
                        'project_name': project_info.get('project_name', ''),
                        'building_type': project_info.get('project_type', ''),
                        'site_location': project_info.get('location', ''),
                        'owner': project_info.get('owner', ''),
                        'site_area': project_info.get('scale', '')
                    }
                
                cot_history = analysis_data.get('cot_history', [])
                pdf_content = analysis_data.get('pdf_text', '')
            
            else:  # 직접 입력
                if not hasattr(st.session_state, 'manual_input') or not st.session_state.manual_input.get('project_name'):
                    st.error("프로젝트 정보를 입력해주세요.")
                    return
                user_inputs = st.session_state.manual_input
            
            # 이미지 설정 데이터 구성
            image_settings = {
                'image_type': image_type,
                'style_preference': style_preference,
                'additional_description': additional_description,
                'pdf_content': pdf_content
            }
            
            # 로딩 표시
            with st.spinner("프롬프트를 생성하고 있습니다..."):
                try:
                    # 프롬프트 생성
                    result = generate_midjourney_prompt(user_inputs, cot_history, image_settings)
                    
                    if result and result.get('success'):
                        st.success("프롬프트가 성공적으로 생성되었습니다!")
                        
                        # 결과 표시
                        st.markdown("---")
                        st.subheader("생성된 프롬프트")
                        
                        # 한글 설명
                        if result.get('korean_description'):
                            st.markdown("**한글 설명:**")
                            st.write(result['korean_description'])
                        
                        # 영어 프롬프트
                        if result.get('english_prompt'):
                            st.markdown("**English Midjourney Prompt:**")
                            st.code(result['english_prompt'], language="text")
                            
                            # 복사 버튼
                            if st.button("프롬프트 복사", key="copy_prompt"):
                                st.write("프롬프트가 클립보드에 복사되었습니다!")
                        
                        # 전체 분석 결과 표시
                        if result.get('full_analysis'):
                            with st.expander("전체 분석 결과"):
                                st.markdown(result['full_analysis'])
                        
                        # 모델 정보
                        if result.get('model'):
                            st.caption(f"생성 모델: {result['model']}")
                    
                    else:
                        error_msg = result.get('error', '알 수 없는 오류') if result else '결과가 없습니다.'
                        st.error(f"프롬프트 생성에 실패했습니다: {error_msg}")
                        
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {str(e)}")
    
    # 하단 정보
    st.markdown("---")
    st.markdown("""
    ### 사용 팁
    
    **PDF 파일 업로드:**
    - 건축 프로젝트 관련 PDF 문서를 직접 업로드하여 분석
    - PDF 내용을 자동으로 추출하여 프롬프트 생성에 활용
    
    **Document Analysis 결과 활용:**
    - Document Analysis 페이지에서 분석한 결과를 자동으로 활용
    - Chain of Thought 분석 과정을 반영한 정확한 프롬프트 생성
    
    **직접 입력:**
    - 프로젝트 정보를 직접 입력하여 프롬프트 생성
    - 빠른 테스트나 간단한 프로젝트에 적합
    
    **이미지 설정:**
    - **이미지 유형**: 원하는 이미지의 종류를 선택하세요 (외관, 내부, 조감도 등)
    - **스타일 선호도**: 여러 스타일을 선택하여 다양한 방향의 프롬프트를 생성할 수 있습니다
    - **추가 설명**: 특별히 강조하고 싶은 요소나 요구사항을 입력하세요
    """)

if __name__ == "__main__":
    main()

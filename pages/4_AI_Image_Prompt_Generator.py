import streamlit as st
import json
from datetime import datetime
import os
import re
import pandas as pd
from file_analyzer import UniversalFileAnalyzer
from dspy_analyzer import EnhancedArchAnalyzer

# 인증 모듈 import
try:
    from auth.authentication import check_page_access
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="AI 이미지 프롬프트 생성기",
    page_icon=None,
    layout="wide"
)

# 세션 초기화 (로그인 + 작업 데이터 복원)
try:
    from auth.session_init import init_page_session, render_session_manager_sidebar
    init_page_session()
except Exception as e:
    print(f"세션 초기화 오류: {e}")
    render_session_manager_sidebar = None

# 로그인 체크
if AUTH_AVAILABLE:
    check_page_access()

# 세션 관리 사이드바 렌더링
if render_session_manager_sidebar:
    render_session_manager_sidebar()

# AI 이미지 프롬프트 생성 함수
def generate_ai_image_prompt(user_inputs, cot_history, image_settings):
    """AI 이미지 프롬프트 생성 함수"""
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

당신은 건축 이미지 생성 전문가입니다. 분석 결과를 바탕으로 AI 이미지 생성 도구(Midjourney, DALL-E, Stable Diffusion 등)에서 사용할 수 있는 구체적이고 효과적인 프롬프트를 생성해주세요.

##  프로젝트 정보
- 프로젝트명: {user_inputs.get('project_name', '')}
- 프로젝트 유형: {user_inputs.get('building_type', '')}
- 대지 위치: {user_inputs.get('site_location', '')}
- 프로젝트 설명: {user_inputs.get('project_description', '')}

## 분석 결과
{analysis_summary}

##  이미지 생성 요청
- 이미지 유형: {image_settings.get('image_type', '')}
- 스타일: {', '.join(image_settings.get('style_preference', [])) if image_settings.get('style_preference') else '기본'}
- 참고 건축가/스튜디오: {image_settings.get('architect_reference', '') or '없음'}
- 추가 설명: {image_settings.get('additional_description', '')}
- 네거티브 프롬프트 (사용자 입력): {image_settings.get('negative_prompt', '') or '없음'}

##  출력 형식

**한글 설명:**
[이미지에 대한 한글 설명 - 건축적 특징, 분위기, 핵심 요소 등]

**English Prompt:**
[구체적이고 실행 가능한 영어 프롬프트]

**Negative Prompt:**
[이미지에서 제외할 요소들 - 사용자 입력을 기반으로 하되, 건축 이미지 품질을 위한 기본 요소도 포함]
기본 포함 요소: blurry, low quality, distorted, watermark, text overlay, signature, deformed architecture, unrealistic proportions

##  프롬프트 생성 가이드라인

**이미지 유형별 키워드:**
- **마스터플랜 조감도**: master plan aerial view, urban planning, site development, multiple buildings, district view, city block
- **토지이용계획도**: land use plan, zoning diagram, color-coded zones, functional areas, urban planning map
- **배치도**: site plan, building arrangement, layout plan, ground floor plan, urban fabric
- **동선계획도**: circulation plan, traffic flow, pedestrian network, vehicle routes, connectivity diagram
- **오픈스페이스**: public space, plaza, park, green corridor, landscape design, outdoor gathering
- **보행자 시점**: street level view, pedestrian perspective, eye-level rendering, urban streetscape
- **야간 경관**: night view, lighting design, illuminated cityscape, nighttime atmosphere, urban lights
- **단면 다이어그램**: section diagram, urban section, building heights, spatial relationship
- **컨셉 이미지**: concept visualization, mood board, artistic expression, design vision

**스타일별 키워드:**
- **현대적**: modern urban design, contemporary architecture, clean geometric forms, glass and steel
- **미니멀**: minimal design, simple volumes, uncluttered layout, essential elements
- **자연친화적**: sustainable development, green urbanism, biophilic design, eco-friendly, urban forest
- **고급스러운**: premium development, high-end district, sophisticated urban fabric, elegant design
- **기능적**: functional zoning, efficient layout, mixed-use development, transit-oriented
- **예술적**: artistic urban design, sculptural buildings, creative placemaking, iconic landmarks
- **도시적**: urban density, city blocks, street grid, metropolitan scale

**기술적 키워드:**
- architectural photography, professional rendering, hyperrealistic, 8k, high quality
- wide angle, natural lighting, golden hour, dramatic shadows, ambient lighting
- architectural visualization, photorealistic, modern design

**건축가 스타일 참고 (참고 건축가가 지정된 경우):**
- 해당 건축가의 대표적인 디자인 특성을 프롬프트에 반영
- 예: "in the style of Zaha Hadid", "inspired by Bjarke Ingels BIG studio"
- 건축가의 특징적인 형태, 재료, 공간 구성 방식을 키워드로 포함

**프롬프트 구조:**
[이미지 종류] + [건축 스타일] + [공간 유형] + [재료/텍스처] + [조명/분위기] + [환경/맥락] + [기술적 키워드] + [이미지 비율]

## 중요 지시사항
1. **분석 결과 반영**: 반드시 분석 결과의 건축적 특징을 프롬프트에 반영
2. **구체성**: 추상적이 아닌 구체적이고 실행 가능한 프롬프트 생성
3. **건축적 정확성**: 실제 건축물의 구조와 형태를 정확히 반영
4. **시각적 임팩트**: 조형적 아름다움과 상징성을 강조
5. **환경적 맥락**: 주변 환경과의 조화로운 관계 표현

위 가이드라인에 따라 한글 설명과 영어 이미지 생성 프롬프트를 생성해주세요.
"""
    
    try:
        # DSPy 분석기 사용
        analyzer = EnhancedArchAnalyzer()
        result = analyzer.analyze_custom_block(image_prompt, "")
        
        if result['success']:
            # 결과를 파싱하여 구조화된 형태로 반환
            analysis_text = result['analysis']
            
            # 한글 설명, 영어 프롬프트, 네거티브 프롬프트 추출 시도
            korean_description = ""
            english_prompt = ""
            negative_prompt = ""

            # 간단한 파싱 로직
            if "**한글 설명:**" in analysis_text:
                parts = analysis_text.split("**한글 설명:**")
                if len(parts) > 1:
                    korean_part = parts[1].split("**English Prompt:**")[0].strip()
                    korean_description = korean_part

            if "**English Prompt:**" in analysis_text:
                parts = analysis_text.split("**English Prompt:**")
                if len(parts) > 1:
                    english_part = parts[1]
                    # Negative Prompt가 있으면 그 전까지만
                    if "**Negative Prompt:**" in english_part:
                        english_prompt = english_part.split("**Negative Prompt:**")[0].strip()
                    else:
                        english_prompt = english_part.strip()

            if "**Negative Prompt:**" in analysis_text:
                parts = analysis_text.split("**Negative Prompt:**")
                if len(parts) > 1:
                    negative_prompt = parts[1].strip()
                    # 다음 섹션이 있으면 그 전까지만
                    if "**" in negative_prompt:
                        negative_prompt = negative_prompt.split("**")[0].strip()

            return {
                'success': True,
                'korean_description': korean_description,
                'english_prompt': english_prompt,
                'negative_prompt': negative_prompt,
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

# 분석 데이터 로드 함수
def load_analysis_data():
    """분석 데이터 로드 - st.session_state에서 Document Analysis 결과를 로드"""
    try:
        # Document Analysis 결과가 있는지 확인
        has_analysis = (
            st.session_state.get('analysis_results') or 
            st.session_state.get('cot_history') or
            st.session_state.get('project_name')
        )
        
        if not has_analysis:
            return {}
        
        # session_state에서 데이터 구성
        analysis_data = {
            'project_info': {
                'project_name': st.session_state.get('project_name', ''),
                'project_type': '',  # Document Analysis에서 별도로 저장하지 않음
                'location': st.session_state.get('location', ''),
                'owner': '',  # Document Analysis에서 별도로 저장하지 않음
                'scale': ''  # Document Analysis에서 별도로 저장하지 않음
            },
            'cot_history': st.session_state.get('cot_history', []),
            'pdf_text': st.session_state.get('pdf_text', ''),
            'analysis_results': st.session_state.get('analysis_results', {})
        }
        
        return analysis_data
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return {}

def render_markdown_with_tables(text):
    """마크다운 텍스트를 렌더링하면서 테이블은 st.dataframe()으로 변환합니다."""
    if not text or not isinstance(text, str):
        return

    lines = text.split('\n')
    i = 0
    buffer = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 마크다운 테이블 시작 감지 (| 구분자 기준)
        if '|' in stripped and stripped.count('|') >= 2:
            # 버퍼에 있는 텍스트 먼저 출력
            if buffer:
                st.markdown('\n'.join(buffer))
                buffer = []

            # 테이블 라인 수집
            table_lines = [stripped]
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if '|' in next_line and next_line.count('|') >= 2:
                    table_lines.append(next_line)
                    i += 1
                else:
                    break

            # 테이블을 DataFrame으로 변환
            if len(table_lines) >= 2:
                try:
                    parsed_rows = []
                    for tl in table_lines:
                        cells = [c.strip() for c in tl.split('|')[1:-1]]
                        if cells:
                            parsed_rows.append(cells)

                    if len(parsed_rows) >= 2:
                        # 구분선 확인 (--- 패턴)
                        is_separator = all(
                            re.match(r'^[-:]+$', c) or c == ''
                            for c in parsed_rows[1]
                        )

                        if is_separator and len(parsed_rows) >= 3:
                            headers = parsed_rows[0]
                            data = parsed_rows[2:]
                        else:
                            headers = [f"열{j+1}" for j in range(len(parsed_rows[0]))]
                            data = parsed_rows

                        # DataFrame 생성
                        if data:
                            max_cols = len(headers)
                            normalized_data = []
                            for row in data:
                                if len(row) < max_cols:
                                    row = row + [''] * (max_cols - len(row))
                                elif len(row) > max_cols:
                                    row = row[:max_cols]
                                normalized_data.append(row)

                            df = pd.DataFrame(normalized_data, columns=headers)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            continue
                except Exception:
                    pass

            # 파싱 실패 시 원본 출력
            st.code('\n'.join(table_lines), language=None)
            continue

        # 일반 라인은 버퍼에 추가
        buffer.append(line)
        i += 1

    # 남은 버퍼 출력
    if buffer:
        st.markdown('\n'.join(buffer))

# 웹 페이지
def main():
    st.title("AI 이미지 프롬프트 생성기")
    st.markdown("**건축 프로젝트를 위한 AI 이미지 생성 프롬프트 도구**")
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
            ["PDF 파일 업로드", "직접 입력"]
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
        
        else:  # 직접 입력
            st.header("프로젝트 정보 직접 입력")

            project_name = st.text_input("프로젝트명", value="", placeholder="예: 서울시청 신청사")
            building_type = st.selectbox(
                "프로젝트 유형",
                ["", "마스터플랜", "도시재생", "복합개발", "캠퍼스/연구단지", "산업단지", "주거단지", "상업/업무단지", "문화시설", "공공시설", "기타"]
            )
            site_location = st.text_input("대지 위치", value="", placeholder="예: 서울시 중구")
            project_description = st.text_area(
                "프로젝트 설명",
                value="",
                placeholder="프로젝트의 특징, 컨셉, 주요 시설 등을 자유롭게 입력하세요.",
                height=120
            )

            # 직접 입력한 정보를 session state에 저장
            st.session_state.manual_input = {
                'project_name': project_name,
                'building_type': building_type,
                'site_location': site_location,
                'project_description': project_description
            }
        
        st.markdown("---")
        st.header("이미지 설정")

        image_type = st.selectbox(
            "이미지 유형",
            ["", "마스터플랜 조감도", "토지이용계획도", "배치도", "동선계획도", "오픈스페이스", "보행자 시점", "야간 경관", "단면 다이어그램", "컨셉 이미지"]
        )

        style_preference = st.multiselect(
            "스타일 선호도",
            ["현대적", "미니멀", "자연친화적", "고급스러운", "기능적", "예술적", "도시적"]
        )

        architect_reference = st.text_input(
            "참고 건축가/스튜디오",
            value="",
            placeholder="예: Bjarke Ingels, Zaha Hadid, MVRDV",
            help="프롬프트에 해당 건축가의 스타일을 반영합니다"
        )

        additional_description = st.text_area(
            "추가 설명",
            value="",
            placeholder="특별히 강조하고 싶은 요소나 요구사항을 입력하세요.",
            height=100
        )

        negative_prompt_input = st.text_area(
            "네거티브 프롬프트 (제외할 요소)",
            value="",
            placeholder="예: blurry, low quality, distorted, watermark, text, people, cars",
            help="이미지에서 제외하고 싶은 요소들을 영어로 입력하세요. 쉼표로 구분합니다.",
            height=80
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
        
        else:  # 직접 입력
            if hasattr(st.session_state, 'manual_input'):
                manual_input = st.session_state.manual_input
                if manual_input.get('project_name'):
                    st.success("프로젝트 정보가 입력되었습니다.")
                    st.write(f"**프로젝트명**: {manual_input.get('project_name')}")
                    st.write(f"**프로젝트 유형**: {manual_input.get('building_type')}")
                    st.write(f"**대지 위치**: {manual_input.get('site_location')}")
                    if manual_input.get('project_description'):
                        st.write(f"**프로젝트 설명**: {manual_input.get('project_description')[:100]}...")
                else:
                    st.info("프로젝트 정보를 입력하면 여기에 표시됩니다.")
    
    with col2:
        st.header("프롬프트 생성")
        
        # 프롬프트 생성 버튼
        if st.button("AI 이미지 프롬프트 생성", type="primary", use_container_width=True):
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
            
            else:  # 직접 입력
                if not hasattr(st.session_state, 'manual_input') or not st.session_state.manual_input.get('project_name'):
                    st.error("프로젝트 정보를 입력해주세요.")
                    return
                manual = st.session_state.manual_input
                user_inputs = {
                    'project_name': manual.get('project_name', ''),
                    'building_type': manual.get('building_type', ''),
                    'site_location': manual.get('site_location', ''),
                    'project_description': manual.get('project_description', '')
                }
            
            # 이미지 설정 데이터 구성
            image_settings = {
                'image_type': image_type,
                'style_preference': style_preference,
                'architect_reference': architect_reference,
                'additional_description': additional_description,
                'negative_prompt': negative_prompt_input,
                'pdf_content': pdf_content
            }
            
            # 로딩 표시
            with st.spinner("프롬프트를 생성하고 있습니다..."):
                try:
                    # 프롬프트 생성
                    result = generate_ai_image_prompt(user_inputs, cot_history, image_settings)
                    
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
                            st.markdown("**English Prompt:**")
                            st.code(result['english_prompt'], language="text")

                        # 네거티브 프롬프트
                        if result.get('negative_prompt'):
                            st.markdown("**Negative Prompt:**")
                            st.code(result['negative_prompt'], language="text")

                            # 복사 버튼
                            if st.button("프롬프트 복사", key="copy_prompt"):
                                st.write("프롬프트가 클립보드에 복사되었습니다!")
                        
                        # 전체 분석 결과 표시
                        if result.get('full_analysis'):
                            with st.expander("전체 분석 결과"):
                                render_markdown_with_tables(result['full_analysis'])
                        
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

    **직접 입력:**
    - 프로젝트 정보를 직접 입력하여 프롬프트 생성
    - 빠른 테스트나 간단한 프로젝트에 적합

    **이미지 설정:**
    - **이미지 유형**: 원하는 이미지의 종류를 선택하세요 (조감도, 배치도, 보행자 시점 등)
    - **스타일 선호도**: 여러 스타일을 선택하여 다양한 방향의 프롬프트를 생성할 수 있습니다
    - **참고 건축가**: 특정 건축가의 스타일을 참고하여 프롬프트에 반영합니다
    - **추가 설명**: 특별히 강조하고 싶은 요소나 요구사항을 입력하세요
    - **네거티브 프롬프트**: 이미지에서 제외하고 싶은 요소를 영어로 입력하세요 (예: blurry, watermark, people)
    """)

if __name__ == "__main__":
    main()

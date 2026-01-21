import streamlit as st
import json
from datetime import datetime
import os
from dspy_analyzer import EnhancedArchAnalyzer

# 인증 모듈 import
try:
    from auth.authentication import check_page_access
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="Video Storyboard Generator",
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


# 상수 정의
VIDEO_TYPES = ["마스터플랜 소개 영상", "프로젝트 소개 영상", "공간 워크스루", "컨셉 설명 영상", "드론 촬영 영상", "개발 단계별 영상"]
VIDEO_LENGTHS = ["30초", "1분", "2분", "3분", "5분"]
TARGET_AUDIENCES = ["일반인", "전문가", "클라이언트", "학생"]
MOODS = ["역동적", "차분한", "감성적", "전문적"]
CAMERA_ANGLES = ["정면", "측면", "조감", "클로즈업", "와이드"]
CAMERA_MOVEMENTS = ["고정", "팬", "틸트", "줌", "트래킹"]
NARRATIVE_TYPES = ["스토리텔링형", "설명형", "감성형", "기술 중심형"]
NARRATIVE_TONES = ["공식적", "친근한", "열정적", "차분한"]

# 템플릿 정의 (마스터플랜 프로젝트 중심)
STORYBOARD_TEMPLATES = {
    "마스터플랜 기본": [
        {"name": "도입 - 광역 맥락", "description": "도시/지역 맥락에서 대상지 위치와 주변 환경", "angle": "조감", "movement": "줌", "duration": 6},
        {"name": "대상지 현황", "description": "현재 대상지 상태와 기존 환경 분석", "angle": "조감", "movement": "팬", "duration": 8},
        {"name": "마스터플랜 전체 조감", "description": "개발 완료 후 전체 마스터플랜 조감도", "angle": "조감", "movement": "팬", "duration": 10},
        {"name": "토지이용계획", "description": "용도별 존(Zone) 구분과 배치 계획", "angle": "조감", "movement": "트래킹", "duration": 8},
        {"name": "동선 체계", "description": "차량, 보행자, 자전거 등 교통 동선 계획", "angle": "조감", "movement": "트래킹", "duration": 8},
        {"name": "오픈스페이스", "description": "공원, 광장, 녹지 등 오픈스페이스 계획", "angle": "와이드", "movement": "팬", "duration": 8},
        {"name": "주요 시설 클러스터", "description": "핵심 시설군과 랜드마크 건물", "angle": "측면", "movement": "트래킹", "duration": 8},
        {"name": "보행자 시점", "description": "보행자 눈높이에서 본 거리 풍경", "angle": "정면", "movement": "트래킹", "duration": 6},
        {"name": "야간 경관", "description": "야간 조명 계획과 경관", "angle": "조감", "movement": "팬", "duration": 6},
        {"name": "마무리", "description": "전체 마스터플랜 최종 조감과 비전", "angle": "조감", "movement": "줌", "duration": 6},
    ],
    "도시재생 마스터플랜": [
        {"name": "도입 - 지역 맥락", "description": "재생 대상 지역의 도시적 맥락과 역사", "angle": "조감", "movement": "줌", "duration": 6},
        {"name": "현황 분석", "description": "기존 도시 조직, 건물, 인프라 현황", "angle": "조감", "movement": "팬", "duration": 8},
        {"name": "재생 컨셉", "description": "도시재생의 핵심 컨셉과 전략", "angle": "조감", "movement": "트래킹", "duration": 8},
        {"name": "전체 마스터플랜", "description": "재생 완료 후 전체 조감도", "angle": "조감", "movement": "팬", "duration": 10},
        {"name": "보존 vs 신축", "description": "기존 건물 보존과 신규 개발 구역", "angle": "와이드", "movement": "팬", "duration": 8},
        {"name": "공공공간 네트워크", "description": "광장, 보행로, 공원의 연결 체계", "angle": "조감", "movement": "트래킹", "duration": 8},
        {"name": "커뮤니티 시설", "description": "주민 커뮤니티 시설과 프로그램", "angle": "와이드", "movement": "트래킹", "duration": 6},
        {"name": "거리 경관", "description": "재생된 거리의 보행자 시점 풍경", "angle": "정면", "movement": "트래킹", "duration": 8},
        {"name": "야간 활성화", "description": "야간 프로그램과 조명 경관", "angle": "측면", "movement": "팬", "duration": 6},
        {"name": "마무리", "description": "도시재생 비전과 최종 조감", "angle": "조감", "movement": "줌", "duration": 6},
    ],
    "복합개발 마스터플랜": [
        {"name": "도입", "description": "대상지 위치와 광역 교통 연계", "angle": "조감", "movement": "줌", "duration": 6},
        {"name": "전체 마스터플랜", "description": "복합개발 전체 조감도", "angle": "조감", "movement": "팬", "duration": 10},
        {"name": "용도 배치", "description": "업무, 상업, 주거, 문화 등 용도별 배치", "angle": "조감", "movement": "트래킹", "duration": 8},
        {"name": "저층부 상업가로", "description": "저층부 리테일과 상업 가로", "angle": "정면", "movement": "트래킹", "duration": 8},
        {"name": "업무 클러스터", "description": "오피스 타워와 업무 시설군", "angle": "측면", "movement": "팬", "duration": 8},
        {"name": "주거 클러스터", "description": "주거동과 커뮤니티 시설", "angle": "와이드", "movement": "팬", "duration": 8},
        {"name": "공공 데크/광장", "description": "입체적 공공공간과 연결 데크", "angle": "와이드", "movement": "트래킹", "duration": 8},
        {"name": "지하 공간", "description": "지하 주차, 물류, 연결 통로", "angle": "측면", "movement": "트래킹", "duration": 6},
        {"name": "야간 스카이라인", "description": "야간 조명과 스카이라인", "angle": "와이드", "movement": "팬", "duration": 6},
        {"name": "마무리", "description": "복합개발 비전과 최종 전경", "angle": "조감", "movement": "줌", "duration": 6},
    ],
    "캠퍼스 마스터플랜": [
        {"name": "도입", "description": "캠퍼스 위치와 주변 도시 맥락", "angle": "조감", "movement": "줌", "duration": 6},
        {"name": "캠퍼스 전체 조감", "description": "캠퍼스 마스터플랜 전체 조감도", "angle": "조감", "movement": "팬", "duration": 10},
        {"name": "존(Zone) 계획", "description": "교육, 연구, 기숙사, 지원시설 존 배치", "angle": "조감", "movement": "트래킹", "duration": 8},
        {"name": "중앙 녹지축", "description": "캠퍼스 중심 녹지와 보행 축", "angle": "와이드", "movement": "트래킹", "duration": 8},
        {"name": "교육 클러스터", "description": "강의동, 실험동 등 교육시설군", "angle": "측면", "movement": "팬", "duration": 8},
        {"name": "연구/산학 클러스터", "description": "연구소, 산학협력 시설", "angle": "측면", "movement": "팬", "duration": 8},
        {"name": "학생 생활관", "description": "기숙사와 학생 편의시설", "angle": "와이드", "movement": "팬", "duration": 6},
        {"name": "캠퍼스 광장", "description": "중앙 광장과 커뮤니티 공간", "angle": "정면", "movement": "트래킹", "duration": 8},
        {"name": "야간 캠퍼스", "description": "야간 캠퍼스 경관과 조명", "angle": "조감", "movement": "팬", "duration": 6},
        {"name": "마무리", "description": "캠퍼스 비전과 최종 조감", "angle": "조감", "movement": "줌", "duration": 6},
    ],
    "산업단지 마스터플랜": [
        {"name": "도입", "description": "산업단지 위치와 광역 물류 연계", "angle": "조감", "movement": "줌", "duration": 6},
        {"name": "전체 마스터플랜", "description": "산업단지 전체 배치 조감도", "angle": "조감", "movement": "팬", "duration": 10},
        {"name": "블록 계획", "description": "용도별 블록 구분과 필지 계획", "angle": "조감", "movement": "트래킹", "duration": 8},
        {"name": "도로/물류 체계", "description": "차량 동선과 물류 동선 계획", "angle": "조감", "movement": "트래킹", "duration": 8},
        {"name": "제조 클러스터", "description": "생산시설과 물류시설 배치", "angle": "와이드", "movement": "팬", "duration": 8},
        {"name": "R&D/지원시설", "description": "연구개발 시설과 지원시설", "angle": "측면", "movement": "팬", "duration": 8},
        {"name": "근린 편의시설", "description": "근로자 편의시설과 휴게공간", "angle": "와이드", "movement": "트래킹", "duration": 6},
        {"name": "녹지/완충지대", "description": "경계 녹지와 환경 완충지대", "angle": "조감", "movement": "팬", "duration": 6},
        {"name": "마무리", "description": "산업단지 비전과 최종 조감", "angle": "조감", "movement": "줌", "duration": 6},
    ],
}


def load_analysis_data():
    """Document Analysis 결과를 session_state에서 로드"""
    try:
        has_analysis = (
            st.session_state.get('analysis_results') or
            st.session_state.get('cot_history') or
            st.session_state.get('project_name')
        )

        if not has_analysis:
            return {}

        analysis_data = {
            'project_info': {
                'project_name': st.session_state.get('project_name', ''),
                'project_type': '',
                'location': st.session_state.get('location', ''),
                'owner': '',
                'scale': ''
            },
            'cot_history': st.session_state.get('cot_history', []),
            'pdf_text': st.session_state.get('pdf_text', ''),
            'analysis_results': st.session_state.get('analysis_results', {}),
            'generated_prompts': st.session_state.get('generated_prompts', [])
        }

        return analysis_data
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return {}


def generate_narrative(scenes, project_info, narrative_type, narrative_tone):
    """AI를 사용하여 각 Scene에 대한 Narrative 생성"""

    scenes_text = "\n".join([
        f"- Scene {i+1} ({s['name']}): {s['description']} / 카메라: {s['angle']}, {s['movement']} / {s['duration']}초"
        for i, s in enumerate(scenes)
    ])

    prompt = f"""
당신은 건축 영상 제작 전문가입니다. 아래 스토리보드의 각 Scene에 대해 Narrative(나레이션/해설)를 작성해주세요.

## 프로젝트 정보
- 프로젝트명: {project_info.get('project_name', 'N/A')}
- 위치: {project_info.get('location', 'N/A')}
- 건물 유형: {project_info.get('building_type', 'N/A')}

## Narrative 스타일
- 유형: {narrative_type}
- 톤: {narrative_tone}

## Scene 목록
{scenes_text}

## 출력 형식
각 Scene별로 아래 형식으로 작성해주세요:

**Scene 1: [Scene 이름]**
[해당 Scene의 Narrative - 2~3문장]

**Scene 2: [Scene 이름]**
[해당 Scene의 Narrative - 2~3문장]

(모든 Scene에 대해 작성)

## 작성 가이드라인
1. {narrative_type} 스타일에 맞게 작성
2. {narrative_tone} 톤 유지
3. 각 Scene의 시각적 특성과 공간적 의미를 반영
4. 전체적인 흐름과 연결성 고려
5. 건축적 특징과 공간의 분위기 강조
"""

    try:
        analyzer = EnhancedArchAnalyzer()
        result = analyzer.analyze_custom_block(prompt, "")

        if result['success']:
            return {
                'success': True,
                'narratives': result['analysis'],
                'model': result['model']
            }
        else:
            return {
                'success': False,
                'error': result.get('error', '알 수 없는 오류')
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def generate_scene_prompts(scenes, project_info):
    """각 Scene에 대한 Midjourney 프롬프트 생성"""

    prompts = []

    for i, scene in enumerate(scenes):
        # 카메라 앵글에 따른 키워드
        angle_keywords = {
            "정면": "front view, eye level, symmetrical composition",
            "측면": "side view, profile shot, lateral perspective",
            "조감": "aerial view, bird's eye view, overhead shot",
            "클로즈업": "close-up shot, detail view, macro perspective",
            "와이드": "wide angle, panoramic view, expansive shot"
        }

        # 카메라 무브먼트에 따른 키워드
        movement_keywords = {
            "고정": "static shot, steady frame",
            "팬": "panning motion blur, horizontal sweep",
            "틸트": "vertical sweep, looking up",
            "줌": "depth focus, zoom perspective",
            "트래킹": "tracking shot, follow through, dynamic movement"
        }

        angle_kw = angle_keywords.get(scene['angle'], '')
        movement_kw = movement_keywords.get(scene['movement'], '')

        prompt = f"architectural visualization, {project_info.get('building_type', 'modern building')}, {scene['description']}, {angle_kw}, {movement_kw}, professional architectural photography, hyperrealistic, 8k, high quality, cinematic lighting --ar 16:9 --v 6"

        prompts.append({
            'scene_number': i + 1,
            'scene_name': scene['name'],
            'prompt': prompt
        })

    return prompts


def main():
    st.title("Video Storyboard Generator")
    st.markdown("**건축 프로젝트 영상용 스토리보드 및 Narrative 생성**")
    st.markdown("---")

    # Session state 초기화
    if 'storyboard_scenes' not in st.session_state:
        st.session_state.storyboard_scenes = []
    if 'narratives' not in st.session_state:
        st.session_state.narratives = ""
    if 'scene_count_confirmed' not in st.session_state:
        st.session_state.scene_count_confirmed = False
    if 'video_settings_confirmed' not in st.session_state:
        st.session_state.video_settings_confirmed = False

    # 사이드바
    with st.sidebar:
        st.header("데이터 소스")

        data_source = st.radio(
            "데이터 소스 선택",
            ["Document Analysis 결과 활용", "직접 입력"]
        )

        if st.button("데이터 확인", type="secondary"):
            if data_source == "Document Analysis 결과 활용":
                analysis_data = load_analysis_data()
                if analysis_data:
                    st.success("Document Analysis 결과가 확인되었습니다.")
                else:
                    st.warning("Document Analysis 결과가 없습니다.")
            else:
                st.info("직접 입력 모드입니다.")

        st.markdown("---")
        st.header("영상 설정")

        video_type = st.selectbox("영상 유형", VIDEO_TYPES)
        video_length = st.selectbox("영상 길이", VIDEO_LENGTHS)
        target_audience = st.selectbox("타겟 관객", TARGET_AUDIENCES)
        mood = st.selectbox("분위기", MOODS)

        if st.button("설정 확인", type="secondary"):
            st.session_state.video_settings = {
                'type': video_type,
                'length': video_length,
                'audience': target_audience,
                'mood': mood
            }
            st.session_state.video_settings_confirmed = True
            st.success("영상 설정이 확인되었습니다.")

        st.markdown("---")
        st.header("Narrative 옵션")

        narrative_type = st.selectbox("Narrative 타입", NARRATIVE_TYPES)
        narrative_tone = st.selectbox("Narrative 톤", NARRATIVE_TONES)

    # 메인 컨텐츠 - 탭 구성
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "프로젝트 정보", "Scene 구성", "Narrative 생성", "스토리보드 미리보기", "다운로드"
    ])

    # 탭 1: 프로젝트 정보
    with tab1:
        st.header("프로젝트 정보")

        if data_source == "Document Analysis 결과 활용":
            analysis_data = load_analysis_data()
            if analysis_data and 'project_info' in analysis_data:
                project_info = analysis_data['project_info']

                col1, col2 = st.columns(2)
                with col1:
                    project_name = st.text_input("프로젝트명", value=project_info.get('project_name', ''))
                    location = st.text_input("위치", value=project_info.get('location', ''))
                with col2:
                    building_type = st.selectbox(
                        "건물 유형",
                        ["", "마스터플랜", "도시재생", "복합개발", "캠퍼스/연구단지", "산업단지", "주거단지", "상업/업무단지", "기타"]
                    )
                    owner = st.text_input("건축주", value=project_info.get('owner', ''))

                # CoT 히스토리 요약 표시
                if 'cot_history' in analysis_data and analysis_data['cot_history']:
                    with st.expander("분석 결과 요약"):
                        for i, history in enumerate(analysis_data['cot_history'][:5], 1):
                            st.write(f"**{i}단계**: {history.get('step', '')} - {history.get('summary', '')[:100]}...")
            else:
                st.warning("Document Analysis 결과가 없습니다. 직접 입력해주세요.")
                project_name = st.text_input("프로젝트명", value="")
                location = st.text_input("위치", value="")
                building_type = st.selectbox(
                    "건물 유형",
                    ["", "마스터플랜", "도시재생", "복합개발", "캠퍼스/연구단지", "산업단지", "주거단지", "상업/업무단지", "기타"]
                )
                owner = st.text_input("건축주", value="")
        else:
            col1, col2 = st.columns(2)
            with col1:
                project_name = st.text_input("프로젝트명", value="", placeholder="예: 서울시청 신청사")
                location = st.text_input("위치", value="", placeholder="예: 서울시 중구")
            with col2:
                building_type = st.selectbox(
                    "건물 유형",
                    ["", "마스터플랜", "도시재생", "복합개발", "캠퍼스/연구단지", "산업단지", "주거단지", "상업/업무단지", "기타"]
                )
                owner = st.text_input("건축주", value="", placeholder="예: 서울특별시")

        project_description = st.text_area(
            "프로젝트 설명",
            value="",
            placeholder="프로젝트의 주요 특징과 컨셉을 입력하세요",
            height=150
        )

        if st.button("프로젝트 정보 저장", type="primary"):
            st.session_state.storyboard_project_info = {
                'project_name': project_name,
                'location': location,
                'building_type': building_type,
                'owner': owner,
                'description': project_description
            }
            st.success("프로젝트 정보가 저장되었습니다.")

    # 탭 2: Scene 구성
    with tab2:
        st.header("Scene 구성")

        # 템플릿 선택
        st.subheader("템플릿 선택 (선택사항)")
        template_col1, template_col2 = st.columns([3, 1])
        with template_col1:
            selected_template = st.selectbox(
                "템플릿 선택",
                ["직접 구성"] + list(STORYBOARD_TEMPLATES.keys()),
                help="템플릿을 선택하면 기본 Scene이 자동으로 생성됩니다"
            )
        with template_col2:
            if st.button("템플릿 적용", type="secondary"):
                if selected_template != "직접 구성":
                    st.session_state.storyboard_scenes = STORYBOARD_TEMPLATES[selected_template].copy()
                    st.session_state.scene_count_confirmed = True
                    st.success(f"'{selected_template}' 템플릿이 적용되었습니다.")
                    st.rerun()

        st.markdown("---")

        # Scene 개수 설정
        st.subheader("Scene 개수 설정")
        scene_count = st.slider("Scene 개수", min_value=3, max_value=20, value=len(st.session_state.storyboard_scenes) if st.session_state.storyboard_scenes else 6)

        if st.button("Scene 개수 확인", type="secondary"):
            if len(st.session_state.storyboard_scenes) != scene_count:
                # Scene 개수 조정
                current_count = len(st.session_state.storyboard_scenes)
                if scene_count > current_count:
                    # Scene 추가
                    for i in range(current_count, scene_count):
                        st.session_state.storyboard_scenes.append({
                            'name': f'Scene {i+1}',
                            'description': '',
                            'angle': '정면',
                            'movement': '고정',
                            'duration': 5
                        })
                else:
                    # Scene 제거
                    st.session_state.storyboard_scenes = st.session_state.storyboard_scenes[:scene_count]
            st.session_state.scene_count_confirmed = True
            st.success(f"{scene_count}개의 Scene이 설정되었습니다.")
            st.rerun()

        # Scene 편집
        if st.session_state.scene_count_confirmed and st.session_state.storyboard_scenes:
            st.markdown("---")
            st.subheader("Scene 편집")

            for i, scene in enumerate(st.session_state.storyboard_scenes):
                with st.expander(f"Scene {i+1}: {scene.get('name', '')}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        new_name = st.text_input(
                            "Scene 이름",
                            value=scene.get('name', f'Scene {i+1}'),
                            key=f"scene_name_{i}"
                        )
                        new_description = st.text_area(
                            "장면 설명",
                            value=scene.get('description', ''),
                            key=f"scene_desc_{i}",
                            height=100
                        )

                    with col2:
                        new_angle = st.selectbox(
                            "촬영 각도",
                            CAMERA_ANGLES,
                            index=CAMERA_ANGLES.index(scene.get('angle', '정면')),
                            key=f"scene_angle_{i}"
                        )
                        new_movement = st.selectbox(
                            "카메라 움직임",
                            CAMERA_MOVEMENTS,
                            index=CAMERA_MOVEMENTS.index(scene.get('movement', '고정')),
                            key=f"scene_movement_{i}"
                        )
                        new_duration = st.number_input(
                            "예상 시간 (초)",
                            min_value=1,
                            max_value=60,
                            value=scene.get('duration', 5),
                            key=f"scene_duration_{i}"
                        )

                    # Scene 업데이트
                    st.session_state.storyboard_scenes[i] = {
                        'name': new_name,
                        'description': new_description,
                        'angle': new_angle,
                        'movement': new_movement,
                        'duration': new_duration
                    }

                    # Scene 순서 조정 및 삭제 버튼
                    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
                    with btn_col1:
                        if i > 0 and st.button("위로", key=f"up_{i}"):
                            st.session_state.storyboard_scenes[i], st.session_state.storyboard_scenes[i-1] = \
                                st.session_state.storyboard_scenes[i-1], st.session_state.storyboard_scenes[i]
                            st.rerun()
                    with btn_col2:
                        if i < len(st.session_state.storyboard_scenes) - 1 and st.button("아래로", key=f"down_{i}"):
                            st.session_state.storyboard_scenes[i], st.session_state.storyboard_scenes[i+1] = \
                                st.session_state.storyboard_scenes[i+1], st.session_state.storyboard_scenes[i]
                            st.rerun()
                    with btn_col3:
                        if st.button("Scene 추가", key=f"add_{i}"):
                            new_scene = {
                                'name': f'새 Scene',
                                'description': '',
                                'angle': '정면',
                                'movement': '고정',
                                'duration': 5
                            }
                            st.session_state.storyboard_scenes.insert(i+1, new_scene)
                            st.rerun()
                    with btn_col4:
                        if len(st.session_state.storyboard_scenes) > 3 and st.button("삭제", key=f"del_{i}"):
                            st.session_state.storyboard_scenes.pop(i)
                            st.rerun()

            # 총 시간 표시
            total_duration = sum(s.get('duration', 0) for s in st.session_state.storyboard_scenes)
            st.info(f"총 예상 시간: {total_duration}초 ({total_duration // 60}분 {total_duration % 60}초)")

    # 탭 3: Narrative 생성
    with tab3:
        st.header("Narrative 생성")

        if not st.session_state.storyboard_scenes:
            st.warning("먼저 Scene 구성을 완료해주세요.")
        else:
            st.subheader("현재 Scene 목록")
            for i, scene in enumerate(st.session_state.storyboard_scenes):
                st.write(f"**Scene {i+1}**: {scene.get('name', '')} - {scene.get('description', '')[:50]}...")

            st.markdown("---")

            if st.button("Narrative 생성", type="primary", use_container_width=True):
                project_info = st.session_state.get('storyboard_project_info', {})

                with st.spinner("Narrative를 생성하고 있습니다..."):
                    result = generate_narrative(
                        st.session_state.storyboard_scenes,
                        project_info,
                        narrative_type,
                        narrative_tone
                    )

                    if result['success']:
                        st.session_state.narratives = result['narratives']
                        st.success("Narrative가 생성되었습니다!")
                    else:
                        st.error(f"Narrative 생성 실패: {result.get('error', '알 수 없는 오류')}")

            # Narrative 결과 표시 및 편집
            if st.session_state.narratives:
                st.markdown("---")
                st.subheader("생성된 Narrative")

                edited_narratives = st.text_area(
                    "Narrative (편집 가능)",
                    value=st.session_state.narratives,
                    height=400
                )

                if st.button("Narrative 저장"):
                    st.session_state.narratives = edited_narratives
                    st.success("Narrative가 저장되었습니다.")

    # 탭 4: 스토리보드 미리보기
    with tab4:
        st.header("스토리보드 미리보기")

        if not st.session_state.storyboard_scenes:
            st.warning("먼저 Scene 구성을 완료해주세요.")
        else:
            # 뷰 선택
            view_mode = st.radio("뷰 모드", ["타임라인 뷰", "테이블 뷰"], horizontal=True)

            if view_mode == "타임라인 뷰":
                st.subheader("타임라인")

                cumulative_time = 0
                for i, scene in enumerate(st.session_state.storyboard_scenes):
                    col1, col2, col3 = st.columns([1, 4, 1])

                    with col1:
                        st.metric(f"Scene {i+1}", f"{scene.get('duration', 0)}초")

                    with col2:
                        st.write(f"**{scene.get('name', '')}**")
                        st.write(f"{scene.get('description', '')}")
                        st.caption(f"카메라: {scene.get('angle', '')} / {scene.get('movement', '')}")

                    with col3:
                        cumulative_time += scene.get('duration', 0)
                        st.caption(f"누적: {cumulative_time}초")

                    st.markdown("---")

            else:  # 테이블 뷰
                st.subheader("스토리보드 테이블")

                table_data = []
                cumulative_time = 0
                for i, scene in enumerate(st.session_state.storyboard_scenes):
                    cumulative_time += scene.get('duration', 0)
                    table_data.append({
                        "번호": i + 1,
                        "Scene 이름": scene.get('name', ''),
                        "설명": scene.get('description', ''),
                        "촬영 각도": scene.get('angle', ''),
                        "카메라 움직임": scene.get('movement', ''),
                        "시간(초)": scene.get('duration', 0),
                        "누적(초)": cumulative_time
                    })

                st.dataframe(table_data, use_container_width=True)

            # 프롬프트 생성 섹션
            st.markdown("---")
            st.subheader("Scene별 이미지 프롬프트")

            if st.button("Scene별 프롬프트 생성", type="secondary"):
                project_info = st.session_state.get('storyboard_project_info', {})
                prompts = generate_scene_prompts(st.session_state.storyboard_scenes, project_info)
                st.session_state.scene_prompts = prompts
                st.success("프롬프트가 생성되었습니다!")

            if 'scene_prompts' in st.session_state and st.session_state.scene_prompts:
                for prompt_data in st.session_state.scene_prompts:
                    with st.expander(f"Scene {prompt_data['scene_number']}: {prompt_data['scene_name']}"):
                        st.code(prompt_data['prompt'], language="text")

                # 전체 프롬프트 복사
                all_prompts = "\n\n".join([
                    f"Scene {p['scene_number']} ({p['scene_name']}):\n{p['prompt']}"
                    for p in st.session_state.scene_prompts
                ])

                st.download_button(
                    "전체 프롬프트 다운로드",
                    data=all_prompts,
                    file_name="storyboard_prompts.txt",
                    mime="text/plain"
                )

    # 탭 5: 다운로드
    with tab5:
        st.header("스토리보드 다운로드")

        if not st.session_state.storyboard_scenes:
            st.warning("먼저 Scene 구성을 완료해주세요.")
        else:
            st.subheader("다운로드 옵션")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Excel 다운로드**")
                st.caption("Scene 데이터를 편집 가능한 Excel 형식으로 다운로드")

                # Excel 데이터 생성
                excel_data = []
                cumulative_time = 0
                for i, scene in enumerate(st.session_state.storyboard_scenes):
                    cumulative_time += scene.get('duration', 0)
                    excel_data.append({
                        "번호": i + 1,
                        "Scene 이름": scene.get('name', ''),
                        "설명": scene.get('description', ''),
                        "촬영 각도": scene.get('angle', ''),
                        "카메라 움직임": scene.get('movement', ''),
                        "시간(초)": scene.get('duration', 0),
                        "누적(초)": cumulative_time,
                        "Narrative": ""  # Narrative 추가
                    })

                import pandas as pd
                df = pd.DataFrame(excel_data)

                # CSV로 다운로드 (Excel 대체)
                csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    "Excel/CSV 다운로드",
                    data=csv_data,
                    file_name=f"storyboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

            with col2:
                st.markdown("**JSON 다운로드**")
                st.caption("전체 스토리보드 데이터를 JSON 형식으로 다운로드")

                json_data = {
                    'project_info': st.session_state.get('storyboard_project_info', {}),
                    'video_settings': st.session_state.get('video_settings', {}),
                    'scenes': st.session_state.storyboard_scenes,
                    'narratives': st.session_state.narratives,
                    'created_at': datetime.now().isoformat()
                }

                st.download_button(
                    "JSON 다운로드",
                    data=json.dumps(json_data, ensure_ascii=False, indent=2),
                    file_name=f"storyboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

            with col3:
                st.markdown("**텍스트 다운로드**")
                st.caption("스토리보드를 텍스트 형식으로 다운로드")

                project_info = st.session_state.get('storyboard_project_info', {})
                text_content = f"""# 스토리보드
프로젝트: {project_info.get('project_name', 'N/A')}
위치: {project_info.get('location', 'N/A')}
건물 유형: {project_info.get('building_type', 'N/A')}
생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Scene 목록

"""
                cumulative_time = 0
                for i, scene in enumerate(st.session_state.storyboard_scenes):
                    cumulative_time += scene.get('duration', 0)
                    text_content += f"""### Scene {i+1}: {scene.get('name', '')}
- 설명: {scene.get('description', '')}
- 촬영 각도: {scene.get('angle', '')}
- 카메라 움직임: {scene.get('movement', '')}
- 시간: {scene.get('duration', 0)}초 (누적: {cumulative_time}초)

"""

                if st.session_state.narratives:
                    text_content += f"""---

## Narrative

{st.session_state.narratives}
"""

                st.download_button(
                    "텍스트 다운로드",
                    data=text_content,
                    file_name=f"storyboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )

    # 하단 정보
    st.markdown("---")
    st.markdown("""
    ### 사용 팁

    **데이터 소스:**
    - Document Analysis 결과를 활용하면 프로젝트 정보가 자동으로 로드됩니다
    - 직접 입력하여 새로운 프로젝트의 스토리보드를 생성할 수 있습니다

    **템플릿:**
    - 미리 정의된 템플릿을 사용하면 빠르게 시작할 수 있습니다
    - 템플릿을 적용한 후 필요에 따라 수정하세요

    **Scene 구성:**
    - 각 Scene의 촬영 각도와 카메라 움직임을 설정하세요
    - Scene 순서는 위/아래로 버튼으로 조정할 수 있습니다

    **Narrative:**
    - AI가 각 Scene에 맞는 Narrative를 자동 생성합니다
    - 생성된 Narrative는 편집 가능합니다

    **프롬프트:**
    - Scene별 이미지 프롬프트가 자동 생성됩니다
    - Midjourney에서 사용할 수 있는 형식으로 제공됩니다
    """)


if __name__ == "__main__":
    main()

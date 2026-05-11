import streamlit as st
import json
from datetime import datetime
import os
from dspy_analyzer import EnhancedArchAnalyzer
from file_analyzer import UniversalFileAnalyzer

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

# 상수 정의
CAMERA_ANGLES = ["정면", "측면", "조감", "클로즈업", "와이드", "아이소메트릭", "FPV 드론", "로우앵글"]
CAMERA_MOVEMENTS = ["고정", "팬 좌우", "틸트 상하", "줌 인", "줌 아웃", "트래킹", "달리 인", "달리 아웃", "크레인", "FPV 비행"]
NARRATIVE_TYPES = ["스토리텔링형", "설명형", "감성형", "기술 중심형"]
NARRATIVE_TONES = ["공식적", "친근한", "열정적", "차분한"]

# 오디오 키워드 정의
AUDIO_ATMOSPHERES = [
    "없음",
    "도시 앰비언스",  # ambient city noise, distant traffic, urban soundscape
    "자연 환경음",    # birds chirping, soft wind, rustling leaves
    "실내 정적",      # quiet indoor atmosphere, subtle room tone
    "활기찬 거리",    # bustling street, footsteps, people chatting
    "드라마틱 음악",  # cinematic orchestral, epic score
    "미니멀 음악",    # minimal ambient music, soft piano
    "테크/모던",      # modern electronic, tech ambience
]

# 카메라 앵글 영문 키워드 매핑
ANGLE_KEYWORDS = {
    "정면": "front view, eye level, symmetrical composition",
    "측면": "side view, profile shot, lateral perspective",
    "조감": "aerial view, bird's eye view, overhead shot, top-down perspective",
    "클로즈업": "close-up shot, detail view, macro perspective",
    "와이드": "wide angle, panoramic view, expansive shot, establishing shot",
    "아이소메트릭": "isometric view, 30-degree angle, axonometric projection",
    "FPV 드론": "FPV drone shot, first-person view, dynamic flight perspective",
    "로우앵글": "low angle shot, looking up, dramatic perspective, worm's eye view",
}

# 카메라 움직임 영문 키워드 매핑
MOVEMENT_KEYWORDS = {
    "고정": "static shot, steady frame, locked camera",
    "팬 좌우": "panning motion, horizontal sweep, left to right movement",
    "틸트 상하": "tilting motion, vertical sweep, looking up and down",
    "줌 인": "zoom in, push in, focus tightening",
    "줌 아웃": "zoom out, pull back, revealing shot",
    "트래킹": "tracking shot, follow through, dynamic movement, dolly alongside",
    "달리 인": "dolly in, camera approaching, forward movement",
    "달리 아웃": "dolly out, camera retreating, backward movement",
    "크레인": "crane shot, vertical elevation change, sweeping overhead",
    "FPV 비행": "FPV flight, gliding motion, smooth aerial traversal",
}

# 오디오 영문 키워드 매핑
AUDIO_KEYWORDS = {
    "없음": "",
    "도시 앰비언스": "ambient city noise, distant traffic, urban soundscape",
    "자연 환경음": "birds chirping, soft wind noise, rustling leaves, nature ambience",
    "실내 정적": "quiet indoor atmosphere, subtle room tone, soft silence",
    "활기찬 거리": "bustling street sounds, footsteps on pavement, people chatting",
    "드라마틱 음악": "cinematic orchestral score, epic dramatic music",
    "미니멀 음악": "minimal ambient music, soft piano notes, gentle melody",
    "테크/모던": "modern electronic ambience, tech soundscape, digital tones",
}

# 템플릿 정의 (예시용)
STORYBOARD_TEMPLATES = {
    "마스터플랜 기본 (예시)": [
        {
            "name": "대상지 위치",
            "description": "도시 전체 위성 뷰에서 시작해 대상지를 향해 서서히 줌인 — 주변 도로망·하천·건물군 사이로 경계가 드러남",
            "angle": "조감", "movement": "줌 인", "duration": 5, "audio": "도시 앰비언스"
        },
        {
            "name": "마스터플랜 전체도",
            "description": "줌인이 멈추며 빈 대지 위로 마스터플랜 배치도가 선으로 그려지듯 나타남 — 카메라가 천천히 좌우로 쓸며 전체 규모를 파악",
            "angle": "조감", "movement": "팬 좌우", "duration": 6, "audio": "미니멀 음악"
        },
        {
            "name": "토지이용계획",
            "description": "팬이 중앙에서 멈추며 배치도 위로 용도별 컬러가 레이어처럼 하나씩 켜짐 — 주거·상업·공원·업무 구역이 순서대로 채워지며 면적 배분을 시각화",
            "angle": "조감", "movement": "고정", "duration": 5, "audio": "미니멀 음악"
        },
        {
            "name": "동선 체계",
            "description": "컬러 존 위로 차량·보행 동선이 빛의 흐름처럼 활성화됨 — 간선도로에서 골목까지 위계적으로 연결되는 네트워크 흐름",
            "angle": "조감", "movement": "고정", "duration": 5, "audio": "도시 앰비언스"
        },
        {
            "name": "오픈스페이스 체계",
            "description": "동선 레이어 위에 공원·광장·녹지축이 겹쳐지며 그린 네트워크가 도시 전체를 연결 — 카메라가 녹지 흐름을 따라 대각선으로 팬",
            "angle": "조감", "movement": "팬 좌우", "duration": 5, "audio": "자연 환경음"
        },
        {
            "name": "주요 시설 배치",
            "description": "녹지 네트워크 위로 핵심 건물들이 하나씩 매스로 솟아오르며 하이라이트됨 — 카메라가 가장 중심 시설로 줌인하며 마무리",
            "angle": "조감", "movement": "줌 인", "duration": 5, "audio": "드라마틱 음악"
        },
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


def parse_scene_narratives(narratives_text, scene_count):
    """생성된 Narrative 텍스트를 씬별로 파싱 (볼드 헤더 / 마크다운 테이블 모두 지원)"""
    import re
    scene_narratives = {}

    # 방법 1: **Scene N: [이름]** 패턴
    pattern = r'\*\*Scene\s+(\d+):\s*([^\*]+?)\*\*\s*\n(.*?)(?=\n\*\*Scene\s+\d+:|$)'
    matches = re.findall(pattern, narratives_text, re.DOTALL)
    for match in matches:
        scene_num = int(match[0])
        scene_narratives[scene_num] = match[2].strip()

    # 방법 2: 마크다운 테이블 파싱 (| Scene N | 이름 | 내용 | Narrative |)
    if not scene_narratives:
        table_rows = re.findall(
            r'^\|\s*Scene\s+(\d+)\s*\|[^|]*\|[^|]*\|\s*(.+?)\s*\|?\s*$',
            narratives_text, re.MULTILINE
        )
        for match in table_rows:
            narrative = match[1].strip()
            if narrative and not narrative.lower().startswith('narrative'):
                scene_narratives[int(match[0])] = narrative

    print(f"[DEBUG] 파싱: {len(scene_narratives)}개 씬 (기대: {scene_count}개)")
    return scene_narratives


def summarize_pdf_for_storyboard(pdf_text):
    """영상 스토리보드 나레이션 목적에 맞게 PDF를 요약"""
    prompt = f"""당신은 건축 영상 제작 전문가입니다. 아래 건축 프로젝트 문서를 영상 스토리보드 나레이션 작성 목적으로 요약해주세요.

## 요약 목적
- 영상 스토리보드의 각 씬(Scene) 나레이션 작성에 활용
- 영상 감독이 장면별 설명을 쓸 때 참고할 핵심 정보 추출

## 반드시 포함할 항목
1. **설계 개념/철학**: 프로젝트의 핵심 컨셉과 비전
2. **공간 구성**: 주요 공간, 동선, 배치 특징
3. **분위기/감성**: 프로젝트가 전달하려는 감성과 분위기
4. **핵심 시설/랜드마크**: 영상에 담길 주요 요소들
5. **맥락/배경**: 입지, 주변 환경, 프로젝트 의의

## 출력 형식
- 총 400~600자 이내
- 항목별 핵심 문장 위주 (나레이션 작성자가 바로 활용 가능하도록)
- 불필요한 수치·행정 정보는 제외

## 문서 내용
{pdf_text[:15000]}{'...(이하 생략)' if len(pdf_text) > 15000 else ''}
"""

    try:
        analyzer = EnhancedArchAnalyzer()
        result = analyzer.analyze_custom_block(prompt, "")

        if result['success']:
            return {'success': True, 'summary': result['analysis'], 'model': result['model']}
        else:
            return {'success': False, 'error': result.get('error', '알 수 없는 오류')}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def generate_narrative(scenes, project_info, narrative_type, narrative_tone, pdf_content=""):
    """AI를 사용하여 각 Scene에 대한 Narrative 생성"""

    scenes_text = ""
    for i, s in enumerate(scenes):
        prev_name = scenes[i-1]['name'] if i > 0 else None
        next_name = scenes[i+1]['name'] if i < len(scenes) - 1 else None
        link_info = ""
        if prev_name:
            link_info += f" | 이전: {prev_name}"
        if next_name:
            link_info += f" | 다음: {next_name}"
        scenes_text += f"- Scene {i+1} ({s['name']}): {s['description']} / 카메라: {s['angle']}, {s['movement']} / {s['duration']}초{link_info}\n"

    pdf_section = ""
    if pdf_content:
        pdf_section = f"\n## PDF 문서 내용 (참고)\n{pdf_content[:8000]}{'...' if len(pdf_content) > 8000 else ''}\n"

    prompt = f"""
당신은 건축 영상 제작 전문가입니다. 아래 스토리보드의 각 Scene에 대해 Narrative(나레이션/해설)를 작성해주세요.

## 프로젝트 정보
- 프로젝트명: {project_info.get('project_name', 'N/A')}
- 위치: {project_info.get('location', 'N/A')}
- 건물 유형: {project_info.get('building_type', 'N/A')}
{pdf_section}

## Narrative 스타일
- 유형: {narrative_type}
- 톤: {narrative_tone}

## Scene 목록 (각 씬에 이전/다음 씬 정보 포함)
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
3. **각 씬의 나레이션은 이전 씬에서 자연스럽게 이어지도록** — 첫 문장은 이전 씬의 흐름을 받아 전환하고, 마지막 문장은 다음 씬을 암시하거나 연결
4. 전체 영상이 하나의 흐름으로 읽혀야 함 (씬을 잘라도 각 나레이션이 독립적으로 읽히면 안 됨)
5. 건축적 특징과 공간의 분위기 강조
"""

    try:
        analyzer = EnhancedArchAnalyzer()
        result = analyzer.analyze_custom_block(prompt, "")

        if result['success']:
            # Narrative를 씬별로 파싱
            scene_narratives = parse_scene_narratives(result['analysis'], len(scenes))

            return {
                'success': True,
                'narratives': result['analysis'],
                'scene_narratives': scene_narratives,
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


def generate_scene_prompts(scenes, project_info, include_timeline=True):
    """각 Scene에 대한 AI 영상/이미지 프롬프트 생성

    Args:
        scenes: Scene 목록
        project_info: 프로젝트 정보
        include_timeline: 타임라인 스크립트 문법 포함 여부 (Kling AI 등 지원)
    """
    prompts = []
    cumulative_time = 0

    for i, scene in enumerate(scenes):
        # 상단 상수에서 키워드 가져오기
        angle_kw = ANGLE_KEYWORDS.get(scene['angle'], '')
        movement_kw = MOVEMENT_KEYWORDS.get(scene['movement'], '')
        audio_kw = AUDIO_KEYWORDS.get(scene.get('audio', '없음'), '')

        duration = scene.get('duration', 5)
        start_time = cumulative_time
        end_time = cumulative_time + duration

        # 이전/다음 씬 컨텍스트
        prev_scene = scenes[i - 1] if i > 0 else None
        next_scene = scenes[i + 1] if i < len(scenes) - 1 else None
        prev_movement_kw = MOVEMENT_KEYWORDS.get(prev_scene['movement'], '') if prev_scene else ''
        next_movement_kw = MOVEMENT_KEYWORDS.get(next_scene['movement'], '') if next_scene else ''

        # 씬 연결 컨텍스트 문자열
        transition_context = ""
        if prev_scene:
            transition_context += f"continuing from previous scene ({prev_scene['name']}: {prev_movement_kw}), "
        if next_scene:
            transition_context += f"transitioning into next scene ({next_scene['name']}: {next_movement_kw})"

        # 기본 이미지 프롬프트 (Midjourney 호환)
        base_prompt = f"architectural visualization, {project_info.get('building_type', 'modern building')}, {scene['description']}, {angle_kw}, {movement_kw}, professional architectural photography, hyperrealistic, 8k, high quality, cinematic lighting"

        # Midjourney 프롬프트
        midjourney_prompt = f"{base_prompt} --ar 16:9 --v 6"

        # 타임라인 스크립트 프롬프트 (Kling AI, Runway 등 영상 AI용)
        timeline_prompt = ""
        if include_timeline:
            timeline_prompt = f"[{start_time}~{end_time}s] {scene['description']}. Camera: {movement_kw}. View: {angle_kw}."
            if transition_context:
                timeline_prompt += f" Transition: {transition_context}."
            if audio_kw:
                timeline_prompt += f" Audio: {audio_kw}."

        # 영상 AI용 통합 프롬프트 (씬 연결 + 물리적 상호작용 포함)
        video_prompt = f"[Camera] {movement_kw}, {angle_kw}. [Scene] {scene['description']}, architectural visualization of {project_info.get('building_type', 'modern building')}."
        if transition_context:
            video_prompt += f" [Transition] {transition_context}."
        video_prompt += " [Physics] Subtle environmental movement, realistic lighting transitions. [Tech] 4k resolution, cinematic lighting, photorealistic, fluid motion."
        if audio_kw:
            video_prompt += f" [Audio] {audio_kw}."

        prompts.append({
            'scene_number': i + 1,
            'scene_name': scene['name'],
            'prompt': midjourney_prompt,  # 기존 호환성 유지
            'midjourney_prompt': midjourney_prompt,
            'timeline_prompt': timeline_prompt,
            'video_prompt': video_prompt,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration
        })

        cumulative_time = end_time

    return prompts


def parse_scene_prompts_ai(response_text, scene_count):
    """AI 응답에서 씬별 이미지/비디오 프롬프트 파싱"""
    import re
    result = {}

    image_pattern = r'\*\*Scene\s+(\d+)\s*-\s*Image:\*\*\s*\n(.*?)(?=\n\*\*Scene\s+\d+|$)'
    for match in re.findall(image_pattern, response_text, re.DOTALL):
        scene_num = int(match[0])
        result.setdefault(scene_num, {})['image'] = match[1].strip()

    video_pattern = r'\*\*Scene\s+(\d+)\s*-\s*Video:\*\*\s*\n(.*?)(?=\n\*\*Scene\s+\d+|$)'
    for match in re.findall(video_pattern, response_text, re.DOTALL):
        scene_num = int(match[0])
        result.setdefault(scene_num, {})['video'] = match[1].strip()

    print(f"[DEBUG] 프롬프트 파싱: {len(result)}개 씬 (기대: {scene_count}개)")
    return result


def generate_scene_prompts_with_ai(scenes, project_info, pdf_summary=""):
    """AI를 사용해 각 Scene에 대한 이미지(Midjourney)/비디오(Kling·Runway) 프롬프트 생성.
    실패 시 키워드 조합 방식으로 자동 fallback.
    """
    scenes_text = ""
    cumulative_time = 0
    for i, scene in enumerate(scenes):
        duration = scene.get('duration', 5)
        start_time = cumulative_time
        end_time = cumulative_time + duration
        angle_kw = ANGLE_KEYWORDS.get(scene['angle'], '')
        movement_kw = MOVEMENT_KEYWORDS.get(scene['movement'], '')
        audio_kw = AUDIO_KEYWORDS.get(scene.get('audio', '없음'), '')
        prev_name = scenes[i - 1]['name'] if i > 0 else None
        next_name = scenes[i + 1]['name'] if i < len(scenes) - 1 else None

        scenes_text += f"Scene {i + 1} ({scene['name']}, {start_time}~{end_time}s):\n"
        scenes_text += f"  설명: {scene['description']}\n"
        scenes_text += f"  카메라: {scene['angle']} ({angle_kw}), {scene['movement']} ({movement_kw})\n"
        scenes_text += f"  오디오: {scene.get('audio', '없음')} ({audio_kw})\n"
        if prev_name:
            scenes_text += f"  이전 씬: {prev_name}\n"
        if next_name:
            scenes_text += f"  다음 씬: {next_name}\n"
        scenes_text += "\n"
        cumulative_time = end_time

    pdf_section = f"\n## 프로젝트 컨텍스트 (PDF 요약)\n{pdf_summary}\n" if pdf_summary else ""

    prompt = f"""당신은 건축 영상 제작 및 AI 이미지/영상 생성 전문가입니다.
아래 스토리보드 씬들에 대해 이미지 AI(Midjourney)와 영상 AI(Kling AI/Runway)에 최적화된 프롬프트를 작성해주세요.

## 프로젝트 정보
- 프로젝트명: {project_info.get('project_name', 'N/A')}
- 건물 유형: {project_info.get('building_type', 'N/A')}
- 위치: {project_info.get('location', 'N/A')}
{pdf_section}
## 씬 목록
{scenes_text}
## 출력 형식 (반드시 준수)

**Scene 1 - Image:**
[Midjourney 프롬프트]

**Scene 1 - Video:**
[Kling/Runway 프롬프트]

**Scene 2 - Image:**
...

## 작성 가이드라인

### 이미지 프롬프트 (Midjourney):
- 영어 키워드를 쉼표로 나열
- 건축물의 재료·분위기·조명을 구체적으로 명시
- 카메라 앵글을 Midjourney 키워드로 표현 (예: bird's eye view, low angle shot)
- 품질 키워드 포함: photorealistic, cinematic, 8k, high detail, golden hour lighting 등
- 마지막에 --ar 16:9 --v 6 추가
- PDF 컨텍스트의 설계 개념·분위기를 반영

### 비디오 프롬프트 (Kling/Runway):
- 자연스러운 영어 문장으로 서술
- 카메라 움직임을 명확히 묘사 (예: The camera slowly dollies forward...)
- 씬의 시작 상태 → 끝 상태 흐름 포함
- 이전·다음 씬과의 연결감 반영
- 오디오 분위기가 있으면 반영
- 빛·바람·그림자 등 물리적 현실감 포함
"""

    try:
        analyzer = EnhancedArchAnalyzer()
        result = analyzer.analyze_custom_block(prompt, "")

        if result['success']:
            parsed = parse_scene_prompts_ai(result['analysis'], len(scenes))

            prompts = []
            cumulative_time = 0
            for i, scene in enumerate(scenes):
                duration = scene.get('duration', 5)
                start_time = cumulative_time
                end_time = cumulative_time + duration
                scene_num = i + 1
                movement_kw = MOVEMENT_KEYWORDS.get(scene['movement'], '')
                angle_kw = ANGLE_KEYWORDS.get(scene['angle'], '')
                audio_kw = AUDIO_KEYWORDS.get(scene.get('audio', '없음'), '')

                scene_data = parsed.get(scene_num, {})
                midjourney_prompt = scene_data.get('image', '')
                video_prompt = scene_data.get('video', '')

                timeline_prompt = f"[{start_time}~{end_time}s] {scene['description']}. Camera: {movement_kw}. View: {angle_kw}."
                if audio_kw:
                    timeline_prompt += f" Audio: {audio_kw}."

                prompts.append({
                    'scene_number': scene_num,
                    'scene_name': scene['name'],
                    'prompt': midjourney_prompt,
                    'midjourney_prompt': midjourney_prompt,
                    'video_prompt': video_prompt,
                    'timeline_prompt': timeline_prompt,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration
                })
                cumulative_time = end_time

            return {'success': True, 'prompts': prompts, 'model': result['model']}
        else:
            return {'success': False, 'error': result.get('error', '알 수 없는 오류')}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def generate_full_timeline_script(scenes, project_info):
    """전체 영상에 대한 타임라인 스크립트 생성 (Kling AI 등 지원)"""
    script_lines = []
    cumulative_time = 0

    script_lines.append(f"# {project_info.get('project_name', 'Architectural Project')} - Video Timeline Script")
    script_lines.append(f"# Total Duration: {sum(s.get('duration', 5) for s in scenes)}s")
    script_lines.append("")

    for i, scene in enumerate(scenes):
        duration = scene.get('duration', 5)
        start_time = cumulative_time
        end_time = cumulative_time + duration

        angle_kw = ANGLE_KEYWORDS.get(scene['angle'], '')
        movement_kw = MOVEMENT_KEYWORDS.get(scene['movement'], '')
        audio_kw = AUDIO_KEYWORDS.get(scene.get('audio', '없음'), '')

        line = f"{start_time}~{end_time}s: {scene['description']}. {movement_kw}. {angle_kw}."
        if audio_kw:
            line += f" ({audio_kw})"

        script_lines.append(line)
        cumulative_time = end_time

    return "\n".join(script_lines)


def main():
    st.title("Video Storyboard Generator")
    st.markdown("**건축 프로젝트 영상용 스토리보드 및 나레이션 생성**")
    st.markdown("---")

    # Session state 초기화
    if 'storyboard_scenes' not in st.session_state:
        st.session_state.storyboard_scenes = []
    if 'narratives' not in st.session_state:
        st.session_state.narratives = ""
    if 'scene_narratives' not in st.session_state:
        st.session_state.scene_narratives = {}
    if 'scene_count_confirmed' not in st.session_state:
        st.session_state.scene_count_confirmed = False
    if '_narrative_applied_count' not in st.session_state:
        st.session_state._narrative_applied_count = None
    if '_narrative_generated' not in st.session_state:
        st.session_state._narrative_generated = False
    if '_narrative_error' not in st.session_state:
        st.session_state._narrative_error = None
    if '_prompt_status' not in st.session_state:
        st.session_state._prompt_status = None

    # 사이드바
    with st.sidebar:
        st.header("데이터 소스")

        data_source = st.radio(
            "데이터 소스 선택",
            ["PDF 업로드", "직접 입력"]
        )

        if data_source == "PDF 업로드":
            uploaded_pdf = st.file_uploader("PDF 파일 업로드", type=['pdf'], key="storyboard_pdf")
            if uploaded_pdf is not None:
                _file_id = getattr(uploaded_pdf, "file_id", None) or uploaded_pdf.name
                _already = (
                    st.session_state.get("_storyboard_pdf_id") == _file_id
                    and st.session_state.get("storyboard_pdf_text")
                )
                if _already:
                    st.success(f"PDF 분석 완료! ({len(st.session_state.storyboard_pdf_text)}자)")
                    st.info(f"파일명: {uploaded_pdf.name}")
                    if st.session_state.get("_storyboard_pdf_sum_id") != _file_id:
                        with st.spinner("스토리보드용 요약 생성 중..."):
                            sum_result = summarize_pdf_for_storyboard(st.session_state.storyboard_pdf_text)
                            if sum_result['success']:
                                st.session_state.storyboard_pdf_summary = sum_result['summary']
                            else:
                                st.warning("요약 생성 실패 — 원문을 사용합니다.")
                            # 성공/실패 무관하게 재시도 방지
                            st.session_state["_storyboard_pdf_sum_id"] = _file_id
                else:
                    extracted_text = None
                    with st.spinner("PDF 분석 중..."):
                        try:
                            analyzer = UniversalFileAnalyzer()
                            pdf_bytes = uploaded_pdf.read()
                            result = analyzer.analyze_file_from_bytes(pdf_bytes, "pdf", uploaded_pdf.name)
                            if result['success']:
                                pdf_text = result['text']
                                if pdf_text and len(pdf_text.strip()) > 0:
                                    extracted_text = pdf_text.strip()
                                    st.session_state.storyboard_pdf_text = extracted_text
                                    st.session_state['storyboard_uploaded_pdf'] = uploaded_pdf
                                    st.session_state["_storyboard_pdf_id"] = _file_id
                                    st.success(f"PDF 분석 완료! ({len(extracted_text)}자)")
                                    st.info(f"파일명: {uploaded_pdf.name}")
                                    if 'metadata' in result:
                                        st.caption(f"페이지 수: {result['metadata'].get('page_count', 'N/A')}")
                                else:
                                    st.error("PDF에서 텍스트를 추출할 수 없습니다.")
                            else:
                                st.error(f"PDF 분석 실패: {result.get('error', '알 수 없는 오류')}")
                        except Exception as e:
                            st.error(f"PDF 분석 실패: {str(e)}")
                    if extracted_text:
                        with st.spinner("스토리보드용 요약 생성 중..."):
                            sum_result = summarize_pdf_for_storyboard(extracted_text)
                            if sum_result['success']:
                                st.session_state.storyboard_pdf_summary = sum_result['summary']
                                st.session_state["_storyboard_pdf_sum_id"] = _file_id
                            else:
                                st.warning("요약 생성 실패 — 원문을 사용합니다.")
        else:
            st.info("직접 입력 모드입니다.")

        st.markdown("---")
        st.header("나레이션 옵션")

        narrative_type = st.selectbox("나레이션 타입", NARRATIVE_TYPES)
        narrative_tone = st.selectbox("나레이션 톤", NARRATIVE_TONES)

    # 메인 컨텐츠 - 탭 구성
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "프로젝트 정보", "Scene 구성", "나레이션 생성", "스토리보드 미리보기", "다운로드"
    ])

    # 탭 1: 프로젝트 정보
    with tab1:
        st.header("프로젝트 정보")

        if data_source == "PDF 업로드":
            uploaded_pdf = st.session_state.get('storyboard_uploaded_pdf')
            if uploaded_pdf:
                st.success(f"업로드된 PDF: {uploaded_pdf.name}")
            pdf_text_preview = st.session_state.get('storyboard_pdf_text', '')
            if pdf_text_preview:
                with st.expander("PDF 내용 미리보기"):
                    st.text(pdf_text_preview[:1000] + "..." if len(pdf_text_preview) > 1000 else pdf_text_preview)

                pdf_summary = st.session_state.get('storyboard_pdf_summary', '')
                if pdf_summary:
                    st.markdown("**나레이션용 요약** (편집 후 저장 가능)")
                    edited_summary = st.text_area(
                        "요약",
                        value=pdf_summary,
                        height=200,
                        key="pdf_summary_editor",
                        label_visibility="collapsed"
                    )
                    if st.button("요약 저장", key="save_summary"):
                        st.session_state.storyboard_pdf_summary = edited_summary
                        st.toast("요약이 저장되었습니다.", icon="✅")
                    st.info("이 요약이 나레이션 생성에 활용됩니다. 필요시 편집 후 저장하세요.")
                else:
                    st.info("PDF 내용이 나레이션 생성에 자동으로 활용됩니다. 아래 필드를 추가로 채워주세요.")
            else:
                st.info("PDF에서 프로젝트 정보를 추출하여 아래 필드를 채워주세요.")

            col1, col2 = st.columns(2)
            with col1:
                project_name = st.text_input("프로젝트명", value="", key="pdf_project_name")
                location = st.text_input("위치", value="", key="pdf_location")
            with col2:
                building_type = st.selectbox(
                    "건물 유형",
                    ["", "마스터플랜", "도시재생", "복합개발", "캠퍼스/연구단지", "산업단지", "주거단지", "상업/업무단지", "기타"],
                    key="pdf_building_type"
                )
                owner = st.text_input("건축주", value="", key="pdf_owner")
        else:
            col1, col2 = st.columns(2)
            with col1:
                project_name = st.text_input("프로젝트명", value="", placeholder="예: 서울시청 신청사", key="direct_project_name")
                location = st.text_input("위치", value="", placeholder="예: 서울시 중구", key="direct_location")
            with col2:
                building_type = st.selectbox(
                    "건물 유형",
                    ["", "마스터플랜", "도시재생", "복합개발", "캠퍼스/연구단지", "산업단지", "주거단지", "상업/업무단지", "기타"],
                    key="direct_building_type"
                )
                owner = st.text_input("건축주", value="", placeholder="예: 서울특별시", key="direct_owner")

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

        st.info("Scene을 직접 추가하고 편집하세요. 참고용 예시 템플릿을 적용할 수도 있습니다.")

        # 예시 템플릿 적용 (선택사항)
        with st.expander("📋 예시 템플릿 참고하기", expanded=False):
            st.caption("마스터플랜 프로젝트의 일반적인 Scene 구성 예시입니다. 적용 후 자유롭게 수정하세요.")
            template_col1, template_col2 = st.columns([3, 1])
            with template_col1:
                selected_template = st.selectbox(
                    "예시 템플릿",
                    list(STORYBOARD_TEMPLATES.keys()),
                    help="예시를 적용한 후 자유롭게 수정할 수 있습니다"
                )
            with template_col2:
                if st.button("예시 적용", type="secondary"):
                    import copy
                    st.session_state.storyboard_scenes = copy.deepcopy(STORYBOARD_TEMPLATES[selected_template])
                    st.session_state.scene_count_confirmed = True
                    st.toast(f"'{selected_template}' 예시가 적용되었습니다.", icon="✅")

        st.markdown("---")

        # Scene 직접 구성
        st.subheader("Scene 목록")

        # Scene 추가/초기화 버튼
        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
        with btn_col1:
            if st.button("➕ Scene 추가", use_container_width=True):
                scene_num = len(st.session_state.storyboard_scenes) + 1
                st.session_state.storyboard_scenes.append({
                    'name': f'Scene {scene_num}',
                    'description': '',
                    'angle': '정면',
                    'movement': '고정',
                    'audio': '없음',
                    'duration': 5,
                    'narrative': ''
                })
                st.session_state.scene_count_confirmed = True
                st.rerun()
        with btn_col2:
            if st.button("🗑️ 전체 초기화", use_container_width=True):
                st.session_state.storyboard_scenes = []
                st.session_state.scene_count_confirmed = False
                st.rerun()
        with btn_col3:
            current_count = len(st.session_state.storyboard_scenes)
            st.caption(f"현재 {current_count}개 Scene")

        # Scene 편집
        if st.session_state.storyboard_scenes:
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
                        new_audio = st.selectbox(
                            "오디오 분위기",
                            AUDIO_ATMOSPHERES,
                            index=AUDIO_ATMOSPHERES.index(scene.get('audio', '없음')),
                            key=f"scene_audio_{i}"
                        )
                        new_duration = st.number_input(
                            "예상 시간 (초)",
                            min_value=1,
                            max_value=60,
                            value=scene.get('duration', 5),
                            key=f"scene_duration_{i}"
                        )

                    # Scene 업데이트 (기존 narrative 보존)
                    st.session_state.storyboard_scenes[i] = {
                        'name': new_name,
                        'description': new_description,
                        'angle': new_angle,
                        'movement': new_movement,
                        'audio': new_audio,
                        'duration': new_duration,
                        'narrative': scene.get('narrative', '')  # 기존 narrative 보존
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
                                'audio': '없음',
                                'duration': 5,
                                'narrative': ''
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

            # Scene 편집 완료 버튼
            st.markdown("---")
            if st.button("✅ Scene 편집 완료", type="primary", use_container_width=True):
                st.session_state.scene_count_confirmed = True
                st.success("Scene 편집이 완료되었습니다. '나레이션 생성' 탭으로 이동하세요.")
        else:
            st.info("위의 '➕ Scene 추가' 버튼을 클릭하여 Scene을 추가하세요.")

    # 탭 3: 나레이션 생성
    with tab3:
        st.header("나레이션 생성")

        if not st.session_state.storyboard_scenes:
            st.warning("먼저 Scene 구성을 완료해주세요.")
        else:
            st.subheader("현재 Scene 목록")
            for i, scene in enumerate(st.session_state.storyboard_scenes):
                st.write(f"**Scene {i+1}**: {scene.get('name', '')} - {scene.get('description', '')[:50]}...")

            st.markdown("---")

            if st.button("나레이션 생성", type="primary", use_container_width=True):
                project_info = st.session_state.get('storyboard_project_info', {})
                with st.spinner("나레이션을 생성하고 있습니다..."):
                    pdf_content = st.session_state.get('storyboard_pdf_summary') or st.session_state.get('storyboard_pdf_text', '')
                    result = generate_narrative(
                        st.session_state.storyboard_scenes,
                        project_info,
                        narrative_type,
                        narrative_tone,
                        pdf_content=pdf_content
                    )

                if result['success']:
                    st.session_state.narratives = result['narratives']
                    st.session_state._narrative_generated = True
                    st.session_state._narrative_applied_count = None
                    st.session_state._narrative_error = None
                else:
                    st.session_state._narrative_generated = False
                    st.session_state._narrative_error = result.get('error', '알 수 없는 오류')

            # 결과 상태 표시 (button 블록 밖)
            if st.session_state._narrative_error:
                st.error(f"나레이션 생성 실패: {st.session_state._narrative_error}")
            elif st.session_state._narrative_applied_count is not None:
                st.success(f"저장 완료! {st.session_state._narrative_applied_count}개 씬에 적용됨")
            elif st.session_state._narrative_generated:
                st.success("나레이션이 생성되었습니다. 아래에서 확인·편집 후 저장하세요.")

            # Narrative 결과 표시 및 편집
            if st.session_state.narratives:
                st.markdown("---")
                st.subheader("생성된 나레이션")

                edited_narratives = st.text_area(
                    "나레이션 (편집 가능)",
                    value=st.session_state.narratives,
                    height=400
                )

                if st.button("나레이션 저장 및 씬 적용", type="primary"):
                    st.session_state.narratives = edited_narratives
                    parsed = parse_scene_narratives(edited_narratives, len(st.session_state.storyboard_scenes))
                    applied = 0
                    for i in range(len(st.session_state.storyboard_scenes)):
                        if (i + 1) in parsed:
                            st.session_state.storyboard_scenes[i]['narrative'] = parsed[i + 1]
                            applied += 1
                    st.session_state._narrative_applied_count = applied
                    if applied == 0:
                        st.session_state._narrative_error = "씬 자동 매칭 실패 — 나레이션 형식을 확인하세요."
                    else:
                        st.session_state._narrative_error = None

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

                        # Narrative 표시 (있는 경우)
                        narrative = scene.get('narrative', '').strip()
                        if narrative:
                            st.info(f"**나레이션:** {narrative}")
                        else:
                            st.caption("⚠️ 나레이션 미생성")

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
                        "나레이션": scene.get('narrative', ''),
                        "촬영 각도": scene.get('angle', ''),
                        "카메라 움직임": scene.get('movement', ''),
                        "시간(초)": scene.get('duration', 0),
                        "누적(초)": cumulative_time
                    })

                st.dataframe(table_data, use_container_width=True)

            # 프롬프트 생성 섹션
            st.markdown("---")
            st.subheader("Scene별 이미지 / 비디오 프롬프트")

            if st.button("Scene별 프롬프트 생성 (AI)", type="secondary"):
                project_info = st.session_state.get('storyboard_project_info', {})
                pdf_summary = st.session_state.get('storyboard_pdf_summary', '')
                with st.spinner("AI가 프롬프트를 생성하고 있습니다..."):
                    ai_result = generate_scene_prompts_with_ai(
                        st.session_state.storyboard_scenes, project_info, pdf_summary
                    )
                if ai_result['success']:
                    st.session_state.scene_prompts = ai_result['prompts']
                    st.session_state._prompt_status = ('success', ai_result.get('model', 'AI'))
                else:
                    prompts = generate_scene_prompts(st.session_state.storyboard_scenes, project_info)
                    st.session_state.scene_prompts = prompts
                    st.session_state._prompt_status = ('fallback', ai_result.get('error', ''))

            # 결과 상태 표시 (button 블록 밖)
            if st.session_state._prompt_status:
                status_type, status_val = st.session_state._prompt_status
                if status_type == 'success':
                    st.success(f"프롬프트 생성 완료! (모델: {status_val})")
                elif status_type == 'fallback':
                    st.warning(f"AI 생성 실패 — 키워드 방식으로 대체했습니다. ({status_val})")

            if 'scene_prompts' in st.session_state and st.session_state.scene_prompts:
                for prompt_data in st.session_state.scene_prompts:
                    with st.expander(f"Scene {prompt_data['scene_number']}: {prompt_data['scene_name']}"):
                        st.markdown("**이미지 프롬프트:**")
                        st.code(prompt_data['prompt'], language="text")

                        if prompt_data.get('video_prompt'):
                            st.markdown("**비디오 프롬프트:**")
                            st.code(prompt_data['video_prompt'], language="text")

                        if prompt_data.get('timeline_prompt'):
                            st.markdown("**타임라인 스크립트:**")
                            st.code(prompt_data['timeline_prompt'], language="text")

                # 전체 타임라인 스크립트 생성 및 표시
                project_info_for_timeline = st.session_state.get('storyboard_project_info', {})
                full_timeline = generate_full_timeline_script(st.session_state.storyboard_scenes, project_info_for_timeline)
                if full_timeline:
                    st.markdown("---")
                    st.subheader("전체 타임라인 스크립트")
                    st.code(full_timeline, language="text")
                    st.download_button(
                        "타임라인 스크립트 다운로드",
                        data=full_timeline,
                        file_name="timeline_script.txt",
                        mime="text/plain"
                    )

                # 전체 프롬프트 복사
                all_prompts = "\n\n".join([
                    f"Scene {p['scene_number']} ({p['scene_name']}):\n[이미지]\n{p['prompt']}\n[비디오]\n{p.get('video_prompt', '')}\n[타임라인]\n{p.get('timeline_prompt', '')}"
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
            # 프롬프트 미생성 시 안내
            if 'scene_prompts' not in st.session_state or not st.session_state.scene_prompts:
                st.warning("프롬프트가 아직 생성되지 않았습니다. '스토리보드 미리보기' 탭에서 먼저 프롬프트를 생성해주세요.")
                st.stop()

            st.subheader("다운로드 옵션")
            st.info("📦 포함 내용: 스토리보드 + 나레이션 + 이미지 프롬프트")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Excel 다운로드**")
                st.caption("Scene 데이터를 표 형식으로 다운로드 (편집 가능)")

                # 프롬프트를 딕셔너리로 변환
                prompt_dict = {}
                if 'scene_prompts' in st.session_state and st.session_state.scene_prompts:
                    prompt_dict = {p['scene_number']: p['prompt'] for p in st.session_state.scene_prompts}

                # 비디오 프롬프트 딕셔너리
                video_prompt_dict = {}
                timeline_prompt_dict = {}
                if 'scene_prompts' in st.session_state and st.session_state.scene_prompts:
                    video_prompt_dict = {p['scene_number']: p.get('video_prompt', '') for p in st.session_state.scene_prompts}
                    timeline_prompt_dict = {p['scene_number']: p.get('timeline_prompt', '') for p in st.session_state.scene_prompts}

                # Excel 데이터 생성
                excel_data = []
                cumulative_time = 0
                for i, scene in enumerate(st.session_state.storyboard_scenes):
                    cumulative_time += scene.get('duration', 0)
                    scene_num = i + 1
                    excel_data.append({
                        "번호": scene_num,
                        "Scene 이름": scene.get('name', ''),
                        "설명": scene.get('description', ''),
                        "나레이션": scene.get('narrative', ''),
                        "이미지 프롬프트": prompt_dict.get(scene_num, ''),
                        "비디오 프롬프트": video_prompt_dict.get(scene_num, ''),
                        "타임라인 스크립트": timeline_prompt_dict.get(scene_num, ''),
                        "촬영 각도": scene.get('angle', ''),
                        "카메라 움직임": scene.get('movement', ''),
                        "오디오 분위기": scene.get('audio', '없음'),
                        "시간(초)": scene.get('duration', 0),
                        "누적(초)": cumulative_time
                    })

                import pandas as pd
                from io import BytesIO
                df = pd.DataFrame(excel_data)

                # Excel 파일로 다운로드 시도
                try:
                    # openpyxl을 사용하여 실제 Excel 파일 생성
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='스토리보드')
                    buffer.seek(0)

                    st.download_button(
                        "Excel 다운로드 (.xlsx)",
                        data=buffer,
                        file_name=f"storyboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except ImportError:
                    # openpyxl이 없으면 CSV로 대체
                    st.warning("⚠️ Excel 라이브러리가 없어 CSV로 다운로드됩니다. Excel에서 열 때: 데이터 > 텍스트/CSV 가져오기 > UTF-8 선택")
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        "CSV 다운로드",
                        data=csv_data,
                        file_name=f"storyboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

            with col2:
                st.markdown("**텍스트 다운로드**")
                st.caption("읽기 쉬운 문서 형식 (Scene + 나레이션 + 프롬프트)")

                project_info = st.session_state.get('storyboard_project_info', {})

                # 프롬프트를 딕셔너리로 변환
                prompt_dict = {}
                if 'scene_prompts' in st.session_state and st.session_state.scene_prompts:
                    prompt_dict = {p['scene_number']: p['prompt'] for p in st.session_state.scene_prompts}

                text_content = f"""# 스토리보드
프로젝트: {project_info.get('project_name', 'N/A')}
위치: {project_info.get('location', 'N/A')}
건물 유형: {project_info.get('building_type', 'N/A')}
생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

총 Scene 수: {len(st.session_state.storyboard_scenes)}개
총 예상 시간: {sum(s.get('duration', 0) for s in st.session_state.storyboard_scenes)}초

---

## Scene 목록

"""
                cumulative_time = 0
                for i, scene in enumerate(st.session_state.storyboard_scenes):
                    cumulative_time += scene.get('duration', 0)
                    scene_num = i + 1
                    scene_prompt = prompt_dict.get(scene_num, 'N/A')

                    text_content += f"""### Scene {scene_num}: {scene.get('name', '')}

**장면 설명:**
{scene.get('description', '')}

**나레이션:**
{scene.get('narrative', 'N/A')}

**이미지 프롬프트:**
{scene_prompt}

**촬영 정보:**
- 촬영 각도: {scene.get('angle', '')}
- 카메라 움직임: {scene.get('movement', '')}
- 시간: {scene.get('duration', 0)}초 (누적: {cumulative_time}초)

---

"""

                # 전체 Narrative 섹션 추가
                if st.session_state.narratives:
                    text_content += f"""
## 전체 나레이션 (통합)

{st.session_state.narratives}

---
"""

                # 전체 프롬프트 섹션 추가
                if 'scene_prompts' in st.session_state and st.session_state.scene_prompts:
                    text_content += """
## 이미지 생성 프롬프트 (Scene별)

"""
                    for prompt_data in st.session_state.scene_prompts:
                        text_content += f"""**Scene {prompt_data['scene_number']}: {prompt_data['scene_name']}**
{prompt_data['prompt']}

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

    **1. 프로젝트 정보 입력:**
    - Document Analysis 결과를 활용하면 프로젝트 정보가 자동으로 로드됩니다
    - 직접 입력하여 새로운 프로젝트의 스토리보드를 생성할 수도 있습니다

    **2. Scene 구성:**
    - 마스터플랜 프로젝트에 최적화된 템플릿을 제공합니다
    - 템플릿을 선택하면 기본 Scene이 자동으로 생성됩니다
    - 씬 개수는 3~20개 사이에서 자유롭게 조정 가능합니다
    - 각 Scene의 이름, 설명, 카메라 설정, 시간을 편집할 수 있습니다

    **3. 나레이션 생성:**
    - AI가 각 Scene에 맞는 나레이션을 자동 생성합니다
    - 생성된 나레이션은 각 씬에 자동으로 매칭됩니다
    - 스토리보드 미리보기에서 씬별 나레이션을 확인할 수 있습니다
    - 나레이션은 편집 가능하며, 다운로드 시 포함됩니다

    **4. 이미지 프롬프트:**
    - Scene별 Midjourney 프롬프트가 자동 생성됩니다
    - 카메라 각도와 움직임이 프롬프트에 반영됩니다

    **5. 다운로드:**
    - Excel: 씬 데이터를 표 형식으로 다운로드
    - 텍스트: 씬별 나레이션을 포함한 텍스트 문서로 다운로드
    """)


if __name__ == "__main__":
    main()

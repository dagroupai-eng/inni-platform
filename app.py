import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv

# 페이지 설정 (가장 먼저 호출해야 함)
st.set_page_config(
    page_title="Urban Insight - 교육용",
    page_icon=None,
    layout="wide"
)

# 데이터베이스 및 인증 모듈 초기화
try:
    from database.init_db import init_database
    from database.db_manager import table_exists
    if not table_exists("users"):
        init_database()
except Exception as e:
    print(f"데이터베이스 초기화 경고: {e}")

# 세션 초기화 (로그인 + 작업 데이터 복원)
try:
    from auth.session_init import init_page_session
    init_page_session()
except Exception as e:
    print(f"세션 초기화 오류: {e}")

# 인증 모듈 import
try:
    from auth.authentication import (
        is_authenticated, get_current_user, logout, login
    )
    AUTH_AVAILABLE = True
except ImportError as e:
    AUTH_AVAILABLE = False
    print(f"인증 모듈 로드 실패: {e}")

# 환경변수 로드 (안전하게 처리)
try:
    load_dotenv()
except UnicodeDecodeError:
    pass


def show_login_page():
    """로그인 페이지를 표시합니다."""
    st.title("Urban Insight")
    st.markdown("**학생들을 위한 도시 프로젝트 분석 도구**")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.subheader("로그인")
        st.markdown("개인 번호를 입력하여 로그인하세요.")

        with st.form("login_form"):
            personal_number = st.text_input(
                "개인 번호",
                placeholder="예: ADMIN001",
                help="관리자에게 부여받은 개인 번호를 입력하세요."
            )

            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

        if submitted and personal_number:
            success, message = login(personal_number)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

        st.markdown("---")
        st.caption("개인 번호가 없으신가요? 관리자에게 문의하세요.")
        st.caption("기본 관리자 번호: ADMIN001")


def load_user_api_keys():
    """로그인한 사용자의 API 키를 DB에서 세션 상태로 로드합니다."""
    try:
        from security.api_key_manager import get_user_api_keys, get_user_api_key
        from auth.authentication import get_current_user_id
        from dspy_analyzer import PROVIDER_CONFIG

        user_id = get_current_user_id()
        if not user_id:
            return

        # 모든 제공자의 API 키 확인
        for provider, config in PROVIDER_CONFIG.items():
            api_key_env = config.get('api_key_env')
            if api_key_env:
                # DB에서 키 가져오기
                db_key = get_user_api_key(user_id, api_key_env)
                if db_key:
                    # 세션 상태에 로드
                    session_key = f'user_api_key_{api_key_env}'
                    st.session_state[session_key] = db_key
    except Exception as e:
        print(f"API 키 로드 오류: {e}")


def show_main_app():
    """메인 앱을 표시합니다 (로그인 후)."""
    # dspy_analyzer 안전한 import 처리
    try:
        from dspy_analyzer import PROVIDER_CONFIG, get_api_key
        DSPY_ANALYZER_AVAILABLE = True
    except ImportError as e:
        DSPY_ANALYZER_AVAILABLE = False
        PROVIDER_CONFIG = {}
        get_api_key = None
        st.error("필수 모듈이 설치되지 않았습니다.")
        st.error(f"오류: {str(e)}")
        st.warning("""
        **해결 방법:**

        1. `install.bat`을 실행하여 모든 의존성을 설치하세요.
        2. 또는 다음 명령을 실행하세요:
           ```
           python -m pip install dspy-ai PyMuPDF python-docx geopandas
           ```
        3. 설치 후 앱을 다시 시작하세요.
        """)
        return
    except Exception as e:
        DSPY_ANALYZER_AVAILABLE = False
        PROVIDER_CONFIG = {}
        get_api_key = None
        st.error(f"모듈 로드 중 오류가 발생했습니다: {str(e)}")
        st.warning("앱을 다시 시작하거나 `install.bat`을 실행해보세요.")
        return

    # DB에서 API 키 로드 (로그인 직후 한 번만)
    if 'api_keys_loaded' not in st.session_state:
        load_user_api_keys()
        st.session_state.api_keys_loaded = True

    # 사이드바: 사용자 정보 및 로그아웃
    user = get_current_user()
    with st.sidebar:
        st.success(f"로그인: {user.get('display_name', user.get('personal_number'))}")
        role_display = {"user": "일반", "team_lead": "팀리드", "admin": "관리자"}
        st.caption(f"역할: {role_display.get(user.get('role'), user.get('role'))}")
        if st.button("로그아웃", key="main_logout", use_container_width=True):
            logout()
            st.rerun()

        # 세션 관리 섹션
        st.markdown("---")
        with st.expander("🔄 세션 관리", expanded=False):
            # 분석 진행 상태 복원 확인
            try:
                from auth.session_init import restore_analysis_progress, apply_restored_progress, reset_analysis_state_selective

                # 복원 대기 중인 상태가 있으면 알림 표시
                if 'pending_restore' in st.session_state and st.session_state.pending_restore:
                    restored_progress = st.session_state.pending_restore
                    restored_time = restored_progress.get('_restored_from', '')[:16].replace('T', ' ')
                    results_count = len(restored_progress.get('cot_results', {}))

                    st.warning(f"📂 중단된 세션 발견")
                    st.caption(f"저장: {restored_time}, 완료 블록: {results_count}개")

                    col_r, col_d = st.columns(2)
                    with col_r:
                        if st.button("✅ 복원", key="sidebar_restore", use_container_width=True):
                            if apply_restored_progress(restored_progress):
                                st.session_state.pop('pending_restore', None)
                                st.success("복원됨")
                                st.rerun()
                    with col_d:
                        if st.button("❌ 삭제", key="sidebar_discard", use_container_width=True):
                            st.session_state.pop('pending_restore', None)
                            st.rerun()

                # 초기화 버튼들
                st.caption("초기화 옵션")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 분석 초기화", key="sidebar_reset_analysis", use_container_width=True, help="분석 결과만 초기화"):
                        try:
                            reset_analysis_state_selective(
                                reset_results=True,
                                reset_session=True,
                                preserve_api_keys=True,
                                preserve_blocks=True,
                                preserve_project_info=True
                            )
                            st.success("초기화 완료")
                            st.rerun()
                        except Exception as e:
                            st.error(f"오류: {e}")
                with col2:
                    if st.button("🗑️ 전체 초기화", key="sidebar_reset_all", use_container_width=True, help="모든 데이터 초기화"):
                        # 전체 초기화
                        keys_to_keep = ['authenticated', 'user', 'api_keys_loaded']
                        for key in list(st.session_state.keys()):
                            if key not in keys_to_keep and not key.startswith('user_api_key_'):
                                del st.session_state[key]
                        st.success("전체 초기화 완료")
                        st.rerun()
            except ImportError:
                st.caption("세션 관리 모듈 로드 실패")

        st.markdown("---")

    # 제목
    st.title("Urban Insight")
    st.markdown("**학생들을 위한 도시 프로젝트 분석 도구**")

    # 메인 페이지 내용 - 탭 기반 UI
    st.markdown("""
    Urban Insight는 도시 프로젝트 분석을 위한 종합 AI 플랫폼입니다.
    아래 탭에서 각 기능의 상세 설명과 사용 방법을 확인하세요.
    """)
    
    # 관리자 권한 확인
    user = get_current_user()
    is_admin = user.get('role') == 'admin'
    
    # 탭 구성 (관리자인 경우 관리 탭 추가)
    if is_admin:
        tabs = st.tabs(["개요", "블록 생성기", "지도 분석", "문서 분석", "이미지 프롬프트", "스토리보드", "관리"])
    else:
        tabs = st.tabs(["개요", "블록 생성기", "지도 분석", "문서 분석", "이미지 프롬프트", "스토리보드"])
    
    # 개요 탭
    with tabs[0]:
        st.header("Urban Insight 사용 가이드")
        
        st.markdown("""
        ### 전체 워크플로우
        
        Urban Insight는 도시 프로젝트 분석의 전 과정을 지원합니다:
        """)
        
        # 전체 개요 다이어그램 1
        image_path = Path(__file__).parent / "IMAGES" / "APP_GUIDE_01.png"
        if image_path.exists():
            col_l, col_img, col_r = st.columns([1, 3, 1])
            with col_img:
                st.image(str(image_path), use_container_width=True)
        else:
            st.info("다이어그램 이미지를 찾을 수 없습니다.")
        
        # 전체 개요 다이어그램 2
        image_path = Path(__file__).parent / "IMAGES" / "APP_GUIDE_02.png"
        if image_path.exists():
            col_l, col_img, col_r = st.columns([1, 3, 1])
            with col_img:
                st.image(str(image_path), use_container_width=True)
        else:
            st.info("다이어그램 이미지를 찾을 수 없습니다.")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("주요 기능")
            st.markdown("""
            - **블록 생성기**: 맞춤형 분석 블록 생성
            - **지도 분석**: 도시 데이터 시각화 및 분석
            - **문서 분석**: AI 기반 PDF 분석
            - **이미지 프롬프트**: AI 이미지 생성 도구
            - **스토리보드**: 비디오 스토리보드 생성
            """)
        
        with col2:
            st.subheader("빠른 시작")
            st.markdown("""
            1. 왼쪽 사이드바에서 페이지 선택
            2. 각 페이지의 안내에 따라 진행
            3. 순차적으로 진행하면 최상의 결과
            4. 데이터는 자동으로 페이지 간 공유
            """)
        
        st.markdown("---")
        
        st.info("**팁**: 각 탭을 클릭하여 상세한 기능 설명과 사용 방법을 확인하세요!")
    
    # 블록 생성기 탭
    with tabs[1]:
        st.header("블록 생성기")
        
        st.markdown("""
        ### 개요
        
        블록 생성기는 프로젝트 분석을 위한 맞춤형 분석 블록을 생성하는 도구입니다.
        사용자가 원하는 분석 관점을 정의하고, AI가 해당 관점에 따라 문서를 분석하도록 설정할 수 있습니다.
        """)
        
        # 블록 생성기 다이어그램
        image_path = Path(__file__).parent / "IMAGES" / "APP_GUIDE_03.png"
        if image_path.exists():
            col_l, col_img, col_r = st.columns([1, 3, 1])
            with col_img:
                st.image(str(image_path), use_container_width=True)
        else:
            st.info("다이어그램 이미지를 찾을 수 없습니다.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("주요 기능")
            st.markdown("""
            - **커스텀 블록 생성**: 원하는 분석 관점 정의
            - **DSPy Signature 자동 생성**: AI 분석 구조 자동 구축
            - **블록 관리**: 생성된 블록 조회, 수정, 삭제
            - **공유 기능**: 팀원과 블록 공유
            """)
        
        with col2:
            st.subheader("사용 대상")
            st.markdown("""
            - 팀 리더
            - 연구자
            - 고급 사용자
            """)
        
        st.markdown("---")
        
        with st.expander("사용 방법"):
            st.markdown("""
            #### 단계별 가이드
            
            1. **블록 ID 입력**
               - 영문, 숫자, 언더스코어만 사용
               - 예: `site_analysis`, `program_review`
            
            2. **블록 이름 작성**
               - 한글로 명확하게 작성
               - 예: "대지 분석", "프로그램 검토"
            
            3. **블록 설명 작성**
               - 분석 목적과 방법을 상세히 기술
               - AI가 이 설명을 기반으로 분석 수행
            
            4. **공개 범위 설정**
               - 나만 보기 / 팀 공유 / 전체 공개 선택
            
            5. **블록 생성**
               - 생성 버튼 클릭
               - DSPy Signature 자동 생성 및 저장
            """)
        
        with st.expander("주의사항"):
            st.markdown("""
            - 블록 ID는 생성 후 변경 불가
            - 설명은 가능한 구체적으로 작성
            - 시스템 블록(기본 제공)은 수정 불가
            """)
    
    # 지도 분석 탭
    with tabs[2]:
        st.header("지도 분석")
        
        st.markdown("""
        ### 개요
        
        지도 분석 페이지는 프로젝트 대상지의 지리적 정보와 도시 데이터를 시각화하고 분석하는 도구입니다.
        VWorld API를 활용하여 실시간 도시 데이터를 수집하고, 다양한 레이어를 통해 대상지를 분석할 수 있습니다.
        """)
        
        # 지도 분석 다이어그램
        image_path = Path(__file__).parent / "IMAGES" / "APP_GUIDE_04.png"
        if image_path.exists():
            col_l, col_img, col_r = st.columns([1, 3, 1])
            with col_img:
                st.image(str(image_path), use_container_width=True)
        else:
            st.info("다이어그램 이미지를 찾을 수 없습니다.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("주요 기능")
            st.markdown("""
            - **인터랙티브 지도**: 실시간 지도 조작 및 탐색
            - **다중 레이어**: 지적도, 용도지역, 건물, 도로 등
            - **도시 데이터 수집**: 주변 시설, 교통, 인구 등
            - **시각화**: 수집된 데이터의 차트 및 그래프
            - **내보내기**: 분석 결과 다운로드
            """)
        
        with col2:
            st.subheader("데이터 소스")
            st.markdown("""
            - VWorld API
            - 국토정보플랫폼
            - OpenStreetMap
            - 공공데이터포털
            """)
        
        st.markdown("---")
        
        with st.expander("사용 방법"):
            st.markdown("""
            #### 단계별 가이드
            
            1. **좌표 입력**
               - 위도/경도 직접 입력
               - 또는 주소 검색
            
            2. **지도 탐색**
               - 확대/축소, 이동
               - 원하는 위치 확인
            
            3. **레이어 선택**
               - 지적도: 필지 경계
               - 용도지역: 도시계획 용도
               - 건물: 건물 정보
               - 도로: 도로망
            
            4. **데이터 수집**
               - 반경 설정 (기본 500m)
               - 수집 항목 선택
               - 수집 시작
            
            5. **결과 확인**
               - 차트로 시각화
               - 상세 데이터 테이블
               - 필요시 다운로드
            """)
        
        with st.expander("활용 팁"):
            st.markdown("""
            - **대상지 분석**: 주변 시설, 접근성 평가
            - **입지 분석**: 상권, 인구, 교통 분석
            - **법규 검토**: 용도지역, 지구단위계획 확인
            - **문서 분석 연계**: 수집된 데이터를 문서 분석에 활용
            """)
    
    # 문서 분석 탭
    with tabs[3]:
        st.header("문서 분석")
        
        st.markdown("""
        ### 개요
        
        문서 분석은 Urban Insight의 핵심 기능입니다.
        PDF, Excel, CSV, 텍스트 파일을 업로드하면, AI가 선택한 분석 블록에 따라
        Chain of Thought 방식으로 심층 분석을 수행합니다.
        """)
        
        # 문서 분석 다이어그램
        image_path = Path(__file__).parent / "IMAGES" / "APP_GUIDE_05.png"
        if image_path.exists():
            col_l, col_img, col_r = st.columns([1, 3, 1])
            with col_img:
                st.image(str(image_path), use_container_width=True)
        else:
            st.info("다이어그램 이미지를 찾을 수 없습니다.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("주요 기능")
            st.markdown("""
            - **다양한 파일 형식**: PDF, Excel, CSV, TXT, JSON
            - **AI 분석**: DSPy 기반 체인 오브 생각(CoT)
            - **커스텀 블록**: 사용자 정의 분석 관점
            - **시스템 블록**: 기본 제공 분석 템플릿
            - **Word 내보내기**: 분석 결과 문서화
            - **세션 저장**: 분석 결과 자동 저장
            """)
        
        with col2:
            st.subheader("지원 형식")
            st.markdown("""
            - PDF
            - Excel (.xlsx, .xls)
            - CSV
            - TXT
            - JSON
            - DOCX
            """)
        
        st.markdown("---")
        
        with st.expander("사용 방법"):
            st.markdown("""
            #### 단계별 가이드
            
            1. **프로젝트 정보 입력**
               - 프로젝트명
               - 위치 (지도 분석과 연동)
               - 좌표 (선택사항)
               - 프로젝트 목표
            
            2. **파일 업로드**
               - 드래그 앤 드롭
               - 또는 파일 선택
               - 여러 형식 지원
            
            3. **AI 모델 선택**
               - Gemini 2.5 Flash (권장)
               - Claude, GPT 등
               - API 키 필요
            
            4. **분석 블록 선택**
               - 시스템 블록: 기본 제공
               - 사용자 블록: 직접 생성한 블록
               - 여러 블록 동시 선택 가능
            
            5. **분석 실행**
               - 분석 시작 버튼
               - 진행 상황 실시간 표시
               - 블록별 결과 확인
            
            6. **결과 활용**
               - 화면에서 바로 확인
               - Word 문서로 다운로드
               - 다음 단계(이미지, 스토리보드)로 자동 전달
            """)
        
        with st.expander("고급 설정"):
            st.markdown("""
            - **Shapefile 연동**: 지도 데이터와 통합 분석
            - **RAG 검색**: 문서 내 키워드 검색
            - **비교 분석**: 여러 문서 비교
            - **통계 분석**: 정량적 데이터 차트화
            """)
    
    # 이미지 프롬프트 탭
    with tabs[4]:
        st.header("이미지 프롬프트 생성기")
        
        st.markdown("""
        ### 개요
        
        문서 분석 결과를 바탕으로 AI 이미지 생성 도구(Midjourney, DALL-E, Stable Diffusion 등)에서
        사용할 수 있는 고품질 프롬프트를 자동 생성합니다.
        """)
        
        # 이미지 프롬프트 다이어그램
        image_path = Path(__file__).parent / "IMAGES" / "APP_GUIDE_06.png"
        if image_path.exists():
            col_l, col_img, col_r = st.columns([1, 3, 1])
            with col_img:
                st.image(str(image_path), use_container_width=True)
        else:
            st.info("다이어그램 이미지를 찾을 수 없습니다.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("주요 기능")
            st.markdown("""
            - **자동 프롬프트 생성**: 분석 결과 기반
            - **다양한 이미지 유형**: 조감도, 투시도, 단면도 등
            - **스타일 커스터마이징**: 사실적, 개념적, 추상적
            - **건축가 레퍼런스**: 유명 건축가 스타일 적용
            - **한영 병기**: 한글 설명 + 영문 프롬프트
            - **즉시 복사**: 원클릭 복사 기능
            """)
        
        with col2:
            st.subheader("지원 도구")
            st.markdown("""
            - Midjourney
            - DALL-E
            - Stable Diffusion
            - Leonardo AI
            - 기타 AI 이미지 도구
            """)
        
        st.markdown("---")
        
        with st.expander("사용 방법"):
            st.markdown("""
            #### 단계별 가이드
            
            1. **문서 분석 완료**
               - 먼저 문서 분석 페이지에서 분석 완료
               - 결과가 자동으로 로드됨
            
            2. **이미지 유형 선택**
               - 마스터플랜 조감도
               - 건물 외관 투시도
               - 내부 공간 투시도
               - 단면도
               - 다이어그램
            
            3. **스타일 설정**
               - 사실적 렌더링
               - 개념적 스케치
               - 추상적 다이어그램
               - 손그림 스타일
            
            4. **추가 옵션**
               - 참고 건축가/스튜디오
               - 시간대, 날씨
               - 카메라 앵글
               - 분위기 키워드
            
            5. **프롬프트 생성**
               - 생성 버튼 클릭
               - 한글 설명 먼저 확인
               - 영문 프롬프트 복사
            
            6. **AI 도구에서 사용**
               - Midjourney 등에 붙여넣기
               - 이미지 생성
               - 필요시 프롬프트 수정하여 재생성
            """)
        
        with st.expander("프롬프트 작성 팁"):
            st.markdown("""
            - **구체적일수록 좋음**: 상세한 설명이 더 나은 결과
            - **키워드 조합**: 건축 용어 + 분위기 + 스타일
            - **네거티브 프롬프트**: 원하지 않는 요소 명시
            - **반복 테스트**: 여러 번 생성하여 최적화
            """)
    
    # 스토리보드 탭
    with tabs[5]:
        st.header("비디오 스토리보드 생성기")
        
        st.markdown("""
        ### 개요
        
        프로젝트 발표나 홍보를 위한 비디오 스토리보드를 자동으로 생성합니다.
        문서 분석 결과를 바탕으로 씬 구성, 카메라 앵글, 나레이션까지 포함한
        완성도 높은 스토리보드를 제공합니다.
        """)
        
        # 스토리보드 생성 다이어그램
        image_path = Path(__file__).parent / "IMAGES" / "APP_GUIDE_07.png"
        if image_path.exists():
            col_l, col_img, col_r = st.columns([1, 3, 1])
            with col_img:
                st.image(str(image_path), use_container_width=True)
        else:
            st.info("다이어그램 이미지를 찾을 수 없습니다.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("주요 기능")
            st.markdown("""
            - **자동 씬 구성**: 프로젝트 특성에 맞는 씬 생성
            - **템플릿 제공**: 마스터플랜, 건축물, 사업계획 등
            - **카메라 설정**: 앵글, 무브먼트, 지속시간
            - **나레이션 생성**: AI 기반 자동 스크립트
            - **이미지 프롬프트**: 각 씬별 이미지 프롬프트
            - **타임라인**: 전체 영상 타임라인 시각화
            - **다운로드**: Excel, PDF 형식 지원
            """)
        
        with col2:
            st.subheader("출력 형식")
            st.markdown("""
            - Excel (.xlsx)
            - PDF 문서
            - JSON 데이터
            - 타임라인 차트
            """)
        
        st.markdown("---")
        
        with st.expander("사용 방법"):
            st.markdown("""
            #### 단계별 가이드
            
            1. **문서 분석 완료**
               - 문서 분석 페이지에서 분석 완료
               - 프로젝트 정보 자동 로드
            
            2. **템플릿 선택**
               - 마스터플랜 기본
               - 건축물 소개
               - 사업계획 발표
               - 또는 빈 템플릿
            
            3. **영상 설정**
               - 총 영상 길이 (초)
               - 나레이션 톤앤매너
               - 영상 스타일
            
            4. **씬 편집**
               - 씬 추가/삭제/순서 변경
               - 각 씬의 지속시간 조정
               - 카메라 앵글/무브먼트 설정
            
            5. **나레이션 생성**
               - AI가 각 씬별 나레이션 자동 생성
               - 수동 편집 가능
               - 톤 조정 (공식적/친근한)
            
            6. **이미지 프롬프트 생성**
               - 각 씬의 시각적 요소를 위한 프롬프트
               - Midjourney 등에서 활용
            
            7. **다운로드**
               - Excel: 편집 가능한 스토리보드
               - PDF: 발표/공유용 문서
            """)
        
        with st.expander("영상 제작 팁"):
            st.markdown("""
            - **스토리 구조**: 도입-전개-결말 구조 유지
            - **씬 지속시간**: 4-6초가 적당
            - **전환**: 씬 간 자연스러운 연결
            - **나레이션**: 명확하고 간결하게
            - **타이밍**: 나레이션과 비주얼 싱크
            """)
    
    # 관리 탭 (관리자만)
    if is_admin:
        with tabs[6]:
            st.header("관리자 기능")
            
            st.markdown("""
            ### 개요
            
            시스템 관리자를 위한 사용자 관리, 팀 관리, 시스템 모니터링 기능을 제공합니다.
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("주요 기능")
                st.markdown("""
                - **사용자 관리**: 계정 생성, 수정, 삭제
                - **팀 관리**: 팀 생성 및 멤버 할당
                - **권한 관리**: 역할 기반 접근 제어
                - **시스템 모니터링**: 사용 통계 및 로그
                - **데이터베이스**: 백업 및 정리
                """)
            
            with col2:
                st.subheader("접근 권한")
                st.markdown("""
                - 관리자(Admin)만 접근 가능
                - 일반 사용자 접근 불가
                - 팀 리더 접근 불가
                """)
            
            st.markdown("---")
            
            with st.expander("사용 방법"):
                st.markdown("""
                #### 사용자 관리
                
                1. **사용자 생성**
                   - 개인 번호 생성
                   - 이름 및 역할 설정
                   - 팀 할당 (선택사항)
                
                2. **사용자 수정**
                   - 정보 변경
                   - 역할 변경
                   - 팀 재할당
                
                3. **사용자 삭제**
                   - 계정 비활성화
                   - 데이터 보존 여부 선택
                
                #### 팀 관리
                
                1. **팀 생성**
                   - 팀 이름 설정
                   - 팀 리더 지정
                
                2. **멤버 관리**
                   - 멤버 추가/제거
                   - 권한 설정
                """)
            
            st.info("관리자 기능은 신중하게 사용하세요. 모든 작업은 로그에 기록됩니다.")

    # API 키 상태 표시
    st.sidebar.header("시스템 상태")

    # API 제공자 선택 (세션 상태 초기화)
    if 'llm_provider' not in st.session_state:
        st.session_state.llm_provider = 'gemini_25flash'

    # API 제공자 선택 (dspy_analyzer가 사용 가능한 경우에만)
    if DSPY_ANALYZER_AVAILABLE and PROVIDER_CONFIG:
        # AI 모델 선택
        st.sidebar.subheader("AI 모델 선택")
        provider_options = {
            provider: config.get('display_name', provider.title())
            for provider, config in PROVIDER_CONFIG.items()
        }
        selected_provider = st.sidebar.selectbox(
            "사용할 AI 모델:",
            options=list(provider_options.keys()),
            format_func=lambda x: provider_options[x],
            key='llm_provider',
            help="분석에 사용할 AI 모델을 선택합니다."
        )

        # 선택된 제공자 정보 표시
        provider_config = PROVIDER_CONFIG.get(selected_provider, {})
        provider_name = provider_config.get('display_name', selected_provider)
        model_name = provider_config.get('model', 'unknown')
        api_key_env = provider_config.get('api_key_env', '')

        st.sidebar.caption(f"모델: {model_name}")

        st.sidebar.markdown("---")

        # API 키 입력 섹션 (선택된 모델에 따라 동적으로 표시)
        if api_key_env:
            st.sidebar.subheader("API 키 설정")

            # 세션 상태 초기화
            session_key = f'user_api_key_{api_key_env}'
            if session_key not in st.session_state:
                st.session_state[session_key] = ''

            # API 키 입력 필드
            user_input_key = st.sidebar.text_input(
                f"{api_key_env} 입력:",
                value=st.session_state[session_key],
                type="password",
                help=f"여기에 {provider_name} API 키를 입력하세요.",
                key=f"api_key_input_{api_key_env}"
            )

            # 버튼 컬럼 (확인, 삭제)
            col1, col2 = st.sidebar.columns(2)

            with col1:
                if st.button("확인", key=f"confirm_key_{api_key_env}", use_container_width=True):
                    if user_input_key.strip():
                        # 세션 상태에 저장
                        st.session_state[session_key] = user_input_key.strip()

                        # DB에도 암호화하여 저장
                        try:
                            from security.api_key_manager import save_user_api_key
                            user_id = user.get('id')
                            if user_id:
                                if save_user_api_key(user_id, api_key_env, user_input_key.strip()):
                                    st.sidebar.success("API 키가 안전하게 저장되었습니다!")
                                else:
                                    st.sidebar.warning("API 키 저장에 실패했습니다.")
                        except Exception as e:
                            st.sidebar.warning(f"DB 저장 오류: {e}")

                        st.rerun()
                    else:
                        st.sidebar.error("API 키를 입력해주세요.")

            with col2:
                if st.session_state[session_key]:
                    if st.button("삭제", key=f"delete_key_{api_key_env}", use_container_width=True):
                        # 세션 상태에서 삭제
                        st.session_state[session_key] = ''

                        # DB에서도 삭제
                        try:
                            from security.api_key_manager import delete_user_api_key
                            user_id = user.get('id')
                            if user_id:
                                delete_user_api_key(user_id, api_key_env)
                        except Exception:
                            pass

                        st.sidebar.info("API 키 삭제됨")
                        st.rerun()

            st.sidebar.markdown("---")

        # 선택된 제공자의 API 키 확인
        if get_api_key:
            api_key = get_api_key(selected_provider)
        else:
            api_key = None

        # API 키 상태 표시
        if api_key_env and not api_key:
            st.sidebar.warning(f"{provider_name} API 키 필요")
        elif api_key:
            st.sidebar.success(f"{provider_name} API 키 [확인됨]")
        elif not api_key_env:
            st.sidebar.info(f"{provider_name}는 API 키 불필요")
    else:
        st.sidebar.warning("AI 모델 기능 사용 불가")

    # 사용법 안내
    st.sidebar.header("사용법")
    st.sidebar.markdown("""
    1. **PDF 분석**: PDF 문서를 업로드하고 분석 블록을 선택하세요
    2. **통계**: 분석 결과를 시각적으로 확인하세요
    3. **지도**: 프로젝트 위치와 관련 데이터를 지도에서 확인하세요
    4. **사이트 데이터 수집**: 좌표를 입력하여 주변 도시 데이터를 자동 수집하세요
    """)

    # 푸터
    st.markdown("---")
    st.markdown("**Urban Insight** - 도시 교육을 위한 AI 분석 도구")


# 메인 로직
if AUTH_AVAILABLE:
    if is_authenticated():
        show_main_app()
    else:
        show_login_page()
else:
    st.error("인증 시스템을 사용할 수 없습니다.")
    st.info("database, auth 모듈이 올바르게 설치되어 있는지 확인하세요.")

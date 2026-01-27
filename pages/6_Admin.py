"""
관리자 페이지
사용자 관리, 팀 관리, 시스템 모니터링
"""

import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="관리자 - Urban ArchInsight",
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

# 세션 관리 사이드바 렌더링
if render_session_manager_sidebar:
    render_session_manager_sidebar()

# 데이터베이스 초기화 (필요시)
try:
    from database.init_db import init_database
    from database.db_manager import table_exists
    if not table_exists("users"):
        init_database()
except Exception as e:
    st.error(f"데이터베이스 초기화 오류: {e}")

# 인증 모듈 import
try:
    from auth.authentication import (
        is_authenticated, get_current_user, is_current_user_admin
    )
    AUTH_AVAILABLE = True
except ImportError as e:
    AUTH_AVAILABLE = False
    st.error(f"인증 모듈 로드 실패: {e}")

# 관리자 모듈 import
try:
    from admin.admin_manager import (
        get_system_stats,
        get_all_users_admin,
        create_user_admin,
        update_user_admin,
        delete_user_admin,
        get_all_teams_admin,
        create_team_admin,
        delete_team_admin,
        cleanup_system,
        get_recent_logins
    )
    from auth.user_manager import get_team_members
    ADMIN_AVAILABLE = True
except ImportError as e:
    ADMIN_AVAILABLE = False
    st.error(f"관리자 모듈 로드 실패: {e}")


def show_access_denied():
    """접근 권한 없음 페이지"""
    st.title("관리자 페이지")
    st.error("관리자 권한이 필요합니다.")
    st.info("관리자 권한이 있는 계정으로 로그인해주세요.")

    if not is_authenticated():
        st.warning("메인 페이지에서 로그인해주세요.")


def show_dashboard():
    """대시보드 탭"""
    st.header("시스템 대시보드")

    stats = get_system_stats()

    # 통계 카드
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "전체 사용자",
            stats["users"]["total"],
            delta=f"활성: {stats['users']['active']}"
        )

    with col2:
        st.metric(
            "전체 팀",
            stats["teams"]["total"]
        )

    with col3:
        st.metric(
            "사용자 블록",
            stats["blocks"]["total"],
            delta=f"공개: {stats['blocks']['public']}"
        )

    with col4:
        st.metric(
            "활성 세션",
            stats["sessions"]["active"]
        )

    st.markdown("---")

    # 최근 로그인
    st.subheader("최근 로그인")
    recent_logins = get_recent_logins(10)

    if recent_logins:
        for login in recent_logins:
            col1, col2, col3 = st.columns([2, 3, 3])
            with col1:
                st.text(login.get("personal_number", ""))
            with col2:
                st.text(login.get("display_name", ""))
            with col3:
                last_login = login.get("last_login", "")
                if last_login:
                    st.text(last_login[:19])
    else:
        st.info("최근 로그인 기록이 없습니다.")

    st.markdown("---")

    # 시스템 관리
    st.subheader("시스템 관리")
    if st.button("만료된 세션 정리"):
        success, message = cleanup_system()
        if success:
            st.success(message)
        else:
            st.error(message)


def show_user_management():
    """사용자 관리 탭"""
    st.header("사용자 관리")

    # 새 사용자 생성
    with st.expander("새 사용자 생성", expanded=False):
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_personal_number = st.text_input(
                    "개인 번호",
                    placeholder="예: USER001",
                    help="고유한 개인 번호를 입력하세요."
                )
                new_display_name = st.text_input(
                    "표시 이름",
                    placeholder="예: 홍길동"
                )

            with col2:
                new_role = st.selectbox(
                    "역할",
                    options=["user", "team_lead", "admin"],
                    format_func=lambda x: {"user": "일반 사용자", "team_lead": "팀 리드", "admin": "관리자"}[x]
                )

                teams = get_all_teams_admin()
                team_options = {0: "팀 없음"}
                team_options.update({t["id"]: t["name"] for t in teams})
                new_team_id = st.selectbox(
                    "소속 팀",
                    options=list(team_options.keys()),
                    format_func=lambda x: team_options[x]
                )

            if st.form_submit_button("사용자 생성", type="primary"):
                success, message = create_user_admin(
                    new_personal_number,
                    new_display_name,
                    new_role,
                    new_team_id if new_team_id != 0 else None
                )
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    st.markdown("---")

    # 사용자 목록
    st.subheader("사용자 목록")

    # 검색
    search = st.text_input("검색 (개인번호 또는 이름)", placeholder="검색어 입력...")

    # 사용자 목록 조회
    users = get_all_users_admin(search_query=search if search else None)

    if users:
        for user in users:
            with st.expander(f"{user['personal_number']} - {user.get('display_name', '이름 없음')}"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown(f"**개인 번호:** {user['personal_number']}")
                    st.markdown(f"**표시 이름:** {user.get('display_name', '-')}")

                with col2:
                    role_display = {"user": "일반", "team_lead": "팀리드", "admin": "관리자"}
                    st.markdown(f"**역할:** {role_display.get(user.get('role'), user.get('role'))}")
                    st.markdown(f"**소속 팀:** {user.get('team_name', '없음')}")

                with col3:
                    status_display = {"active": "활성", "inactive": "비활성", "suspended": "정지"}
                    st.markdown(f"**상태:** {status_display.get(user.get('status'), user.get('status'))}")
                    last_login = user.get('last_login', '')
                    st.markdown(f"**마지막 로그인:** {last_login[:19] if last_login else '-'}")

                # 사용자 정보 수정
                st.markdown("**사용자 정보 수정**")
                col1, col2, col3 = st.columns(3)

                with col1:
                    status_options = ["active", "inactive", "suspended"]
                    current_status = user.get("status", "active")
                    try:
                        status_index = status_options.index(current_status)
                    except ValueError:
                        status_index = 0
                    
                    new_status = st.selectbox(
                        "상태",
                        options=status_options,
                        format_func=lambda x: {"active": "활성", "inactive": "비활성", "suspended": "정지"}[x],
                        index=status_index,
                        key=f"status_{user['id']}"
                    )

                with col2:
                    role_options = ["user", "team_lead", "admin"]
                    current_role = user.get("role", "user")
                    try:
                        role_index = role_options.index(current_role)
                    except ValueError:
                        role_index = 0
                    
                    new_role = st.selectbox(
                        "역할",
                        options=role_options,
                        format_func=lambda x: {"user": "일반 사용자", "team_lead": "팀 리드", "admin": "관리자"}[x],
                        index=role_index,
                        key=f"role_{user['id']}"
                    )

                with col3:
                    teams = get_all_teams_admin()
                    team_options = {0: "팀 없음"}
                    team_options.update({t["id"]: t["name"] for t in teams})
                    
                    current_team_id = user.get("team_id") or 0
                    team_keys = list(team_options.keys())
                    try:
                        team_index = team_keys.index(current_team_id)
                    except ValueError:
                        team_index = 0
                    
                    new_team_id = st.selectbox(
                        "소속 팀",
                        options=team_keys,
                        format_func=lambda x: team_options[x],
                        index=team_index,
                        key=f"team_{user['id']}"
                    )

                # 버튼
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button("정보 업데이트", key=f"update_{user['id']}", type="primary"):
                        print(f"[DEBUG 업데이트] user_id: {user['id']}")
                        print(f"[DEBUG 업데이트] 이전 status: {user.get('status')} -> 새 status: {new_status}")
                        print(f"[DEBUG 업데이트] 이전 role: {user.get('role')} -> 새 role: {new_role}")
                        print(f"[DEBUG 업데이트] 이전 team_id: {user.get('team_id')} -> 새 team_id: {new_team_id}")
                        
                        # team_id 처리: 0이면 None으로, 그 외에는 그대로
                        final_team_id = None if new_team_id == 0 else new_team_id
                        print(f"[DEBUG 업데이트] 최종 team_id: {final_team_id}")
                        
                        success, message = update_user_admin(
                            user["id"],
                            status=new_status,
                            role=new_role,
                            team_id=final_team_id
                        )
                        print(f"[DEBUG 업데이트] 결과: success={success}, message={message}")
                        
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

                with col2:
                    if user.get("role") != "admin":
                        if st.button("삭제", key=f"delete_{user['id']}", type="secondary"):
                            success, message = delete_user_admin(user["id"])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
    else:
        st.info("등록된 사용자가 없습니다.")


def show_team_management():
    """팀 관리 탭"""
    st.header("팀 관리")

    # 새 팀 생성
    with st.expander("새 팀 생성", expanded=False):
        with st.form("create_team_form"):
            new_team_name = st.text_input(
                "팀 이름",
                placeholder="예: 도시계획팀"
            )
            new_team_desc = st.text_area(
                "팀 설명",
                placeholder="팀에 대한 설명을 입력하세요."
            )

            if st.form_submit_button("팀 생성", type="primary"):
                success, message = create_team_admin(new_team_name, new_team_desc)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    st.markdown("---")

    # 팀 목록
    st.subheader("팀 목록")

    teams = get_all_teams_admin()

    if teams:
        for team in teams:
            with st.expander(f"{team['name']} ({team.get('member_count', 0)}명)"):
                st.markdown(f"**설명:** {team.get('description', '-')}")
                st.markdown(f"**생성일:** {team.get('created_at', '')[:10]}")

                # 팀 멤버 목록
                members = get_team_members(team["id"])
                if members:
                    st.markdown("**멤버:**")
                    for member in members:
                        st.text(f"  - {member.get('display_name', member.get('personal_number'))}")

                # 팀 삭제 버튼
                if st.button("팀 삭제", key=f"del_team_{team['id']}", type="secondary"):
                    success, message = delete_team_admin(team["id"])
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        st.info("등록된 팀이 없습니다.")


def main():
    """메인 함수"""
    st.title("관리자 페이지")

    if not AUTH_AVAILABLE or not ADMIN_AVAILABLE:
        st.error("필요한 모듈을 로드할 수 없습니다.")
        return

    # 인증 및 권한 확인
    if not is_authenticated():
        show_access_denied()
        return

    if not is_current_user_admin():
        show_access_denied()
        return

    # 사이드바에 현재 관리자 정보 표시
    with st.sidebar:
        user = get_current_user()
        st.success(f"관리자: {user.get('display_name', user.get('personal_number'))}")
        st.markdown("---")

    # 탭 메뉴
    tab1, tab2, tab3 = st.tabs(["대시보드", "사용자 관리", "팀 관리"])

    with tab1:
        show_dashboard()

    with tab2:
        show_user_management()

    with tab3:
        show_team_management()


if __name__ == "__main__":
    main()

"""
GitHub 기반 영구 스토리지
Streamlit Cloud 재시작 시에도 데이터 유지
"""

import os
import json
import base64
import gzip
from datetime import datetime
from typing import Optional, Dict, Any, List
import streamlit as st

# GitHub API 라이브러리
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def get_github_token() -> Optional[str]:
    """GitHub Personal Access Token 가져오기"""
    # 1. Streamlit secrets에서 먼저 확인
    try:
        if hasattr(st, 'secrets') and 'GITHUB_TOKEN' in st.secrets:
            return st.secrets['GITHUB_TOKEN']
    except Exception:
        pass

    # 2. 환경변수에서 확인
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        return token

    return None


def get_github_config() -> Dict[str, str]:
    """GitHub 저장소 설정"""
    # Streamlit secrets 또는 환경변수에서 설정 읽기
    try:
        if hasattr(st, 'secrets'):
            return {
                'owner': st.secrets.get('GITHUB_OWNER', 'dagroupai-eng'),
                'repo': st.secrets.get('GITHUB_REPO', 'inni-platform'),
                'branch': st.secrets.get('GITHUB_DATA_BRANCH', 'user-data'),
            }
    except Exception:
        pass

    return {
        'owner': os.environ.get('GITHUB_OWNER', 'dagroupai-eng'),
        'repo': os.environ.get('GITHUB_REPO', 'inni-platform'),
        'branch': os.environ.get('GITHUB_DATA_BRANCH', 'user-data'),
    }


def _compress_data(data: Dict) -> str:
    """데이터를 압축하여 base64로 인코딩"""
    json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    compressed = gzip.compress(json_str.encode('utf-8'))
    return base64.b64encode(compressed).decode('ascii')


def _decompress_data(encoded: str) -> Dict:
    """base64 디코딩 후 압축 해제"""
    compressed = base64.b64decode(encoded.encode('ascii'))
    json_str = gzip.decompress(compressed).decode('utf-8')
    return json.loads(json_str)


def _get_file_sha(path: str) -> Optional[str]:
    """파일의 현재 SHA 가져오기 (업데이트 시 필요)"""
    token = get_github_token()
    config = get_github_config()

    if not token:
        return None

    url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/contents/{path}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    params = {'ref': config['branch']}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get('sha')
    except Exception:
        pass

    return None


def _ensure_branch_exists():
    """데이터 브랜치가 없으면 생성"""
    token = get_github_token()
    config = get_github_config()

    if not token:
        return False

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # 브랜치 존재 확인
    url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/branches/{config['branch']}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True

        # 브랜치가 없으면 master/main에서 생성
        # 먼저 기본 브랜치의 SHA 가져오기
        for base_branch in ['master', 'main']:
            ref_url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/git/refs/heads/{base_branch}"
            ref_response = requests.get(ref_url, headers=headers, timeout=10)
            if ref_response.status_code == 200:
                sha = ref_response.json()['object']['sha']

                # 새 브랜치 생성
                create_url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/git/refs"
                create_data = {
                    'ref': f"refs/heads/{config['branch']}",
                    'sha': sha
                }
                create_response = requests.post(create_url, headers=headers, json=create_data, timeout=10)
                if create_response.status_code == 201:
                    print(f"[GitHub] '{config['branch']}' 브랜치 생성 완료")
                    return True
                break
    except Exception as e:
        print(f"[GitHub] 브랜치 확인/생성 오류: {e}")

    return False


def save_to_github(user_id: str, data_type: str, data: Dict) -> bool:
    """
    데이터를 GitHub에 저장

    Args:
        user_id: 사용자 식별자 (personal_number 권장, 예: 'ADMIN001', 'JUEUN')
        data_type: 데이터 타입 (예: 'session', 'analysis', 'project')
        data: 저장할 데이터

    Returns:
        성공 여부

    Note:
        폴더 구조: user_data/{user_id}/{data_type}.json.gz
        예: user_data/ADMIN001/session.json.gz
    """
    if not REQUESTS_AVAILABLE:
        print("[GitHub] requests 라이브러리가 필요합니다")
        return False

    token = get_github_token()
    if not token:
        print("[GitHub] GITHUB_TOKEN이 설정되지 않았습니다")
        return False

    config = get_github_config()

    # 브랜치 확인/생성
    if not _ensure_branch_exists():
        print("[GitHub] 데이터 브랜치 생성 실패")
        return False

    # 파일 경로: user_data/{user_id}/{data_type}.json.gz
    file_path = f"user_data/{user_id}/{data_type}.json.gz"

    # 데이터 압축 (용량 절감)
    try:
        compressed_content = _compress_data(data)
    except Exception as e:
        print(f"[GitHub] 데이터 압축 실패: {e}")
        return False

    # 기존 파일 SHA 확인 (업데이트인 경우)
    sha = _get_file_sha(file_path)

    # GitHub API로 파일 생성/업데이트
    url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/contents/{file_path}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    payload = {
        'message': f"[Auto] Update {data_type} for user {user_id[:8]}...",
        'content': base64.b64encode(compressed_content.encode('utf-8')).decode('ascii'),
        'branch': config['branch']
    }

    if sha:
        payload['sha'] = sha

    try:
        response = requests.put(url, headers=headers, json=payload, timeout=30)

        if response.status_code in [200, 201]:
            print(f"[GitHub] 저장 성공: {file_path}")
            return True
        else:
            print(f"[GitHub] 저장 실패: {response.status_code} - {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[GitHub] API 오류: {e}")
        return False


def load_from_github(user_id: str, data_type: str) -> Optional[Dict]:
    """
    GitHub에서 데이터 불러오기

    Args:
        user_id: 사용자 식별자 (personal_number 권장, 예: 'ADMIN001', 'JUEUN')
        data_type: 데이터 타입

    Returns:
        저장된 데이터 또는 None

    Note:
        폴더 구조: user_data/{user_id}/{data_type}.json.gz
    """
    if not REQUESTS_AVAILABLE:
        return None

    token = get_github_token()
    if not token:
        return None

    config = get_github_config()
    file_path = f"user_data/{user_id}/{data_type}.json.gz"

    url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/contents/{file_path}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    params = {'ref': config['branch']}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)

        if response.status_code == 200:
            content = response.json().get('content', '')
            # base64 디코딩 후 압축 해제
            decoded = base64.b64decode(content).decode('utf-8')
            data = _decompress_data(decoded)
            print(f"[GitHub] 불러오기 성공: {file_path}")
            return data
        elif response.status_code == 404:
            print(f"[GitHub] 파일 없음: {file_path}")
            return None
        else:
            print(f"[GitHub] 불러오기 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"[GitHub] 불러오기 오류: {e}")
        return None


def delete_from_github(user_id: str, data_type: str) -> bool:
    """
    GitHub에서 데이터 삭제

    Args:
        user_id: 사용자 식별자 (personal_number 권장, 예: 'ADMIN001', 'JUEUN')
        data_type: 데이터 타입

    Returns:
        성공 여부
    """
    if not REQUESTS_AVAILABLE:
        return False

    token = get_github_token()
    if not token:
        return False

    config = get_github_config()
    file_path = f"user_data/{user_id}/{data_type}.json.gz"

    sha = _get_file_sha(file_path)
    if not sha:
        return True  # 파일이 없으면 성공으로 처리

    url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/contents/{file_path}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    payload = {
        'message': f"[Auto] Delete {data_type} for user {user_id[:8]}...",
        'sha': sha,
        'branch': config['branch']
    }

    try:
        response = requests.delete(url, headers=headers, json=payload, timeout=15)
        return response.status_code in [200, 204]
    except Exception:
        return False


def list_user_data(user_id: str) -> List[str]:
    """사용자의 저장된 데이터 타입 목록"""
    if not REQUESTS_AVAILABLE:
        return []

    token = get_github_token()
    if not token:
        return []

    config = get_github_config()
    dir_path = f"user_data/{user_id}"

    url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/contents/{dir_path}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    params = {'ref': config['branch']}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            files = response.json()
            return [f['name'].replace('.json.gz', '') for f in files if f['name'].endswith('.json.gz')]
    except Exception:
        pass

    return []


def save_analysis_to_github(user_id: str, block_id: str, result: str, project_info: Optional[Dict] = None) -> bool:
    """분석 결과를 GitHub에 저장 (개별 블록)"""
    data = {
        'block_id': block_id,
        'result': result,
        'project_info': project_info,
        'saved_at': datetime.now().isoformat()
    }
    return save_to_github(user_id, f"analysis_{block_id}", data)


def load_all_analysis_from_github(user_id: str) -> Dict[str, str]:
    """사용자의 모든 분석 결과 불러오기"""
    results = {}

    data_types = list_user_data(user_id)
    for dt in data_types:
        if dt.startswith('analysis_'):
            data = load_from_github(user_id, dt)
            if data and 'block_id' in data and 'result' in data:
                results[data['block_id']] = data['result']

    return results


# GitHub 저장 가능 여부 확인
def is_github_storage_available() -> bool:
    """GitHub 스토리지 사용 가능 여부"""
    return REQUESTS_AVAILABLE and get_github_token() is not None


# ============================================
# 공유 데이터 (블록, 팀, 사용자) 백업/복원
# ============================================

def _save_shared_data(data_type: str, data: Dict) -> bool:
    """공유 데이터를 GitHub에 저장 (shared_data 폴더)"""
    if not REQUESTS_AVAILABLE:
        return False

    token = get_github_token()
    if not token:
        return False

    config = get_github_config()

    if not _ensure_branch_exists():
        return False

    file_path = f"shared_data/{data_type}.json.gz"

    try:
        compressed_content = _compress_data(data)
    except Exception as e:
        print(f"[GitHub] 공유 데이터 압축 실패: {e}")
        return False

    sha = _get_file_sha(file_path)

    url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/contents/{file_path}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    payload = {
        'message': f"[Auto] Update shared {data_type}",
        'content': base64.b64encode(compressed_content.encode('utf-8')).decode('ascii'),
        'branch': config['branch']
    }

    if sha:
        payload['sha'] = sha

    try:
        response = requests.put(url, headers=headers, json=payload, timeout=30)
        if response.status_code in [200, 201]:
            print(f"[GitHub] 공유 데이터 저장 성공: {data_type}")
            return True
        else:
            print(f"[GitHub] 공유 데이터 저장 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"[GitHub] 공유 데이터 API 오류: {e}")
        return False


def _load_shared_data(data_type: str) -> Optional[Dict]:
    """GitHub에서 공유 데이터 불러오기"""
    if not REQUESTS_AVAILABLE:
        return None

    token = get_github_token()
    if not token:
        return None

    config = get_github_config()
    file_path = f"shared_data/{data_type}.json.gz"

    url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/contents/{file_path}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    params = {'ref': config['branch']}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)

        if response.status_code == 200:
            content = response.json().get('content', '')
            decoded = base64.b64decode(content).decode('utf-8')
            data = _decompress_data(decoded)
            print(f"[GitHub] 공유 데이터 불러오기 성공: {data_type}")
            return data
        elif response.status_code == 404:
            return None
        else:
            print(f"[GitHub] 공유 데이터 불러오기 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"[GitHub] 공유 데이터 불러오기 오류: {e}")
        return None


def backup_all_blocks() -> bool:
    """모든 블록 데이터를 GitHub에 백업"""
    try:
        from database.db_manager import execute_query

        result = execute_query("SELECT * FROM blocks")
        blocks = [dict(row) for row in result] if result else []

        return _save_shared_data("blocks", {"blocks": blocks, "updated_at": datetime.now().isoformat()})
    except Exception as e:
        print(f"[GitHub] 블록 백업 오류: {e}")
        return False


def restore_all_blocks() -> bool:
    """GitHub에서 블록 데이터 복원"""
    try:
        data = _load_shared_data("blocks")
        if not data or "blocks" not in data:
            print("[GitHub] 복원할 블록 데이터 없음")
            return False

        from database.db_manager import execute_query

        blocks = data["blocks"]
        restored = 0

        for block in blocks:
            # 이미 존재하는지 확인
            existing = execute_query(
                "SELECT id FROM blocks WHERE block_id = ?",
                (block.get('block_id'),)
            )

            if not existing:
                execute_query(
                    """
                    INSERT INTO blocks (block_id, owner_id, name, category, block_data, visibility, shared_with_teams, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        block.get('block_id'),
                        block.get('owner_id'),
                        block.get('name'),
                        block.get('category'),
                        block.get('block_data'),
                        block.get('visibility'),
                        block.get('shared_with_teams'),
                        block.get('created_at')
                    ),
                    commit=True
                )
                restored += 1

        print(f"[GitHub] {restored}개 블록 복원 완료")
        return True
    except Exception as e:
        print(f"[GitHub] 블록 복원 오류: {e}")
        return False


def backup_all_teams() -> bool:
    """모든 팀 데이터를 GitHub에 백업"""
    try:
        from database.db_manager import execute_query

        result = execute_query("SELECT * FROM teams")
        teams = [dict(row) for row in result] if result else []

        return _save_shared_data("teams", {"teams": teams, "updated_at": datetime.now().isoformat()})
    except Exception as e:
        print(f"[GitHub] 팀 백업 오류: {e}")
        return False


def restore_all_teams() -> bool:
    """GitHub에서 팀 데이터 복원"""
    try:
        data = _load_shared_data("teams")
        if not data or "teams" not in data:
            return False

        from database.db_manager import execute_query

        teams = data["teams"]
        restored = 0

        for team in teams:
            existing = execute_query(
                "SELECT id FROM teams WHERE id = ?",
                (team.get('id'),)
            )

            if not existing:
                execute_query(
                    """
                    INSERT INTO teams (id, name, description, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        team.get('id'),
                        team.get('name'),
                        team.get('description'),
                        team.get('created_at')
                    ),
                    commit=True
                )
                restored += 1

        print(f"[GitHub] {restored}개 팀 복원 완료")
        return True
    except Exception as e:
        print(f"[GitHub] 팀 복원 오류: {e}")
        return False


def backup_all_users() -> bool:
    """모든 사용자 데이터를 GitHub에 백업 (비밀번호 해시 포함)"""
    try:
        from database.db_manager import execute_query

        result = execute_query("SELECT * FROM users")
        users = [dict(row) for row in result] if result else []

        return _save_shared_data("users", {"users": users, "updated_at": datetime.now().isoformat()})
    except Exception as e:
        print(f"[GitHub] 사용자 백업 오류: {e}")
        return False


def restore_all_users() -> bool:
    """GitHub에서 사용자 데이터 복원"""
    try:
        data = _load_shared_data("users")
        if not data or "users" not in data:
            return False

        from database.db_manager import execute_query

        users = data["users"]
        restored = 0

        for user in users:
            existing = execute_query(
                "SELECT id FROM users WHERE personal_number = ?",
                (user.get('personal_number'),)
            )

            if not existing:
                execute_query(
                    """
                    INSERT INTO users (personal_number, display_name, role, team_id, status, last_login, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user.get('personal_number'),
                        user.get('display_name'),
                        user.get('role'),
                        user.get('team_id'),
                        user.get('status', 'active'),
                        user.get('last_login'),
                        user.get('created_at')
                    ),
                    commit=True
                )
                restored += 1

        print(f"[GitHub] {restored}명 사용자 복원 완료")
        return True
    except Exception as e:
        print(f"[GitHub] 사용자 복원 오류: {e}")
        return False


def backup_all_shared_data() -> bool:
    """모든 공유 데이터 백업 (블록, 팀, 사용자)"""
    success = True
    success = backup_all_blocks() and success
    success = backup_all_teams() and success
    success = backup_all_users() and success
    return success


def restore_all_shared_data() -> bool:
    """모든 공유 데이터 복원 (블록, 팀, 사용자)"""
    success = True
    success = restore_all_users() and success  # 사용자 먼저 (FK 때문)
    success = restore_all_teams() and success
    success = restore_all_blocks() and success
    return success

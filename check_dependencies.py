#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
필수 모듈 체크 및 자동 설치 스크립트
앱 시작 전 필수 모듈이 설치되어 있는지 확인하고, 누락 시 자동 설치를 시도합니다.
"""

import sys
import subprocess
import time
from typing import Dict, Tuple, List

# 필수 모듈 정의: (모듈명, 패키지명, 선택적여부)
REQUIRED_MODULES = [
    ("streamlit", "streamlit", False),
    ("dotenv", "python-dotenv", False),
    ("dspy", "dspy-ai", False),
    ("fitz", "PyMuPDF", False),
    ("docx", "python-docx", False),
    ("geopandas", "geopandas", True),  # 선택적 (conda 권장)
    ("folium", "folium", False),
    ("streamlit_folium", "streamlit-folium", False),
]

# geopandas 의존성 (geopandas 설치 시 함께 설치)
GEOPANDAS_DEPS = ["shapely", "pyproj"]


def check_module(module_name: str) -> Tuple[bool, str]:
    """
    모듈 import 테스트
    
    Args:
        module_name: 테스트할 모듈명
        
    Returns:
        (성공여부, 에러메시지)
    """
    try:
        __import__(module_name)
        return True, ""
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def install_package(package_name: str, retry_count: int = 3) -> Tuple[bool, str]:
    """
    패키지 설치 시도
    
    Args:
        package_name: 설치할 패키지명
        retry_count: 재시도 횟수
        
    Returns:
        (성공여부, 에러메시지)
    """
    for attempt in range(1, retry_count + 1):
        try:
            print(f"  [시도 {attempt}/{retry_count}] {package_name} 설치 중...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name, "--upgrade", "--no-warn-script-location"],
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )
            
            if result.returncode == 0:
                # 설치 후 잠시 대기 (Python 모듈 캐시 갱신 시간)
                time.sleep(2)
                return True, ""
            else:
                error_msg = result.stderr or result.stdout
                if attempt < retry_count:
                    print(f"  [경고] 설치 실패, 재시도 중...")
                    time.sleep(3)
                else:
                    return False, error_msg
                    
        except subprocess.TimeoutExpired:
            if attempt < retry_count:
                print(f"  [경고] 타임아웃, 재시도 중...")
                time.sleep(3)
            else:
                return False, "Installation timeout (5 minutes)"
        except Exception as e:
            if attempt < retry_count:
                print(f"  [경고] 오류 발생, 재시도 중...")
                time.sleep(3)
            else:
                return False, str(e)
    
    return False, "Max retries exceeded"


def check_and_install_module(module_name: str, package_name: str, optional: bool = False) -> Tuple[bool, str]:
    """
    모듈 체크 및 필요시 설치
    
    Args:
        module_name: 테스트할 모듈명
        package_name: 설치할 패키지명
        optional: 선택적 모듈 여부
        
    Returns:
        (성공여부, 메시지)
    """
    # 먼저 import 테스트
    success, error = check_module(module_name)
    if success:
        return True, f"✅ {module_name} 이미 설치됨"
    
    # 선택적 모듈이고 실패한 경우 경고만 표시
    if optional:
        print(f"⚠️  {module_name} 누락 (선택적 모듈)")
        print(f"  설치 시도 중...")
    else:
        print(f"❌ {module_name} 누락 (필수 모듈)")
        print(f"  자동 설치 시도 중...")
    
    # geopandas의 경우 의존성도 함께 설치
    if module_name == "geopandas":
        print(f"  geopandas 의존성 설치 중 (shapely, pyproj)...")
        for dep in GEOPANDAS_DEPS:
            dep_success, dep_error = install_package(dep)
            if not dep_success:
                print(f"  [경고] {dep} 설치 실패: {dep_error}")
    
    # 패키지 설치 시도
    install_success, install_error = install_package(package_name)
    
    if not install_success:
        if optional:
            return False, f"⚠️  {module_name} 설치 실패 (선택적 모듈이므로 계속 진행): {install_error[:100]}"
        else:
            return False, f"❌ {module_name} 설치 실패: {install_error[:100]}"
    
    # 설치 후 재검증 (여러 번 시도)
    for verify_attempt in range(1, 4):
        time.sleep(1)  # 모듈 캐시 갱신 대기
        success, error = check_module(module_name)
        if success:
            return True, f"✅ {module_name} 설치 및 검증 완료"
        if verify_attempt < 3:
            print(f"  [검증 {verify_attempt}/3] 재시도 중...")
    
    # 재검증 실패
    if optional:
        return False, f"⚠️  {module_name} 설치 후 검증 실패 (선택적 모듈이므로 계속 진행)"
    else:
        return False, f"❌ {module_name} 설치 후 검증 실패: {error}"


def check_pip() -> Tuple[bool, str]:
    """
    pip 설치 확인 및 필요시 설치
    
    Returns:
        (성공여부, 메시지)
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, "✅ pip 준비 완료"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    # pip가 없으면 설치 시도
    print("⚠️  pip가 설치되어 있지 않습니다. pip 설치 중...")
    try:
        # ensurepip 사용 (Python 3.4+ 내장)
        result = subprocess.run(
            [sys.executable, "-m", "ensurepip", "--upgrade", "--default-pip"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            time.sleep(2)  # 설치 후 대기
            # 재확인
            verify_result = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if verify_result.returncode == 0:
                return True, "✅ pip 설치 완료"
            else:
                return False, "❌ pip 설치 후 검증 실패"
        else:
            error_msg = result.stderr or result.stdout
            return False, f"❌ pip 설치 실패: {error_msg[:100]}"
    except subprocess.TimeoutExpired:
        return False, "❌ pip 설치 타임아웃"
    except Exception as e:
        return False, f"❌ pip 설치 중 오류: {str(e)}"


def main() -> int:
    """
    메인 함수: 모든 필수 모듈 체크 및 설치
    
    Returns:
        종료 코드 (0: 성공, 1: 실패)
    """
    print("=" * 60)
    print("필수 모듈 체크 및 자동 설치")
    print("=" * 60)
    print()
    
    # pip 사전 체크
    print("[사전 체크] pip 설치 확인 중...")
    pip_success, pip_message = check_pip()
    print(pip_message)
    print()
    
    if not pip_success:
        print("❌ pip 설치에 실패했습니다.")
        print("다음을 시도해보세요:")
        print(f"  {sys.executable} -m ensurepip --upgrade")
        print()
        return 1
    
    results: List[Tuple[str, bool, str]] = []
    has_critical_failure = False
    
    for module_name, package_name, optional in REQUIRED_MODULES:
        print(f"[{module_name}] 체크 중...")
        success, message = check_and_install_module(module_name, package_name, optional)
        results.append((module_name, success, message))
        print(message)
        print()
        
        if not success and not optional:
            has_critical_failure = True
    
    # 결과 요약
    print("=" * 60)
    print("체크 결과 요약")
    print("=" * 60)
    
    for module_name, success, message in results:
        status = "✅" if success else ("⚠️" if any(m[0] == module_name and m[2] for m in REQUIRED_MODULES) else "❌")
        print(f"{status} {module_name}: {'성공' if success else '실패'}")
    
    print()
    
    if has_critical_failure:
        print("❌ 필수 모듈 설치에 실패했습니다.")
        print("다음을 시도해보세요:")
        print("  1. install.bat 실행")
        print("  2. 인터넷 연결 확인")
        print("  3. Python 버전 확인 (3.8 이상 필요)")
        return 1
    else:
        print("✅ 모든 필수 모듈이 준비되었습니다.")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)


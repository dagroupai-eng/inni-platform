"""
Colab 환경 설정 스크립트
Google Colab에서 필요한 패키지들을 자동으로 설치합니다.
"""

import subprocess
import sys
import os

def install_package(package):
    """패키지 설치"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} 설치 완료")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ {package} 설치 실패")
        return False

def setup_colab_environment():
    """Colab 환경 설정"""
    print("🚀 Colab 환경 설정을 시작합니다...")
    
    # 필요한 패키지 목록
    packages = [
        "google-generativeai==0.3.2",
        "anthropic==0.7.8", 
        "dspy-ai==2.6.27",
        "PyMuPDF==1.23.8",
        "plotly==6.3.0",
        "pandas==2.3.1",
        "python-docx==0.8.11",
        "Pillow==10.1.0",
        "openpyxl==3.1.2",
        "xlrd==2.0.1",
        "chardet==5.2.0",
        "requests==2.32.5",
        "ipywidgets==8.1.1"
    ]
    
    # 패키지 설치
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n📊 설치 결과: {success_count}/{len(packages)} 패키지 설치 완료")
    
    if success_count == len(packages):
        print("🎉 모든 패키지가 성공적으로 설치되었습니다!")
        return True
    else:
        print("⚠️ 일부 패키지 설치에 실패했습니다. 수동으로 설치해주세요.")
        return False

def check_environment():
    """환경 확인"""
    print("🔍 환경 확인 중...")
    
    # Google Colab 환경 확인
    try:
        import google.colab
        print("✅ Google Colab 환경 확인됨")
    except ImportError:
        print("⚠️ Google Colab 환경이 아닙니다.")
    
    # 필수 패키지 확인
    required_packages = [
        ("google.generativeai", "google-generativeai"),
        ("anthropic", "anthropic"),
        ("dspy", "dspy-ai"),
        ("fitz", "PyMuPDF"),
        ("plotly", "plotly"),
        ("pandas", "pandas"),
        ("docx", "python-docx"),
        ("PIL", "Pillow"),
        ("openpyxl", "openpyxl"),
        ("ipywidgets", "ipywidgets")
    ]
    
    missing_packages = []
    for module, package in required_packages:
        try:
            __import__(module)
            print(f"✅ {package} 확인됨")
        except ImportError:
            print(f"❌ {package} 누락됨")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ 누락된 패키지: {', '.join(missing_packages)}")
        return False
    else:
        print("\n🎉 모든 필수 패키지가 설치되어 있습니다!")
        return True

def main():
    """메인 함수"""
    print("🏗️ Simple Arch Insight - Colab 환경 설정")
    print("=" * 50)
    
    # 환경 확인
    if not check_environment():
        print("\n🔧 누락된 패키지를 설치합니다...")
        setup_colab_environment()
        
        # 재확인
        print("\n🔍 재확인 중...")
        if check_environment():
            print("\n🎉 환경 설정이 완료되었습니다!")
            print("이제 colab_app.py를 실행할 수 있습니다.")
        else:
            print("\n❌ 환경 설정에 실패했습니다.")
            print("수동으로 패키지를 설치해주세요.")
    else:
        print("\n🎉 환경이 이미 설정되어 있습니다!")
        print("colab_app.py를 바로 실행할 수 있습니다.")

if __name__ == "__main__":
    main()

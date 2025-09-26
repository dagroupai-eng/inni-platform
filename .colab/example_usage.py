"""
Colab 사용 예시
Google Colab에서 Simple Arch Insight를 사용하는 다양한 방법을 보여줍니다.
"""

import os
import pandas as pd
from IPython.display import display, HTML
from google.colab import files
import ipywidgets as widgets

def show_example_1_basic_usage():
    """예시 1: 기본 사용법"""
    display(HTML("""
    <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h3>📖 예시 1: 기본 사용법</h3>
        <p>가장 간단한 방법으로 PDF 분석을 시작하는 방법입니다.</p>
    </div>
    """))
    
    code = '''
# 1. 앱 실행
from colab_app import run_colab_app
run_colab_app()

# 2. API 키 설정 (Gemini 권장)
# - Google AI Studio에서 API 키 발급
# - 앱에서 API 키 입력

# 3. PDF 분석
# - 프로젝트명 입력
# - 분석 블록 선택
# - PDF 파일 업로드
'''
    
    display(HTML(f"<pre style='background: #f8f9fa; padding: 15px; border-radius: 5px;'>{code}</pre>"))

def show_example_2_advanced_usage():
    """예시 2: 고급 사용법"""
    display(HTML("""
    <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h3>🔧 예시 2: 고급 사용법</h3>
        <p>여러 프로젝트를 동시에 분석하고 결과를 비교하는 방법입니다.</p>
    </div>
    """))
    
    code = '''
# 1. 여러 프로젝트 분석
projects = [
    "서울대학교 기숙사",
    "연세대학교 도서관", 
    "고려대학교 연구동"
]

# 2. 각 프로젝트별로 분석 실행
for project in projects:
    # 프로젝트별 PDF 업로드 및 분석
    # 결과를 별도로 저장하여 비교 분석
    pass

# 3. 통계 탭에서 전체 분석 결과 확인
'''
    
    display(HTML(f"<pre style='background: #f8f9fa; padding: 15px; border-radius: 5px;'>{code}</pre>"))

def show_example_3_custom_analysis():
    """예시 3: 커스텀 분석"""
    display(HTML("""
    <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h3>🎨 예시 3: 커스텀 분석</h3>
        <p>특정 분석 블록만 선택하여 맞춤형 분석을 수행하는 방법입니다.</p>
    </div>
    """))
    
    code = '''
# 1. 특정 분석 블록만 선택
selected_blocks = [
    "basic_info",      # 기본 정보 추출
    "requirements",    # 요구사항 분석
    "design_suggestions"  # 설계 제안
]

# 2. 특정 AI 모델 선택
model_choice = "gemini"  # 또는 "dspy"

# 3. 분석 실행
# - 프로젝트명: "커스텀 프로젝트"
# - 분석 블록: 위에서 선택한 블록들
# - AI 모델: 선택한 모델
# - PDF 파일: 업로드
'''
    
    display(HTML(f"<pre style='background: #f8f9fa; padding: 15px; border-radius: 5px;'>{code}</pre>"))

def show_example_4_batch_processing():
    """예시 4: 배치 처리"""
    display(HTML("""
    <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h3>⚡ 예시 4: 배치 처리</h3>
        <p>여러 PDF 파일을 한 번에 분석하는 방법입니다.</p>
    </div>
    """))
    
    code = '''
# 1. 여러 PDF 파일 업로드
uploaded_files = files.upload()  # 여러 파일 선택 가능

# 2. 각 파일별로 분석 실행
for filename, file_content in uploaded_files.items():
    if filename.lower().endswith('.pdf'):
        # 파일별 분석 실행
        # 프로젝트명: 파일명에서 추출
        # 분석 블록: 동일하게 적용
        pass

# 3. 통계 탭에서 전체 결과 확인
'''
    
    display(HTML(f"<pre style='background: #f8f9fa; padding: 15px; border-radius: 5px;'>{code}</pre>"))

def show_tips_and_tricks():
    """팁과 트릭"""
    display(HTML("""
    <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h3>💡 팁과 트릭</h3>
    </div>
    """))
    
    tips = [
        "🔑 **API 키 관리**: Gemini API는 무료이므로 먼저 시도해보세요",
        "📄 **PDF 품질**: 텍스트가 포함된 PDF가 분석 품질이 좋습니다",
        "🎯 **블록 선택**: 처음에는 '기본 정보 추출'만 선택해보세요",
        "📊 **결과 저장**: 중요한 분석 결과는 별도로 복사해두세요",
        "🔄 **재분석**: 다른 AI 모델로 같은 PDF를 분석해보세요",
        "📈 **통계 활용**: 여러 프로젝트 분석 후 통계 탭에서 비교해보세요",
        "🗺️ **지도 기능**: 위치 정보가 있는 프로젝트는 지도 탭을 확인해보세요"
    ]
    
    for tip in tips:
        display(HTML(f"<p style='margin: 5px 0;'>{tip}</p>"))

def show_troubleshooting():
    """문제 해결"""
    display(HTML("""
    <div style="background: #f8d7da; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h3>🔧 문제 해결</h3>
    </div>
    """))
    
    problems = [
        {
            "문제": "API 키 오류",
            "해결": "Google AI Studio에서 새 API 키를 발급받아 다시 입력하세요"
        },
        {
            "문제": "PDF 업로드 실패",
            "해결": "파일 크기가 50MB 이하인지 확인하고, PDF 형식인지 확인하세요"
        },
        {
            "문제": "분석 결과가 나오지 않음",
            "해결": "PDF에 텍스트가 포함되어 있는지 확인하고, 다른 AI 모델을 시도해보세요"
        },
        {
            "문제": "패키지 설치 오류",
            "해결": "Colab 런타임을 재시작하고 다시 설치해보세요"
        },
        {
            "문제": "메모리 부족",
            "해결": "큰 PDF 파일은 작은 단위로 나누어 분석하세요"
        }
    ]
    
    for problem in problems:
        display(HTML(f"""
        <div style="background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 5px;">
            <strong>❌ {problem['문제']}</strong><br>
            <small>💡 {problem['해결']}</small>
        </div>
        """))

def run_examples():
    """예시 실행"""
    display(HTML("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(90deg, #4285f4 0%, #34a853 100%); color: white; border-radius: 10px; margin-bottom: 20px;">
        <h1>📚 Simple Arch Insight - 사용 예시</h1>
        <p>다양한 사용 방법과 팁을 확인해보세요</p>
    </div>
    """))
    
    # 예시들 표시
    show_example_1_basic_usage()
    show_example_2_advanced_usage()
    show_example_3_custom_analysis()
    show_example_4_batch_processing()
    show_tips_and_tricks()
    show_troubleshooting()
    
    display(HTML("""
    <div style="background: #d1ecf1; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h3>🚀 시작하기</h3>
        <p>예시를 확인했다면 이제 실제 분석을 시작해보세요!</p>
        <code>from colab_app import run_colab_app<br>run_colab_app()</code>
    </div>
    """))

if __name__ == "__main__":
    run_examples()

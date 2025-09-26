"""
🏗️ Simple Arch Insight - Colab 버전
Google Colab에서 바로 사용할 수 있는 건축 프로젝트 PDF 분석 도구

주요 기능:
- Gemini 1.5 Pro + DSPy 기반 AI 분석
- 7개 분석 블록 시스템
- PDF 텍스트 + 이미지 멀티모달 분석
- 통계 대시보드 및 지도 시각화
"""

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from IPython.display import display, HTML, clear_output
from google.colab import files
import ipywidgets as widgets
import json
import base64
from io import BytesIO
import tempfile
from datetime import datetime

# AI 모델 설정
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import dspy
    import anthropic
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

class ColabArchInsight:
    """Colab용 건축 프로젝트 분석 시스템"""
    
    def __init__(self):
        self.gemini_model = None
        self.dspy_analyzer = None
        self.analysis_history = []
        self.analysis_blocks = self.load_analysis_blocks()
        self.current_project = None
        
    def load_analysis_blocks(self):
        """분석 블록 로드"""
        return {
            "basic_info": {
                "name": "📋 기본 정보 추출 (CoT)",
                "description": "Chain of Thought로 PDF에서 프로젝트의 기본 정보를 추출합니다",
                "prompt": """다음 단계별로 분석해주세요:

1단계: 문서 스캔
- PDF 내용을 읽고 건축 프로젝트 관련 정보 식별

2단계: 정보 분류
- 프로젝트명, 건축주, 대지위치, 건물용도, 주요 요구사항으로 분류

3단계: 정보 정리
- 각 항목별로 명확하게 정리하여 제시

각 단계별 사고 과정을 보여주세요.

PDF 내용: {pdf_content}"""
            },
            "requirements": {
                "name": "🏗️ 건축 요구사항 분석 (CoT)",
                "description": "Chain of Thought로 건축 관련 요구사항을 분석하고 정리합니다",
                "prompt": """다음 단계별로 요구사항을 분석해주세요:

1단계: 요구사항 식별
- PDF에서 건축 관련 요구사항을 찾아내기

2단계: 요구사항 분류
- 공간 요구사항, 기능적 요구사항, 법적 요구사항, 기술적 요구사항으로 분류

3단계: 우선순위 평가
- 각 요구사항의 중요도와 우선순위 평가

4단계: 종합 정리
- 분류된 요구사항을 명확하게 정리하여 제시

각 단계별 사고 과정을 보여주세요.

PDF 내용: {pdf_content}"""
            },
            "design_suggestions": {
                "name": "💡 설계 제안 (CoT)",
                "description": "Chain of Thought로 기본적인 설계 방향과 제안사항을 제공합니다",
                "prompt": """다음 단계별로 설계 제안을 해주세요:

1단계: 현황 분석
- PDF 내용을 바탕으로 프로젝트의 현재 상황 파악

2단계: 설계 방향 도출
- 분석 결과를 바탕으로 설계 컨셉 방향 설정

3단계: 구체적 제안
- 공간 구성, 주요 설계 포인트, 주의사항 제안

4단계: 실행 계획
- 제안사항의 실행 가능성과 구체적 방안 제시

각 단계별 사고 과정을 보여주세요.

PDF 내용: {pdf_content}"""
            },
            "accessibility": {
                "name": "🚶 접근성 평가 (CoT)",
                "description": "Chain of Thought로 대상지의 접근성을 종합적으로 평가합니다",
                "prompt": """다음 단계별로 접근성을 분석해주세요:

1단계: 교통 접근성 분석
- 대중교통 정류장과의 거리 및 연결성 평가
- 도로망 접근성 및 교통 혼잡도 분석

2단계: 보행 접근성 분석
- 보행자 동선 및 보도 연결성 평가
- 장애인 접근성 및 무장애 환경 분석

3단계: 시설 접근성 분석
- 주변 주요 시설(병원, 학교, 상업시설)과의 거리 평가
- 생활 편의시설 접근성 분석

4단계: 종합 평가
- 각 접근성 요소의 가중치를 고려한 종합 점수 산출
- 개선 방안 및 우선순위 제시

각 단계별 사고 과정을 보여주세요.

PDF 내용: {pdf_content}"""
            },
            "zoning": {
                "name": "🏘️ 법규 검증 (CoT)",
                "description": "Chain of Thought로 대상지의 용도지역 및 건축법규를 검증합니다",
                "prompt": """다음 단계별로 법규를 검증해주세요:

1단계: 용도지역 확인
- 대상지의 용도지역 분류 및 허용 용도 확인
- 용도지역별 건축 제한사항 분석

2단계: 건축법규 검토
- 용적률, 건폐율, 높이 제한 등 건축 제한 확인
- 도시계획법상 제한사항 검토

3단계: 특별법 검토
- 문화재보호법, 환경보전법 등 특별법 적용 여부 확인
- 개발제한구역, 보전지역 등 특별지역 여부 확인

4단계: 위험요소 분석
- 법규 위반 가능성 및 리스크 요소 식별
- 대안 및 해결방안 제시

각 단계별 사고 과정을 보여주세요.

PDF 내용: {pdf_content}"""
            },
            "capacity": {
                "name": "📊 수용력 추정 (CoT)",
                "description": "Chain of Thought로 대상지의 개발 수용력을 추정합니다",
                "prompt": """다음 단계별로 수용력을 추정해주세요:

1단계: 물리적 수용력 분석
- 대지면적 및 건축 가능 면적 계산
- 지형, 지질 등 물리적 제약요소 분석

2단계: 법적 수용력 분석
- 용적률, 건폐율 등 법적 제한에 따른 최대 건축면적 계산
- 높이 제한에 따른 최대 건축 규모 추정

3단계: 사회적 수용력 분석
- 주변 인구밀도 및 수요 분석
- 지역사회 수용성 및 갈등 가능성 평가

4단계: 경제적 수용력 분석
- 개발비용 대비 수익성 분석
- 시장 수요 및 공급 상황 고려

5단계: 종합 수용력 평가
- 각 요소를 종합한 최적 개발 규모 제안
- 단계별 개발 방안 제시

각 단계별 사고 과정을 보여주세요.

PDF 내용: {pdf_content}"""
            },
            "feasibility": {
                "name": "💰 사업성 개략 평가 (CoT)",
                "description": "Chain of Thought로 대상지의 사업성을 개략적으로 평가합니다",
                "prompt": """다음 단계별로 사업성을 평가해주세요:

1단계: 시장성 분석
- 지역 시장 규모 및 성장 잠재력 분석
- 경쟁사 현황 및 차별화 요소 분석

2단계: 수익성 분석
- 예상 매출 및 운영비용 추정
- 투자회수기간 및 수익률 계산

3단계: 위험성 분석
- 시장 위험, 법적 위험, 기술적 위험 요소 식별
- 각 위험 요소의 발생 가능성 및 영향도 평가

4단계: 자금 조달 분석
- 필요 자금 규모 및 조달 방안 검토
- 자금 조달 가능성 및 조건 분석

5단계: 종합 평가
- 사업성 종합 점수 산출
- Go/No-Go 결정 및 개선 방안 제시

각 단계별 사고 과정을 보여주세요.

PDF 내용: {pdf_content}"""
            }
        }
    
    def setup_gemini(self, api_key):
        """Gemini API 설정"""
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai 패키지가 설치되지 않았습니다.")
        
        genai.configure(api_key=api_key)
        self.gemini_model = genai.GenerativeModel('gemini-1.5-pro')
        print("✅ Gemini 1.5 Pro 모델 설정 완료")
        
    def setup_dspy(self, anthropic_api_key):
        """DSPy 설정"""
        if not DSPY_AVAILABLE:
            raise ImportError("dspy-ai 패키지가 설치되지 않았습니다.")
        
        # DSPy 설정
        lm = dspy.LM(
            model="claude-3-5-sonnet-20241022",
            provider="anthropic",
            api_key=anthropic_api_key,
            max_tokens=8000
        )
        dspy.configure(lm=lm, track_usage=True)
        
        # DSPy 분석기 클래스 정의
        class SimpleAnalysisSignature(dspy.Signature):
            input = dspy.InputField(desc="분석할 텍스트")
            output = dspy.OutputField(desc="분석 결과")
        
        self.dspy_analyzer = dspy.Predict(SimpleAnalysisSignature)
        print("✅ DSPy + Claude Sonnet 3.5 모델 설정 완료")
    
    def extract_pdf_content(self, pdf_file):
        """PDF 내용 추출"""
        if not PDF_AVAILABLE:
            raise ImportError("PyMuPDF 패키지가 설치되지 않았습니다.")
        
        try:
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            content = ""
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text:
                    content += f"\n--- 페이지 {page_num + 1} ---\n"
                    content += text
                
                # 이미지 정보 (첫 번째 페이지만)
                if page_num == 0:
                    image_list = page.get_images()
                    if image_list:
                        content += "\n[이미지가 포함된 페이지입니다]"
            
            return content[:8000]  # 컨텍스트 제한 고려
            
        except Exception as e:
            return f"PDF 처리 중 오류: {str(e)}"
    
    def analyze_with_gemini(self, pdf_content, block_id):
        """Gemini로 분석"""
        if not self.gemini_model:
            raise ValueError("Gemini 모델이 설정되지 않았습니다.")
        
        try:
            block = self.analysis_blocks[block_id]
            prompt = block["prompt"].format(pdf_content=pdf_content)
            
            response = self.gemini_model.generate_content(prompt)
            
            return {
                "success": True,
                "analysis": response.text,
                "model": "Gemini 1.5 Pro",
                "method": "Gemini Multimodal"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": "Gemini 1.5 Pro",
                "method": "Gemini Multimodal"
            }
    
    def analyze_with_dspy(self, pdf_content, block_id):
        """DSPy로 분석"""
        if not self.dspy_analyzer:
            raise ValueError("DSPy 분석기가 설정되지 않았습니다.")
        
        try:
            block = self.analysis_blocks[block_id]
            prompt = block["prompt"].format(pdf_content=pdf_content)
            
            result = self.dspy_analyzer(input=prompt)
            
            return {
                "success": True,
                "analysis": result.output,
                "model": "Claude Sonnet 3.5 (DSPy)",
                "method": "DSPy + CoT"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": "Claude Sonnet 3.5 (DSPy)",
                "method": "DSPy + CoT"
            }
    
    def show_header(self):
        """헤더 표시"""
        display(HTML("""
        <div style="text-align: center; padding: 20px; background: linear-gradient(90deg, #4285f4 0%, #34a853 100%); color: white; border-radius: 10px; margin-bottom: 20px;">
            <h1>🏗️ Simple Arch Insight - Colab 버전</h1>
            <p>Google Gemini AI + DSPy로 건축 프로젝트 분석</p>
        </div>
        """))
    
    def show_api_setup(self):
        """API 키 설정 인터페이스"""
        display(HTML("""
        <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h4>🔑 API 키 설정</h4>
            <p>사용할 AI 모델의 API 키를 설정해주세요:</p>
        </div>
        """))
        
        # API 키 입력 위젯들
        gemini_key = widgets.Text(
            value='',
            placeholder='AIza... (Gemini API 키)',
            description='Gemini:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='500px')
        )
        
        anthropic_key = widgets.Text(
            value='',
            placeholder='sk-ant-... (Anthropic API 키)',
            description='Anthropic:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='500px')
        )
        
        def on_submit(b):
            try:
                if gemini_key.value:
                    self.setup_gemini(gemini_key.value)
                if anthropic_key.value:
                    self.setup_dspy(anthropic_key.value)
                
                if not gemini_key.value and not anthropic_key.value:
                    display(HTML("<p style='color: red;'>❌ 최소 하나의 API 키를 입력해주세요.</p>"))
                    return
                
                clear_output()
                self.show_main_interface()
                
            except Exception as e:
                display(HTML(f"<p style='color: red;'>❌ API 키 설정 실패: {str(e)}</p>"))
        
        submit_btn = widgets.Button(
            description="API 키 설정 완료",
            button_style='success',
            layout=widgets.Layout(width='200px')
        )
        submit_btn.on_click(on_submit)
        
        display(HTML("""
        <div style="background: #e8f4fd; padding: 10px; border-radius: 5px; margin: 10px 0;">
            <h5>📝 API 키 발급 방법</h5>
            <p><strong>Gemini API:</strong> <a href="https://aistudio.google.com/app/apikey" target="_blank">Google AI Studio</a> (무료)</p>
            <p><strong>Anthropic API:</strong> <a href="https://console.anthropic.com/" target="_blank">Anthropic Console</a> (유료)</p>
        </div>
        """))
        
        display(widgets.VBox([gemini_key, anthropic_key, submit_btn]))
    
    def show_main_interface(self):
        """메인 인터페이스 표시"""
        # 탭 위젯 생성
        tab = widgets.Tab()
        
        # 각 탭 생성
        pdf_tab = self.create_pdf_analysis_tab()
        stats_tab = self.create_statistics_tab()
        map_tab = self.create_map_tab()
        
        tab.children = [pdf_tab, stats_tab, map_tab]
        tab.set_title(0, '📄 PDF 분석')
        tab.set_title(1, '📊 통계')
        tab.set_title(2, '🗺️ 지도')
        
        display(tab)
    
    def create_pdf_analysis_tab(self):
        """PDF 분석 탭 생성"""
        tab_content = widgets.VBox()
        
        # 프로젝트명 입력
        project_name = widgets.Text(
            value='',
            placeholder='프로젝트명을 입력하세요',
            description='프로젝트명:',
            style={'description_width': 'initial'}
        )
        
        # 분석 블록 선택
        block_options = [(block["name"], block_id) for block_id, block in self.analysis_blocks.items()]
        selected_blocks = widgets.SelectMultiple(
            options=block_options,
            value=[block_options[0][1]],  # 기본 선택
            description='분석 블록:',
            style={'description_width': 'initial'}
        )
        
        # AI 모델 선택
        model_choice = widgets.RadioButtons(
            options=[
                ('Gemini 1.5 Pro (권장)', 'gemini'),
                ('Claude Sonnet 3.5 (DSPy)', 'dspy')
            ],
            value='gemini',
            description='AI 모델:',
            style={'description_width': 'initial'}
        )
        
        # 파일 업로드 버튼
        upload_btn = widgets.Button(
            description="📁 PDF 파일 업로드 및 분석",
            button_style='primary',
            layout=widgets.Layout(width='400px')
        )
        
        # 결과 표시 영역
        result_area = widgets.Output()
        
        def on_analyze_click(b):
            with result_area:
                clear_output()
                self.run_analysis(project_name.value, selected_blocks.value, model_choice.value)
        
        upload_btn.on_click(on_analyze_click)
        
        tab_content.children = [
            project_name,
            selected_blocks,
            model_choice,
            upload_btn,
            result_area
        ]
        
        return tab_content
    
    def run_analysis(self, project_name, selected_blocks, model_choice):
        """분석 실행"""
        if not project_name:
            display(HTML("<p style='color: red;'>❌ 프로젝트명을 입력해주세요.</p>"))
            return
        
        if not selected_blocks:
            display(HTML("<p style='color: red;'>❌ 분석 블록을 선택해주세요.</p>"))
            return
        
        display(HTML(f"<h3>📄 {project_name} - PDF 분석</h3>"))
        
        # 파일 업로드
        uploaded = files.upload()
        
        if uploaded:
            for filename, file_content in uploaded.items():
                if filename.lower().endswith('.pdf'):
                    display(HTML(f"<p>✅ <strong>{filename}</strong> 업로드 완료!</p>"))
                    
                    # PDF 텍스트 추출
                    pdf_content = self.extract_pdf_content(file_content)
                    display(HTML(f"<p>📄 텍스트 추출 완료 (길이: {len(pdf_content)}자)</p>"))
                    
                    # 선택된 블록들로 분석
                    for block_id in selected_blocks:
                        block_name = self.analysis_blocks[block_id]["name"]
                        display(HTML(f"<h4>🔍 {block_name} 분석 중...</h4>"))
                        
                        # AI 모델에 따라 분석 실행
                        if model_choice == 'gemini':
                            result = self.analyze_with_gemini(pdf_content, block_id)
                        else:
                            result = self.analyze_with_dspy(pdf_content, block_id)
                        
                        if result["success"]:
                            display(HTML(f"""
                            <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
                                <h5>📊 {block_name} 결과</h5>
                                <pre style="white-space: pre-wrap; font-family: monospace; background: white; padding: 10px; border-radius: 5px;">{result['analysis']}</pre>
                                <small style="color: #666;">모델: {result['model']} | 방법: {result['method']}</small>
                            </div>
                            """))
                            
                            # 분석 기록 저장
                            self.analysis_history.append({
                                'project_name': project_name,
                                'filename': filename,
                                'block_id': block_id,
                                'block_name': block_name,
                                'result': result['analysis'],
                                'model': result['model'],
                                'timestamp': datetime.now()
                            })
                            
                        else:
                            display(HTML(f"<p style='color: red;'>❌ 분석 실패: {result['error']}</p>"))
                else:
                    display(HTML(f"<p style='color: red;'>❌ <strong>{filename}</strong>은 PDF 파일이 아닙니다.</p>"))
    
    def create_statistics_tab(self):
        """통계 탭 생성"""
        tab_content = widgets.VBox()
        
        # 통계 표시 영역
        stats_area = widgets.Output()
        
        def show_stats():
            with stats_area:
                clear_output()
                self.show_statistics()
        
        # 통계 새로고침 버튼
        refresh_btn = widgets.Button(description="📊 통계 새로고침")
        refresh_btn.on_click(lambda b: show_stats())
        
        tab_content.children = [refresh_btn, stats_area]
        
        # 초기 통계 표시
        show_stats()
        
        return tab_content
    
    def show_statistics(self):
        """통계 표시"""
        if not self.analysis_history:
            display(HTML("<p>📊 분석 기록이 없습니다. 먼저 PDF를 분석해주세요.</p>"))
            return
        
        display(HTML("<h3>📊 분석 통계</h3>"))
        
        df = pd.DataFrame(self.analysis_history)
        
        # 프로젝트별 분석 횟수
        if len(df) > 0:
            project_stats = df.groupby('project_name').size().reset_index(name='분석횟수')
            
            fig1 = px.bar(
                project_stats,
                x='project_name',
                y='분석횟수',
                title='프로젝트별 분석 횟수',
                color='분석횟수',
                color_continuous_scale='Blues'
            )
            fig1.show()
            
            # 분석 블록별 사용 현황
            block_stats = df.groupby('block_name').size().reset_index(name='사용횟수')
            
            fig2 = px.pie(
                block_stats,
                values='사용횟수',
                names='block_name',
                title='분석 블록 사용 현황'
            )
            fig2.show()
            
            # 최근 분석 기록
            display(HTML("<h4>📋 최근 분석 기록</h4>"))
            recent_df = df.sort_values('timestamp', ascending=False).head(10)
            
            for _, row in recent_df.iterrows():
                display(HTML(f"""
                <div style="background: #f0f0f0; padding: 10px; margin: 5px 0; border-radius: 5px;">
                    <strong>{row['project_name']}</strong> - {row['block_name']}<br>
                    <small>파일: {row['filename']} | 모델: {row['model']} | 시간: {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</small>
                </div>
                """))
    
    def create_map_tab(self):
        """지도 탭 생성"""
        tab_content = widgets.VBox()
        
        # 지도 표시 영역
        map_area = widgets.Output()
        
        def show_map():
            with map_area:
                clear_output()
                self.show_simple_map()
        
        # 지도 새로고침 버튼
        refresh_btn = widgets.Button(description="🗺️ 지도 새로고침")
        refresh_btn.on_click(lambda b: show_map())
        
        tab_content.children = [refresh_btn, map_area]
        
        # 초기 지도 표시
        show_map()
        
        return tab_content
    
    def show_simple_map(self):
        """간단한 지도 표시"""
        display(HTML("<h3>🗺️ 프로젝트 위치 정보</h3>"))
        
        # 샘플 데이터 (실제로는 분석 기록에서 추출)
        sample_data = {
            '프로젝트명': ['서울대학교 건축학과', '연세대학교 건축학과', '고려대학교 건축학과'],
            '위도': [37.4598, 37.5640, 37.5906],
            '경도': [126.9515, 126.9390, 127.0266],
            '지역': ['서울시 관악구', '서울시 서대문구', '서울시 성북구']
        }
        
        df = pd.DataFrame(sample_data)
        
        # Plotly 지도 생성
        fig = px.scatter_mapbox(
            df,
            lat='위도',
            lon='경도',
            hover_name='프로젝트명',
            hover_data=['지역'],
            color='지역',
            zoom=10,
            height=500
        )
        
        fig.update_layout(
            mapbox_style="open-street-map",
            title="서울 지역 대학교 건축학과 위치"
        )
        
        fig.show()
        
        # 데이터 테이블도 표시
        display(df)

def run_colab_app():
    """Colab 앱 실행"""
    # 필요한 패키지 설치 확인
    missing_packages = []
    
    if not GEMINI_AVAILABLE:
        missing_packages.append("google-generativeai")
    if not DSPY_AVAILABLE:
        missing_packages.append("dspy-ai anthropic")
    if not PDF_AVAILABLE:
        missing_packages.append("PyMuPDF")
    
    if missing_packages:
        display(HTML(f"""
        <div style="background: #f8d7da; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h4>⚠️ 필요한 패키지 설치</h4>
            <p>다음 패키지들을 설치해주세요:</p>
            <code>!pip install {' '.join(missing_packages)}</code>
        </div>
        """))
        return
    
    # 앱 초기화
    app = ColabArchInsight()
    
    # 헤더 표시
    app.show_header()
    
    # API 키 설정 또는 메인 인터페이스 표시
    if not app.gemini_model and not app.dspy_analyzer:
        app.show_api_setup()
    else:
        app.show_main_interface()

# Colab에서 실행
if __name__ == "__main__":
    run_colab_app()

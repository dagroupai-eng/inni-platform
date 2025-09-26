"""
🏗️ Simple Arch Insight - Colab 버전
Google Colab에서 바로 사용할 수 있는 건축 프로젝트 PDF 분석 도구
"""

import os
import pandas as pd
import plotly.express as px
from IPython.display import display, HTML, clear_output
from google.colab import files
from datetime import datetime
import json

# AI 모델 설정
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import dspy
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

class AnalysisBlocks:
    """분석 블록 관리 클래스"""
    
    def __init__(self):
        self.blocks = self.load_analysis_blocks()
        self.custom_blocks = {}  # 사용자 정의 블록
    
    def load_analysis_blocks(self):
        """분석 블록 로드"""
        return {
            "basic_info": {
                "name": "📋 기본 정보 추출",
                "description": "PDF에서 프로젝트의 기본 정보를 추출합니다",
                "prompt": """다음 건축 프로젝트 PDF 내용을 분석해주세요:

**분석 요청사항:**
1. 프로젝트명 및 개요
2. 건축주 및 설계자 정보
3. 대지 위치 및 규모
4. 건물 용도 및 주요 기능
5. 건축 면적 및 규모
6. 주요 특징 및 특이사항

**분석 형식:**
- 각 항목별로 명확하게 정리
- 구체적인 수치와 정보 포함
- 누락된 정보는 "정보 없음"으로 표시

PDF 내용: {pdf_content}"""
            },
            "requirements": {
                "name": "🏗️ 건축 요구사항 분석",
                "description": "건축 관련 요구사항을 분석하고 정리합니다",
                "prompt": """다음 건축 프로젝트 PDF에서 요구사항을 분석해주세요:

**분석 요청사항:**
1. 공간 요구사항
   - 필요한 공간 종류 및 면적
   - 공간 간 연결성 요구사항
   - 특수 공간 요구사항

2. 기능적 요구사항
   - 건물의 주요 기능
   - 사용자 편의성 요구사항
   - 운영 효율성 요구사항

3. 법적 요구사항
   - 건축법규 관련 요구사항
   - 방화, 방재 관련 요구사항
   - 접근성 관련 요구사항

4. 기술적 요구사항
   - 구조적 요구사항
   - 설비 관련 요구사항
   - 환경 친화적 요구사항

**분석 형식:**
- 각 요구사항별로 구체적으로 정리
- 우선순위 및 중요도 표시
- 실현 가능성 평가

PDF 내용: {pdf_content}"""
            },
            "design_suggestions": {
                "name": "💡 설계 제안",
                "description": "기본적인 설계 방향과 제안사항을 제공합니다",
                "prompt": """다음 건축 프로젝트 PDF를 바탕으로 설계 제안을 해주세요:

**분석 요청사항:**
1. 설계 컨셉 제안
   - 건축적 아이디어 및 컨셉
   - 공간 구성 방향
   - 외관 및 형태 제안

2. 공간 계획 제안
   - 동선 계획
   - 공간 배치 제안
   - 기능별 공간 구성

3. 기술적 제안
   - 구조 시스템 제안
   - 설비 계획 제안
   - 재료 및 마감 제안

4. 환경 친화적 제안
   - 에너지 효율성 제안
   - 자연 채광 및 환기 계획
   - 친환경 재료 활용

**분석 형식:**
- 각 제안별로 구체적인 방안 제시
- 실현 가능성 및 효과 분석
- 대안 제안 포함

PDF 내용: {pdf_content}"""
            },
            "accessibility": {
                "name": "🚶 접근성 평가",
                "description": "대상지의 접근성을 종합적으로 평가합니다",
                "prompt": """다음 건축 프로젝트 PDF를 바탕으로 접근성을 평가해주세요:

**분석 요청사항:**
1. 교통 접근성
   - 대중교통 연결성
   - 도로 접근성
   - 주차 시설 접근성

2. 보행 접근성
   - 보행자 동선
   - 보도 연결성
   - 장애인 접근성

3. 시설 접근성
   - 주변 시설과의 거리
   - 생활 편의시설 접근성
   - 응급시설 접근성

4. 건물 내 접근성
   - 수평/수직 동선
   - 장애인 편의시설
   - 안전 시설

**분석 형식:**
- 각 접근성 요소별 점수 평가 (1-10점)
- 개선 방안 제시
- 우선순위별 개선 계획

PDF 내용: {pdf_content}"""
            },
            "feasibility": {
                "name": "💰 사업성 평가",
                "description": "대상지의 사업성을 개략적으로 평가합니다",
                "prompt": """다음 건축 프로젝트 PDF를 바탕으로 사업성을 평가해주세요:

**분석 요청사항:**
1. 시장성 분석
   - 지역 시장 규모
   - 수요 분석
   - 경쟁사 현황

2. 수익성 분석
   - 예상 매출
   - 운영비용
   - 투자회수기간

3. 위험성 분석
   - 시장 위험
   - 법적 위험
   - 기술적 위험

4. 자금 조달 분석
   - 필요 자금 규모
   - 조달 방안
   - 자금 조달 가능성

**분석 형식:**
- 각 요소별 점수 평가 (1-10점)
- 종합 사업성 점수 산출
- Go/No-Go 결정 및 근거

PDF 내용: {pdf_content}"""
            }
        }
    
    def get_all_blocks(self):
        """모든 분석 블록 반환 (기본 + 사용자 정의)"""
        return {**self.blocks, **self.custom_blocks}
    
    def get_block_names(self):
        """분석 블록 이름 목록 반환"""
        all_blocks = self.get_all_blocks()
        return [block["name"] for block in all_blocks.values()]
    
    def get_block_by_id(self, block_id):
        """ID로 분석 블록 반환"""
        all_blocks = self.get_all_blocks()
        return all_blocks.get(block_id)
    
    def add_custom_block(self, block_id, name, description, prompt):
        """사용자 정의 분석 블록 추가"""
        self.custom_blocks[block_id] = {
            "name": name,
            "description": description,
            "prompt": prompt
        }
        print(f"✅ 사용자 정의 블록 '{name}' 추가 완료!")
    
    def remove_custom_block(self, block_id):
        """사용자 정의 분석 블록 제거"""
        if block_id in self.custom_blocks:
            block_name = self.custom_blocks[block_id]["name"]
            del self.custom_blocks[block_id]
            print(f"✅ 사용자 정의 블록 '{block_name}' 제거 완료!")
        else:
            print(f"❌ 블록 ID '{block_id}'를 찾을 수 없습니다.")
    
    def list_custom_blocks(self):
        """사용자 정의 블록 목록 표시"""
        if not self.custom_blocks:
            print("📝 사용자 정의 블록이 없습니다.")
            return
        
        print("📝 사용자 정의 분석 블록:")
        for block_id, block in self.custom_blocks.items():
            print(f"  - {block_id}: {block['name']}")
    
    def save_custom_blocks(self, filename="custom_blocks.json"):
        """사용자 정의 블록을 파일로 저장"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.custom_blocks, f, ensure_ascii=False, indent=2)
            print(f"✅ 사용자 정의 블록이 '{filename}'에 저장되었습니다.")
        except Exception as e:
            print(f"❌ 저장 실패: {str(e)}")
    
    def load_custom_blocks(self, filename="custom_blocks.json"):
        """파일에서 사용자 정의 블록 로드"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.custom_blocks = json.load(f)
            print(f"✅ 사용자 정의 블록이 '{filename}'에서 로드되었습니다.")
        except FileNotFoundError:
            print(f"📝 '{filename}' 파일이 없습니다. 새로 시작합니다.")
        except Exception as e:
            print(f"❌ 로드 실패: {str(e)}")

class PDFProcessor:
    """PDF 처리 클래스"""
    
    def __init__(self):
        if not PDF_AVAILABLE:
            raise ImportError("PyMuPDF 패키지가 설치되지 않았습니다.")
    
    def extract_content(self, pdf_file):
        """PDF 내용 추출"""
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

class GeminiAnalyzer:
    """Gemini AI 분석 클래스"""
    
    def __init__(self):
        self.model = None
    
    def setup(self, api_key):
        """Gemini API 설정"""
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai 패키지가 설치되지 않았습니다.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        print("✅ Gemini 1.5 Pro 모델 설정 완료")
    
    def analyze(self, pdf_content, block):
        """Gemini로 분석"""
        if not self.model:
            raise ValueError("Gemini 모델이 설정되지 않았습니다.")
        
        try:
            import time
            time.sleep(1)  # API 요청 간격 조정
            
            prompt = block["prompt"].format(pdf_content=pdf_content)
            response = self.model.generate_content(prompt)
            
            return {
                "success": True,
                "analysis": response.text,
                "model": "Gemini 1.5 Pro",
                "method": "Gemini Multimodal"
            }
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                error_msg = "API 할당량 초과. 잠시 후 다시 시도하거나 다른 API 키를 사용하세요."
            elif "400" in error_msg:
                error_msg = "잘못된 요청. PDF 내용을 확인해주세요."
            
            return {
                "success": False,
                "error": error_msg,
                "model": "Gemini 1.5 Pro",
                "method": "Gemini Multimodal"
            }


class GeminiCoTAnalyzer:
    """Gemini + DSPy CoT 분석 클래스"""
    
    def __init__(self):
        self.model = None
        self.lm = None
    
    def setup(self, api_key):
        """Gemini API 및 DSPy 설정"""
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai 패키지가 설치되지 않았습니다.")
        if not DSPY_AVAILABLE:
            raise ImportError("dspy-ai 패키지가 설치되지 않았습니다.")
        
        try:
            # Gemini 설정
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro')
            
            # DSPy 설정
            self.lm = dspy.Google("models/gemini-1.5-pro", api_key=api_key)
            dspy.settings.configure(lm=self.lm)
            
            print("✅ Gemini CoT 모델 설정 완료")
        except Exception as e:
            raise Exception(f"Gemini CoT 설정 실패: {str(e)}")
    
    def analyze(self, pdf_content, block):
        """CoT 방식으로 분석"""
        if not self.model or not self.lm:
            raise ValueError("Gemini CoT 모델이 설정되지 않았습니다.")
        
        try:
            import time
            time.sleep(1)  # API 요청 간격 조정
            
            # CoT 프롬프트 생성
            cot_prompt = self._create_cot_prompt(pdf_content, block)
            
            # DSPy CoT 분석 실행
            response = self.lm(cot_prompt)
            
            return {
                "success": True,
                "analysis": response,
                "model": "Gemini 1.5 Pro + DSPy CoT",
                "method": "Chain of Thought"
            }
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                error_msg = "API 할당량 초과. 잠시 후 다시 시도하거나 다른 API 키를 사용하세요."
            elif "400" in error_msg:
                error_msg = "잘못된 요청. PDF 내용을 확인해주세요."
            
            return {
                "success": False,
                "error": error_msg,
                "model": "Gemini 1.5 Pro + DSPy CoT",
                "method": "Chain of Thought"
            }
    
    def _create_cot_prompt(self, pdf_content, block):
        """CoT 프롬프트 생성"""
        base_prompt = block["prompt"].format(pdf_content=pdf_content)
        
        cot_instruction = """
다음 단계를 따라 체계적으로 분석해주세요:

1단계: 문제 이해
- 주어진 PDF 내용에서 핵심 정보를 파악하세요
- 분석해야 할 주요 요소들을 식별하세요

2단계: 정보 추출
- 관련된 구체적인 데이터와 사실을 추출하세요
- 중요한 수치, 날짜, 위치, 규모 등을 정리하세요

3단계: 분석 및 해석
- 추출한 정보를 바탕으로 심층 분석을 수행하세요
- 각 요소들 간의 관계와 영향을 분석하세요

4단계: 결론 및 제안
- 분석 결과를 종합하여 명확한 결론을 도출하세요
- 실용적이고 구체적인 제안사항을 제시하세요

각 단계별로 상세한 설명과 근거를 제시해주세요.
"""
        
        return f"{cot_instruction}\n\n{base_prompt}"


class StatisticsManager:
    """통계 관리 클래스"""
    
    def __init__(self):
        self.analysis_history = []
    
    def add_analysis(self, project_name, filename, block_id, block_name, result, model):
        """분석 기록 추가"""
        self.analysis_history.append({
            'project_name': project_name,
            'filename': filename,
            'block_id': block_id,
            'block_name': block_name,
            'result': result,
            'model': model,
            'timestamp': datetime.now()
        })
    
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

class SimpleArchInsight:
    """Colab용 건축 프로젝트 분석 시스템"""
    
    def __init__(self):
        self.analysis_blocks = AnalysisBlocks()
        self.pdf_processor = PDFProcessor() if PDF_AVAILABLE else None
        self.gemini_analyzer = GeminiAnalyzer()
        self.gemini_cot_analyzer = GeminiCoTAnalyzer()
        self.stats_manager = StatisticsManager()
        self.current_analyzer = None
    
    def show_header(self):
        """헤더 표시"""
        display(HTML("""
        <div style="text-align: center; padding: 20px; background: linear-gradient(90deg, #4285f4 0%, #34a853 100%); color: white; border-radius: 10px; margin-bottom: 20px;">
            <h1>🏗️ Simple Arch Insight - Colab 버전</h1>
            <p>Google Gemini AI로 건축 프로젝트 분석</p>
        </div>
        """))
    
    def show_api_setup(self):
        """API 키 설정 인터페이스"""
        display(HTML("""
        <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h4>🔑 AI 모델 선택 및 API 키 설정</h4>
            <p>사용할 AI 모델을 선택하고 API 키를 입력해주세요:</p>
            <p><strong>1. Gemini (무료, 기본)</strong>: <a href="https://aistudio.google.com/app/apikey" target="_blank">🔗 Google AI Studio</a></p>
            <p><strong>2. Gemini CoT (무료, 고품질)</strong>: <a href="https://aistudio.google.com/app/apikey" target="_blank">🔗 Google AI Studio</a></p>
        </div>
        """))
        
        # AI 모델 선택
        print("🤖 사용할 AI 모델을 선택하세요:")
        print("1. Gemini 1.5 Pro (무료, 기본 분석)")
        print("2. Gemini CoT (무료, Chain of Thought 분석)")
        
        model_choice = input("선택 (1 또는 2): ").strip()
        
        # API 키 입력
        api_key = input("Gemini API 키를 입력하세요: ")
        
        if model_choice == "1":
            try:
                self.gemini_analyzer.setup(api_key)
                self.current_analyzer = self.gemini_analyzer
                print("✅ Gemini 기본 모델 설정 완료!")
                return True
            except Exception as e:
                print(f"❌ Gemini API 키 설정 실패: {str(e)}")
                return False
        elif model_choice == "2":
            try:
                self.gemini_cot_analyzer.setup(api_key)
                self.current_analyzer = self.gemini_cot_analyzer
                print("✅ Gemini CoT 모델 설정 완료!")
                return True
            except Exception as e:
                print(f"❌ Gemini CoT API 키 설정 실패: {str(e)}")
                return False
        else:
            print("❌ 잘못된 선택입니다. Gemini 기본 모델을 설정합니다.")
            try:
                self.gemini_analyzer.setup(api_key)
                self.current_analyzer = self.gemini_analyzer
                print("✅ Gemini 설정 완료!")
                return True
            except Exception as e:
                print(f"❌ API 키 설정 실패: {str(e)}")
                return False
    
    def show_main_interface(self):
        """메인 인터페이스 표시"""
        display(HTML("""
        <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h3>📄 PDF 분석 준비 완료!</h3>
            <p>아래 셀에서 분석을 시작하세요.</p>
        </div>
        """))
        
        # 분석 블록 선택
        print("\n📋 사용 가능한 분석 블록:")
        all_blocks = self.analysis_blocks.get_all_blocks()
        for i, (block_id, block) in enumerate(all_blocks.items(), 1):
            block_type = "🔧" if block_id in self.analysis_blocks.custom_blocks else "📋"
            print(f"{i}. {block_type} {block['name']}")
        
        print("\n🎯 분석을 시작하려면 다음 셀을 실행하세요!")
        print("💡 사용자 정의 블록을 추가하려면 'block_manager' 셀을 실행하세요!")
    
    def run_analysis(self, project_name, selected_blocks):
        """분석 실행"""
        if not project_name:
            print("❌ 프로젝트명을 입력해주세요.")
            return
        
        if not selected_blocks:
            print("❌ 분석 블록을 선택해주세요.")
            return
        
        # AI 분석기 확인
        if not self.current_analyzer:
            print("❌ AI 모델이 설정되지 않았습니다.")
            print("💡 앱을 다시 실행하고 API 키를 설정해주세요.")
            return
        
        display(HTML(f"<h3>📄 {project_name} - PDF 분석</h3>"))
        
        # 파일 업로드
        print("📁 PDF 파일을 업로드해주세요...")
        uploaded = files.upload()
        
        if uploaded:
            for filename, file_content in uploaded.items():
                if filename.lower().endswith('.pdf'):
                    display(HTML(f"<p>✅ <strong>{filename}</strong> 업로드 완료!</p>"))
                    
                    # PDF 텍스트 추출
                    if self.pdf_processor:
                        pdf_content = self.pdf_processor.extract_content(file_content)
                        display(HTML(f"<p>📄 텍스트 추출 완료 (길이: {len(pdf_content)}자)</p>"))
                        
                        # 선택된 블록들로 분석
                        for block_id in selected_blocks:
                            block = self.analysis_blocks.get_block_by_id(block_id)
                            if block:
                                display(HTML(f"<h4>🔍 {block['name']} 분석 중...</h4>"))
                                
                                # AI 분석 실행
                                try:
                                    result = self.current_analyzer.analyze(pdf_content, block)
                                    
                                    if result["success"]:
                                        display(HTML(f"""
                                        <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
                                            <h5>📊 {block['name']} 결과</h5>
                                            <pre style="white-space: pre-wrap; font-family: monospace; background: white; padding: 10px; border-radius: 5px;">{result['analysis']}</pre>
                                            <small style="color: #666;">모델: {result['model']} | 방법: {result['method']}</small>
                                        </div>
                                        """))
                                        
                                        # 분석 기록 저장
                                        self.stats_manager.add_analysis(
                                            project_name, filename, block_id, 
                                            block['name'], result['analysis'], result['model']
                                        )
                                        
                                    else:
                                        display(HTML(f"<p style='color: red;'>❌ 분석 실패: {result['error']}</p>"))
                                        
                                except Exception as e:
                                    display(HTML(f"<p style='color: red;'>❌ 분석 중 오류 발생: {str(e)}</p>"))
                            else:
                                display(HTML(f"<p style='color: red;'>❌ 블록 ID '{block_id}'를 찾을 수 없습니다.</p>"))
                    else:
                        display(HTML("<p style='color: red;'>❌ PDF 처리기가 초기화되지 않았습니다.</p>"))
                else:
                    display(HTML(f"<p style='color: red;'>❌ <strong>{filename}</strong>은 PDF 파일이 아닙니다.</p>"))
    
    def show_statistics(self):
        """통계 표시"""
        self.stats_manager.show_statistics()

def run_simple_arch_insight():
    """Simple Arch Insight 실행"""
    # 필요한 패키지 설치 확인
    missing_packages = []
    
    if not GEMINI_AVAILABLE:
        missing_packages.append("google-generativeai")
    if not DSPY_AVAILABLE:
        missing_packages.append("dspy-ai")
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
        return None
    
    # 앱 초기화
    app = SimpleArchInsight()
    
    # 헤더 표시
    app.show_header()
    
    # API 키 설정
    if not app.current_analyzer:
        success = app.show_api_setup()
        if not success:
            print("❌ API 키 설정에 실패했습니다. 다시 시도해주세요.")
            return app
    
    # 메인 인터페이스 표시
    app.show_main_interface()
    
    return app

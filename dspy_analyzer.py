import dspy
import os
from dotenv import load_dotenv

# 환경변수 로드 (안전하게 처리)
try:
    load_dotenv()
except UnicodeDecodeError:
    # .env 파일에 인코딩 문제가 있는 경우 무시
    pass

# 간단한 Signature 정의
class SimpleAnalysisSignature(dspy.Signature):
    """간단한 분석을 위한 Signature"""
    input = dspy.InputField(desc="분석할 텍스트")
    output = dspy.OutputField(desc="분석 결과")

class EnhancedArchAnalyzer:
    """dA_AI와 동일한 방식으로 DSPy를 사용하는 건축 분석기"""
    
    def __init__(self):
        """DSPy 설정 초기화 (dA_AI와 동일한 방식)"""
        self.setup_dspy()
    
    def setup_dspy(self):
        """dA_AI와 동일한 DSPy 설정"""
        # Streamlit secrets와 환경변수 모두 확인
        try:
            import streamlit as st
            anthropic_api_key = st.secrets.get('ANTHROPIC_API_KEY') or os.environ.get('ANTHROPIC_API_KEY')
        except:
            # Streamlit이 아닌 환경에서는 환경변수만 사용
            anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
        
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY를 설정해주세요.")
        
        if not getattr(dspy.settings, "lm", None):
            try:
                # DSPy 3.0에서 올바른 LM 사용법
                lm = dspy.LM(
                    model="claude-3-5-sonnet-20241022",  # 사용 가능한 Claude 모델
                    provider="anthropic",
                    api_key=anthropic_api_key,
                    max_tokens=8000
                )
                dspy.configure(lm=lm, track_usage=True)
                print("✅ Claude Sonnet 3.5 모델이 성공적으로 설정되었습니다.")
            except Exception as e:
                print(f"❌ Claude 모델 설정 실패: {e}")
                # 대안으로 OpenAI 모델 시도
                try:
                    openai_api_key = os.environ.get('OPENAI_API_KEY')
                    if openai_api_key:
                        lm = dspy.LM(
                            model="gpt-4o-mini",
                            provider="openai",
                            api_key=openai_api_key,
                            max_tokens=8000
                        )
                        dspy.configure(lm=lm, track_usage=True)
                        print("✅ OpenAI GPT-4o-mini 모델이 성공적으로 설정되었습니다.")
                    else:
                        raise ValueError("Claude와 OpenAI API 키가 모두 없습니다.")
                except Exception as e2:
                    print(f"❌ 대안 모델 설정도 실패: {e2}")
                    raise
    
    def analyze_project(self, project_info, pdf_text):
        """프로젝트 분석 (dA_AI와 동일한 방식)"""
        prompt = f"""
다음 건축 프로젝트 정보를 바탕으로 Chain of Thought 방식으로 분석해주세요:

**프로젝트 정보:**
- 프로젝트명: {project_info.get('project_name', 'N/A')}
- 프로젝트 유형: {project_info.get('project_type', 'N/A')}
- 위치: {project_info.get('location', 'N/A')}
- 규모: {project_info.get('scale', 'N/A')}

**PDF 문서 내용:**
{pdf_text[:3000] if pdf_text else "PDF 문서가 없습니다."}

다음 형식으로 분석해주세요:

## 🏗️ 프로젝트 개요
- 프로젝트명
- 주요 특징
- 건축적 의미

## 📋 기본 정보 추출 (CoT)
- 핵심 키워드
- 우선순위
"""
        
        try:
            # DSPy Predict 사용 (signature 포함)
            result = dspy.Predict(SimpleAnalysisSignature)(input=prompt)
            
            return {
                "success": True,
                "analysis": result.output,
                "model": "claude-sonnet-4-20250514 (DSPy)",
                "method": "DSPy + CoT"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": "claude-sonnet-4-20250514 (DSPy)",
                "method": "DSPy + CoT"
            }
    
    def analyze_custom_block(self, prompt, pdf_text):
        """사용자 정의 블록 분석 (dA_AI와 동일한 방식)"""
        # 사용자 정의 프롬프트에 PDF 텍스트 삽입
        full_prompt = f"""
{prompt}

**PDF 문서 내용:**
{pdf_text[:3000] if pdf_text else "PDF 문서가 없습니다."}

위 내용을 바탕으로 분석해주세요.
"""
        
        try:
            # DSPy Predict 사용 (signature 포함)
            result = dspy.Predict(SimpleAnalysisSignature)(input=full_prompt)
            
            return {
                "success": True,
                "analysis": result.output,
                "model": "claude-sonnet-4-20250514 (DSPy)",
                "method": "DSPy + Custom CoT"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": "claude-sonnet-4-20250514 (DSPy)",
                "method": "DSPy + Custom CoT"
            }
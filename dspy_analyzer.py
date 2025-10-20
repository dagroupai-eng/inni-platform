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

class BasicInfoSignature(dspy.Signature):
    """기본 정보 추출을 위한 Signature"""
    input = dspy.InputField(desc="프로젝트 기본 정보를 추출할 문서")
    output = dspy.OutputField(desc="체계적으로 추출된 기본 정보")

class RequirementsSignature(dspy.Signature):
    """요구사항 분석을 위한 Signature"""
    input = dspy.InputField(desc="건축 요구사항을 분석할 문서")
    output = dspy.OutputField(desc="분류되고 우선순위가 설정된 요구사항 분석")

class DesignSignature(dspy.Signature):
    """설계 제안을 위한 Signature"""
    input = dspy.InputField(desc="설계 방향을 제안할 문서")
    output = dspy.OutputField(desc="구체적인 설계 제안과 실행 계획")

class InvestmentSignature(dspy.Signature):
    """투자 지표 계산을 위한 Signature"""
    input = dspy.InputField(desc="투자 지표를 계산할 문서")
    output = dspy.OutputField(desc="계산된 투자 지표와 재무 분석")

class AccessibilitySignature(dspy.Signature):
    """접근성 평가를 위한 Signature"""
    input = dspy.InputField(desc="접근성을 평가할 문서")
    output = dspy.OutputField(desc="종합적인 접근성 평가 결과")

class ZoningSignature(dspy.Signature):
    """법규 검증을 위한 Signature"""
    input = dspy.InputField(desc="법규를 검증할 문서")
    output = dspy.OutputField(desc="법규 검증 결과와 위험요소 분석")

class CapacitySignature(dspy.Signature):
    """수용력 추정을 위한 Signature"""
    input = dspy.InputField(desc="수용력을 추정할 문서")
    output = dspy.OutputField(desc="개발 수용력 분석과 최적 규모 제안")

class FeasibilitySignature(dspy.Signature):
    """사업성 평가를 위한 Signature"""
    input = dspy.InputField(desc="사업성을 평가할 문서")
    output = dspy.OutputField(desc="종합적인 사업성 평가 결과")

class 도시재개발사회경제적영향분석Signature(dspy.Signature):
    """도시 재개발 사회경제적 영향 분석을 위한 Signature"""
    input = dspy.InputField(desc="도시 재개발 사회경제적 영향 분석을 위한 입력 데이터")
    output = dspy.OutputField(desc="도시 재개발 사회경제적 영향 분석에 따른 분석 결과")

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
                    model="claude-sonnet-4-20250514",  # 사용 가능한 Claude 모델
                    provider="anthropic",
                    api_key=anthropic_api_key,
                    max_tokens=8000
                )
                dspy.configure(lm=lm, track_usage=True)
                print("Claude Sonnet 4.0 모델이 성공적으로 설정되었습니다.")
            except Exception as e:
                print(f"Claude 모델 설정 실패: {e}")
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
                        print("OpenAI GPT-4o-mini 모델이 성공적으로 설정되었습니다.")
                    else:
                        raise ValueError("Claude와 OpenAI API 키가 모두 없습니다.")
                except Exception as e2:
                    print(f"대안 모델 설정도 실패: {e2}")
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

## 프로젝트 개요
- 프로젝트명
- 주요 특징
- 건축적 의미

## 기본 정보 추출 (CoT)
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
    
    def analyze_custom_block(self, prompt, pdf_text, block_id=None):
        """사용자 정의 블록 분석 - 블록별 고유 프롬프트와 Signature 사용"""
        try:
            # 블록 ID에 따라 적절한 Signature 선택
            signature_map = {
                'basic_info': BasicInfoSignature,
                'requirements': RequirementsSignature,
                'design_suggestions': DesignSignature,
                'investment_metrics_calculator': InvestmentSignature,
                'accessibility_analysis': AccessibilitySignature,
                'zoning_verification': ZoningSignature,
                'capacity_estimation': CapacitySignature,
                'feasibility_analysis': FeasibilitySignature
                '도시_재개발_사회경제적_영향_분석': 도시재개발사회경제적영향분석Signature,
}
            
            # 기본 Signature 사용 (블록 ID가 없거나 매핑되지 않은 경우)
            signature_class = signature_map.get(block_id, SimpleAnalysisSignature)
            
            # 디버깅 정보 출력
            print(f"🔍 DSPy 분석 디버깅:")
            print(f"   블록 ID: {block_id}")
            print(f"   사용할 Signature: {signature_class.__name__}")
            print(f"   프롬프트 길이: {len(prompt)}자")
            print(f"   프롬프트 미리보기: {prompt[:200]}...")
            
            # 프롬프트가 이미 완전히 구성되어 있으므로 그대로 사용
            # DSPy Predict 사용 (블록별 특화 signature 포함)
            result = dspy.Predict(signature_class)(input=prompt)
            
            return {
                "success": True,
                "analysis": result.output,
                "model": "claude-sonnet-4-20250514 (DSPy)",
                "method": f"DSPy + {signature_class.__name__}",
                "block_id": block_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": "claude-sonnet-4-20250514 (DSPy)",
                "method": f"DSPy + {signature_class.__name__ if 'signature_class' in locals() else 'Unknown'}",
                "block_id": block_id
            }
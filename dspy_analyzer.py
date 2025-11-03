import dspy
import os
from datetime import datetime
from dotenv import load_dotenv

# 환경변수 로드 (안전하게 처리)
try:
    load_dotenv()
except UnicodeDecodeError:
    # .env 파일에 인코딩 문제가 있는 경우 무시
    pass

# 개선된 Signature 정의
class SimpleAnalysisSignature(dspy.Signature):
    """Chain of Thought 기반 종합 분석을 위한 Signature"""
    input = dspy.InputField(desc="프로젝트 문서 및 분석 요구사항")
    output = dspy.OutputField(desc="단계별 추론 과정을 포함한 체계적인 분석 결과")

class BasicInfoSignature(dspy.Signature):
    """기본 정보 추출을 위한 Signature"""
    input = dspy.InputField(desc="프로젝트 기본 정보를 추출할 문서")
    output = dspy.OutputField(desc="프로젝트명, 위치, 규모, 목표, 주요 특징을 포함한 체계적인 기본 정보 표")

class RequirementsSignature(dspy.Signature):
    """요구사항 분석을 위한 Signature"""
    input = dspy.InputField(desc="건축 요구사항을 분석할 문서")
    output = dspy.OutputField(desc="요구사항 매트릭스, 우선순위 도표, 설계 방향을 포함한 종합 분석")

class DesignSignature(dspy.Signature):
    """설계 제안을 위한 Signature"""
    input = dspy.InputField(desc="설계 방향을 제안할 문서")
    output = dspy.OutputField(desc="설계 원칙, 공간 구성안, 실행 단계를 포함한 구체적인 설계 제안")

class InvestmentSignature(dspy.Signature):
    """투자 지표 계산을 위한 Signature"""
    input = dspy.InputField(desc="투자 지표를 계산할 문서")
    output = dspy.OutputField(desc="비용 분석표, 수익성 지표, 투자 회수 기간을 포함한 재무 분석")

class AccessibilitySignature(dspy.Signature):
    """접근성 평가를 위한 Signature"""
    input = dspy.InputField(desc="접근성을 평가할 문서")
    output = dspy.OutputField(desc="접근성 매트릭스, 개선 방안, 점수 평가를 포함한 종합 평가")

class ZoningSignature(dspy.Signature):
    """법규 검증을 위한 Signature"""
    input = dspy.InputField(desc="법규를 검증할 문서")
    output = dspy.OutputField(desc="법규 준수 체크리스트, 위험요소 분석, 대응 방안을 포함한 검증 결과")

class CapacitySignature(dspy.Signature):
    """수용력 추정을 위한 Signature"""
    input = dspy.InputField(desc="수용력을 추정할 문서")
    output = dspy.OutputField(desc="물리적/법적/사회적/경제적 수용력 분석표와 최적 개발 규모 제안")

class FeasibilitySignature(dspy.Signature):
    """사업성 평가를 위한 Signature"""
    input = dspy.InputField(desc="사업성을 평가할 문서")
    output = dspy.OutputField(desc="시장성, 기술성, 경제성, 법규성 평가표와 종합 사업성 점수")

class 도시재개발사회경제적영향분석Signature(dspy.Signature):
    """도시 재개발 사회경제적 영향 분석을 위한 Signature"""
    input = dspy.InputField(desc="도시 재개발 사회경제적 영향 분석을 위한 입력 데이터")
    output = dspy.OutputField(desc="사회경제적 영향 매트릭스, 정량적 지표, 개선 방안을 포함한 종합 분석 결과")

class AnalysisQualityValidator(dspy.Signature):
    """분석 결과 품질 검증을 위한 Signature"""
    analysis_result = dspy.InputField(desc="검증할 분석 결과")
    validation_criteria = dspy.InputField(desc="품질 검증 기준")
    output = dspy.OutputField(desc="품질 점수, 개선 사항, 완성도 평가를 포함한 검증 결과")

class 건축요구사항분석CotSignature(dspy.Signature):
    """건축 요구사항 분석 (CoT)을 위한 Signature"""
    input = dspy.InputField(desc="건축 요구사항 분석 (CoT)을 위한 입력 데이터")
    output = dspy.OutputField(desc="Chain of Thought로 건축 관련 요구사항을 분석하고 정리합니다에 따른 분석 결과")

class 건축요구사항분석22Signature(dspy.Signature):
    """건축 요구사항 분석22을 위한 Signature"""
    input = dspy.InputField(desc="건축 요구사항 분석22을 위한 입력 데이터")
    output = dspy.OutputField(desc="Chain of Thought로 건축 관련 요구사항을 분석하고 정리합니다에 따른 분석 결과")

class EnhancedArchAnalyzer:
    """dA_AI와 동일한 방식으로 DSPy를 사용하는 건축 분석기"""
    
    def __init__(self):
        """DSPy 설정 초기화 (dA_AI와 동일한 방식)"""
        self.setup_dspy()
    
    def _get_output_format_template(self):
        """출력 형식 템플릿을 반환하는 공통 함수"""
        return """
## 출력 형식 요구사항

**반드시 다음 형식으로 결과를 제시해주세요:**

### [소제목 1]
[소제목에 대한 상세한 해설 (3-5문장, 200-400자)]

| 항목 | 내용 | 비고 |
|------|------|------|
| 항목1 | 내용1 | 비고1 |
| 항목2 | 내용2 | 비고2 |

**[표 해설]**
위 표에 대한 상세한 해설을 4-8문장(300-600자)로 작성해주세요. 표의 내용을 분석하고 해석하며, 각 항목의 의미와 중요성을 설명해주세요.

### [소제목 2]
[소제목에 대한 상세한 해설 (3-5문장, 200-400자)]

| 항목 | 내용 | 비고 |
|------|------|------|
| 항목1 | 내용1 | 비고1 |
| 항목2 | 내용2 | 비고2 |

**[표 해설]**
위 표에 대한 상세한 해설을 4-8문장(300-600자)로 작성해주세요. 표의 내용을 분석하고 해석하며, 각 항목의 의미와 중요성을 설명해주세요.

### [소제목 3]
[소제목에 대한 상세한 해설 (3-5문장, 200-400자)]

| 항목 | 내용 | 비고 |
|------|------|------|
| 항목1 | 내용1 | 비고1 |
| 항목2 | 내용2 | 비고2 |

**[표 해설]**
위 표에 대한 상세한 해설을 4-8문장(300-600자)로 작성해주세요. 표의 내용을 분석하고 해석하며, 각 항목의 의미와 중요성을 설명해주세요.

### [소제목 4]
[소제목에 대한 상세한 해설 (3-5문장, 200-400자)]

| 항목 | 내용 | 비고 |
|------|------|------|
| 항목1 | 내용1 | 비고1 |
| 항목2 | 내용2 | 비고2 |

**[표 해설]**
위 표에 대한 상세한 해설을 4-8문장(300-600자)로 작성해주세요. 표의 내용을 분석하고 해석하며, 각 항목의 의미와 중요성을 설명해주세요.

**중요**: 각 소제목 아래에는 반드시 3-5문장의 상세한 해설을 작성하고, 각 표 아래에는 반드시 4-8문장의 표 해설을 작성해주세요.
"""
    
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
        """프로젝트 분석 - 일관된 구조, 블록별 내용 차별화"""
        prompt = f"""
다음 건축 프로젝트 정보를 바탕으로 체계적인 Chain of Thought 분석을 수행해주세요:

**프로젝트 정보:**
- 프로젝트명: {project_info.get('project_name', 'N/A')}
- 프로젝트 유형: {project_info.get('project_type', 'N/A')}
- 위치: {project_info.get('location', 'N/A')}
- 규모: {project_info.get('scale', 'N/A')}

**PDF 문서 내용:**
{pdf_text[:4000] if pdf_text else "PDF 문서가 없습니다."}

## Chain of Thought 분석 단계:

### 1단계: 정보 수집 및 분류
- 문서에서 명시적 정보 식별
- 암시적 정보 추론
- 정보 신뢰도 평가

### 2단계: 핵심 요소 추출
- 프로젝트 목표 및 비전
- 주요 제약조건 및 기회요소
- 이해관계자 및 영향 범위

### 3단계: 분석 및 종합
- 각 요소의 중요도 평가
- 요소 간 상호관계 분석
- 종합적 해석 및 인사이트 도출

## 📋 품질 기준 및 제약조건

### 필수 제약조건
- **AI 추론 표시**: 모든 AI 기반 추론은 반드시 '(AI 추론)' 표시 후 근거와 함께 제시
- **구체적 근거**: 모든 분석 결과는 구체적인 근거와 출처 페이지/원문 인용 필수
- **표 해설**: 각 섹션의 표 하단에 해설 추가 (최소 4문장, 최대 8문장, 300-600자)
- **소제목 해설**: 모든 소제목 아래에 상세한 해설 줄글 필수 (최소 3-5문장, 200-400자)
- **분량 요구**: 전체 문서 분량 2000자 이상 작성 (기존 1200자에서 확대)
- **표와 서술**: 표와 서술식 줄글의 적절한 조합 필수
- **상세 분석**: 각 항목별로 구체적인 수치, 기간, 규모, 비용 등을 상세히 제시
- **다각도 분석**: 물리적, 법적, 경제적, 사회적 측면을 모두 고려한 종합 분석
- **비교 분석**: 대안이 있는 경우 상세한 비교 분석표와 시나리오별 분석 필수

### 분석 가이드라인
- **구체성**: 키워드나 단순 나열이 아닌 구체적이고 서술적인 설명 제공
- **근거 제시**: 모든 결론에는 명확한 근거와 출처를 제시
- **표 활용**: 정보를 체계적으로 정리하기 위해 표 형식을 적극 활용
- **문장 형태**: 불릿 포인트보다는 완성된 문장으로 설명
- **실용성**: 추상적인 내용보다는 실제 실행 가능한 구체적 방안 제시
- **정량적 정보**: 가능한 한 구체적인 수치, 기간, 규모 등을 포함
- **맥락 제공**: 각 정보가 프로젝트 전체에서 어떤 의미인지 맥락 설명
- **심화 분석**: 표면적 정보를 넘어서 심층적이고 전문적인 분석 수행
- **예시 제시**: 구체적인 사례나 예시를 통한 설명 강화
- **단계별 분석**: 복잡한 내용은 단계별로 나누어 상세히 분석
- **시각화 고려**: 복잡한 데이터는 표나 차트 형태로 정리

## 📝 출력 형식 요구사항

**반드시 다음 형식으로 결과를 제시해주세요:**

### [소제목 1]
[소제목에 대한 상세한 해설 (3-5문장, 200-400자)]

| 항목 | 내용 | 비고 |
|------|------|------|
| 항목1 | 내용1 | 비고1 |
| 항목2 | 내용2 | 비고2 |

**[표 해설]**
위 표에 대한 상세한 해설을 4-8문장(300-600자)로 작성해주세요. 표의 내용을 분석하고 해석하며, 각 항목의 의미와 중요성을 설명해주세요.

### [소제목 2]
[소제목에 대한 상세한 해설 (3-5문장, 200-400자)]

| 항목 | 내용 | 비고 |
|------|------|------|
| 항목1 | 내용1 | 비고1 |
| 항목2 | 내용2 | 비고2 |

**[표 해설]**
위 표에 대한 상세한 해설을 4-8문장(300-600자)로 작성해주세요. 표의 내용을 분석하고 해석하며, 각 항목의 의미와 중요성을 설명해주세요.

### [소제목 3]
[소제목에 대한 상세한 해설 (3-5문장, 200-400자)]

| 항목 | 내용 | 비고 |
|------|------|------|
| 항목1 | 내용1 | 비고1 |
| 항목2 | 내용2 | 비고2 |

**[표 해설]**
위 표에 대한 상세한 해설을 4-8문장(300-600자)로 작성해주세요. 표의 내용을 분석하고 해석하며, 각 항목의 의미와 중요성을 설명해주세요.

### [소제목 4]
[소제목에 대한 상세한 해설 (3-5문장, 200-400자)]

| 항목 | 내용 | 비고 |
|------|------|------|
| 항목1 | 내용1 | 비고1 |
| 항목2 | 내용2 | 비고2 |

**[표 해설]**
위 표에 대한 상세한 해설을 4-8문장(300-600자)로 작성해주세요. 표의 내용을 분석하고 해석하며, 각 항목의 의미와 중요성을 설명해주세요.

**중요**: 각 소제목 아래에는 반드시 3-5문장의 상세한 해설을 작성하고, 각 표 아래에는 반드시 4-8문장의 표 해설을 작성해주세요.
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
            signature_map = {                'basic_info': BasicInfoSignature,
                'requirements': RequirementsSignature,
                'design_suggestions': DesignSignature,
                'accessibility_analysis': AccessibilitySignature,
                'zoning_verification': ZoningSignature,
                'capacity_estimation': CapacitySignature,
                'feasibility_analysis': FeasibilitySignature
}
            
            # 기본 Signature 사용 (블록 ID가 없거나 매핑되지 않은 경우)
            signature_class = signature_map.get(block_id, SimpleAnalysisSignature)
            
            # 디버깅 정보 출력
            print(f"🔍 DSPy 분석 디버깅:")
            print(f"   블록 ID: {block_id}")
            print(f"   사용할 Signature: {signature_class.__name__}")
            print(f"   프롬프트 길이: {len(prompt)}자")
            print(f"   PDF 텍스트 길이: {len(pdf_text) if pdf_text else 0}자")
            print(f"   프롬프트 미리보기: {prompt[:200]}...")
            
            # 프롬프트 템플릿의 플레이스홀더를 실제 값으로 치환 (단일 블록 분석용)
            formatted_prompt = prompt
            if "{pdf_text}" in prompt:
                formatted_prompt = prompt.replace("{pdf_text}", "PDF 문서 내용이 여기에 삽입됩니다.")
            
            # 출력 형식 요구사항 추가
            enhanced_prompt = f"""
{formatted_prompt}

{self._get_output_format_template()}
"""
            
            # DSPy Predict 사용 (블록별 특화 signature 포함)
            result = dspy.Predict(signature_class)(input=enhanced_prompt)
            
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
    
    def validate_analysis_quality(self, analysis_result, block_type="general"):
        """분석 결과 품질 검증 - 개선된 버전"""
        try:
            # 블록별 특화 검증 기준
            validation_criteria = {
                "basic_info": {
                    "name": "기본 정보 추출",
                    "criteria": [
                        "프로젝트명, 위치, 규모 등 핵심 정보가 모두 포함되었는가?",
                        "표 형태로 정보가 체계적으로 정리되었는가?",
                        "각 표 하단에 상세한 해설이 있는가?",
                        "소제목별로 서술형 설명이 있는가?",
                        "문서 출처와 근거가 명시되었는가?"
                    ],
                    "weights": [0.25, 0.25, 0.2, 0.15, 0.15]
                },
                "requirements": {
                    "name": "건축 요구사항 분석",
                    "criteria": [
                        "요구사항이 체계적으로 식별되고 분류되었는가?",
                        "우선순위가 명확하게 설정되었는가?",
                        "요구사항 매트릭스가 포함되었는가?",
                        "설계 방향이 구체적으로 제시되었는가?",
                        "표 해설과 서술형 설명이 충분한가?"
                    ],
                    "weights": [0.3, 0.2, 0.2, 0.2, 0.1]
                },
                "design_suggestions": {
                    "name": "설계 제안",
                    "criteria": [
                        "현황 분석이 정확하고 포괄적인가?",
                        "설계 컨셉이 명확하고 구체적인가?",
                        "공간 구성안이 실현 가능한가?",
                        "실행 계획이 단계별로 제시되었는가?",
                        "전체적인 일관성과 논리성이 있는가?"
                    ],
                    "weights": [0.2, 0.3, 0.25, 0.15, 0.1]
                },
                "accessibility_analysis": {
                    "name": "접근성 평가",
                    "criteria": [
                        "교통, 보행, 시설, 장애인 접근성이 모두 평가되었는가?",
                        "5점 척도로 객관적인 점수가 산출되었는가?",
                        "개선 방안이 구체적으로 제시되었는가?",
                        "점수 산출 근거가 명확한가?",
                        "실행 가능한 개선 로드맵이 있는가?"
                    ],
                    "weights": [0.25, 0.2, 0.25, 0.15, 0.15]
                },
                "zoning_verification": {
                    "name": "법규 검증",
                    "criteria": [
                        "용도지역, 건축법규, 특별법이 모두 검토되었는가?",
                        "법적 위험요소가 정확하게 식별되었는가?",
                        "위험도별 분류가 적절한가?",
                        "대응방안이 구체적으로 제시되었는가?",
                        "법령 조항과 근거가 명확한가?"
                    ],
                    "weights": [0.25, 0.25, 0.15, 0.2, 0.15]
                },
                "capacity_estimation": {
                    "name": "수용력 추정",
                    "criteria": [
                        "물리적, 법적, 사회적, 경제적 수용력이 모두 분석되었는가?",
                        "정량적 계산과 수치가 포함되었는가?",
                        "최적 개발 규모가 제시되었는가?",
                        "단계별 개발 방안이 구체적인가?",
                        "계산 과정과 근거가 명확한가?"
                    ],
                    "weights": [0.3, 0.25, 0.2, 0.15, 0.1]
                },
                "feasibility_analysis": {
                    "name": "사업성 평가",
                    "criteria": [
                        "시장성, 수익성, 위험성, 자금조달성이 모두 평가되었는가?",
                        "각 기준별 1-5점 평가가 객관적인가?",
                        "종합 점수 산출이 적절한가?",
                        "Go/No-Go 결정 근거가 명확한가?",
                        "투자 권고안이 실용적인가?"
                    ],
                    "weights": [0.3, 0.2, 0.2, 0.15, 0.15]
                }
            }
            
            # 기본 검증 기준 (일반적인 경우)
            general_criteria = {
                "name": "일반 분석",
                "criteria": [
                    "분석 완성도가 높은가?",
                    "구체적인 수치와 결론이 있는가?",
                    "체계적인 형식으로 구성되었는가?",
                    "근거와 출처가 명시되었는가?",
                    "실용적인 정보인가?"
                ],
                "weights": [0.2, 0.2, 0.2, 0.2, 0.2]
            }
            
            # 블록별 검증 기준 선택
            criteria_info = validation_criteria.get(block_type, general_criteria)
            
            validation_prompt = f"""
다음 {criteria_info['name']} 분석 결과의 품질을 검증해주세요:

**분석 결과:**
{analysis_result}

**검증 기준:**
{chr(10).join([f"{i+1}. {criterion}" for i, criterion in enumerate(criteria_info['criteria'])])}

다음 형식으로 검증 결과를 제시해주세요:

## 📊 품질 검증 결과

### 📋 항목별 점수 평가 (각 항목 1-5점)
{chr(10).join([f"- **항목 {i+1}**: [점수]/5 - [간단한 평가 근거]" for i in range(len(criteria_info['criteria']))])}

### 📈 종합 점수: [총점]/25점
### 🏆 품질 등급: [우수/양호/보통/미흡/부족]

### ✅ 우수한 부분
- [잘된 부분들을 구체적으로 나열]

### 🔧 개선이 필요한 부분
- [개선이 필요한 항목들을 구체적으로 나열]

### 📝 구체적인 개선 제안
- [각 개선 항목에 대한 구체적인 제안사항]
"""
            
            result = dspy.Predict(AnalysisQualityValidator)(
                analysis_result=validation_prompt,
                validation_criteria=str(criteria_info['criteria'])
            )
            
            return {
                "success": True,
                "validation": result.output,
                "block_type": block_type,
                "criteria_info": criteria_info,
                "model": "claude-sonnet-4-20250514 (DSPy)",
                "method": "DSPy + Enhanced AnalysisQualityValidator"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "block_type": block_type,
                "model": "claude-sonnet-4-20250514 (DSPy)",
                "method": "DSPy + AnalysisQualityValidator"
            }
    
    def enhanced_analyze_with_validation(self, project_info, pdf_text, block_type="general"):
        """검증이 포함된 향상된 분석"""
        try:
            # 1단계: 기본 분석 수행
            analysis_result = self.analyze_project(project_info, pdf_text)
            
            if not analysis_result["success"]:
                return analysis_result
            
            # 2단계: 분석 결과 품질 검증
            validation_result = self.validate_analysis_quality(
                analysis_result["analysis"], 
                block_type
            )
            
            # 3단계: 결과 통합
            return {
                "success": True,
                "analysis": analysis_result["analysis"],
                "validation": validation_result.get("validation", "검증 실패"),
                "quality_score": self._extract_quality_score(validation_result.get("validation", "")),
                "model": analysis_result["model"],
                "method": f"{analysis_result['method']} + Quality Validation",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": "claude-sonnet-4-20250514 (DSPy)",
                "method": "Enhanced Analysis with Validation"
            }
    
    def _extract_quality_score(self, validation_text):
        """검증 결과에서 품질 점수 추출"""
        import re
        try:
            # "종합 점수: [총점]/25점" 패턴 찾기
            score_pattern = r'종합 점수:\s*(\d+)/25'
            match = re.search(score_pattern, validation_text)
            if match:
                return int(match.group(1))
            return None
        except:
            return None
    
    def _extract_quality_grade(self, validation_text):
        """검증 결과에서 품질 등급 추출"""
        import re
        try:
            # "품질 등급: [등급]" 패턴 찾기
            grade_pattern = r'품질 등급:\s*([가-힣]+)'
            match = re.search(grade_pattern, validation_text)
            if match:
                return match.group(1)
            return "미평가"
        except:
            return "미평가"
    
    def analyze_blocks_with_cot(self, selected_blocks, project_info, pdf_text, block_infos, progress_callback=None):
        """블록 간 Chain of Thought 분석"""
        try:
            # 누적 컨텍스트 초기화
            cumulative_context = {
                "project_info": project_info,
                "pdf_text": pdf_text,
                "previous_results": {},
                "cot_history": [],
                "total_blocks": len(selected_blocks)
            }
            
            analysis_results = {}
            
            print(f"🔗 블록 간 Chain of Thought 분석 시작: {len(selected_blocks)}개 블록")
            if progress_callback:
                progress_callback(f"🔗 블록 간 Chain of Thought 분석 시작: {len(selected_blocks)}개 블록")
            
            for i, block_id in enumerate(selected_blocks):
                block_name = block_infos.get(block_id, {}).get('name', block_id)
                print(f"📊 {i+1}/{len(selected_blocks)} 블록 분석 중: {block_id}")
                if progress_callback:
                    progress_callback(f"📊 {i+1}/{len(selected_blocks)} 블록 분석 중: {block_name}")
                
                # 현재 블록 정보 찾기
                block_info = block_infos.get(block_id)
                if not block_info:
                    print(f"❌ 블록 정보를 찾을 수 없습니다: {block_id}")
                    if progress_callback:
                        progress_callback(f"❌ 블록 정보를 찾을 수 없습니다: {block_id}")
                    continue
                
                # 현재 블록을 위한 컨텍스트 구성
                context_for_current_block = self._build_cot_context(
                    cumulative_context, block_info, i + 1
                )
                
                # 현재 블록 분석 (이전 결과들을 참고)
                result = self._analyze_block_with_cot_context(
                    context_for_current_block, block_info, block_id
                )
                
                if result['success']:
                    # 품질 검증 수행
                    validation_result = self.validate_analysis_quality(result['analysis'], block_id)
                    
                    analysis_results[block_id] = result['analysis']
                    
                    # 다음 블록을 위해 결과 누적
                    cumulative_context["previous_results"][block_id] = result['analysis']
                    key_insights = self._extract_key_insights(result['analysis'])
                    cumulative_context["cot_history"].append({
                        "block_id": block_id,
                        "block_name": block_info.get('name', 'Unknown'),
                        "step": i + 1,
                        "key_insights": key_insights,
                        "validation": validation_result
                    })
                    
                    # 품질 점수 추출
                    quality_score = self._extract_quality_score(validation_result.get('validation', ''))
                    quality_grade = self._extract_quality_grade(validation_result.get('validation', ''))
                    
                    print(f"✅ {block_id} 블록 완료 - 핵심 인사이트: {len(key_insights)}개, 품질: {quality_grade} ({quality_score}/25)")
                    if progress_callback:
                        progress_callback(f"✅ {block_name} 블록 완료 - 품질: {quality_grade} ({quality_score}/25)")
                else:
                    print(f"❌ {block_id} 블록 실패: {result.get('error', '알 수 없는 오류')}")
                    if progress_callback:
                        progress_callback(f"❌ {block_name} 블록 실패: {result.get('error', '알 수 없는 오류')}")
            
            print("🎉 모든 블록 분석 완료!")
            if progress_callback:
                progress_callback("🎉 모든 블록 분석 완료!")
            
            return {
                "success": True,
                "analysis_results": analysis_results,
                "cot_history": cumulative_context["cot_history"],
                "model": "claude-sonnet-4-20250514 (DSPy + Block CoT)",
                "method": "Block Chain of Thought Analysis"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": "claude-sonnet-4-20250514 (DSPy)",
                "method": "Block Chain of Thought Analysis"
            }
    
    def _build_cot_context(self, cumulative_context, block_info, current_step):
        """현재 블록을 위한 CoT 컨텍스트 구성"""
        
        # 이전 블록들의 핵심 인사이트 요약
        previous_insights_summary = ""
        if cumulative_context["previous_results"]:
            previous_insights_summary = "\n### 🔗 이전 블록들의 핵심 인사이트:\n"
            
            for i, history_item in enumerate(cumulative_context["cot_history"]):
                previous_insights_summary += f"""
**{i+1}단계 - {history_item['block_name']}:**
{history_item['key_insights'][:300]}...

"""
        
        # 공간 데이터 컨텍스트 추가
        spatial_context = ""
        project_info = cumulative_context.get('project_info', {})
        
        if isinstance(project_info, dict) and project_info.get('has_geo_data'):
            spatial_data_text = project_info.get('spatial_data_context', '')
            location_info = project_info.get('location', 'N/A')
            
            spatial_context = f"""

### 🗺️ 실제 공간 데이터 (Shapefile)

{spatial_data_text}

**중요 지시사항**: 
위 실제 공간 데이터를 근거로 분석을 수행하세요. 프로젝트 위치({location_info})와 실제 행정구역, 토지소유, 공시지가 정보를 교차 검증하세요.
입지 선정, 법규 검증, 접근성 평가 등 모든 분석은 위 Shapefile 데이터를 참고하여 실제 존재하는 필지/구역을 기반으로 하세요.
"""
        
        # 프로젝트 정보를 텍스트로 포맷팅
        if isinstance(project_info, dict):
            project_info_text = f"""
- 프로젝트명: {project_info.get('project_name', 'N/A')}
- 위치: {project_info.get('location', 'N/A')}
- 프로젝트 목표: {project_info.get('project_goals', 'N/A')[:200]}
- 추가 정보: {project_info.get('additional_info', 'N/A')[:200]}
"""
        else:
            project_info_text = str(project_info)
        
        # 현재 블록을 위한 특별한 컨텍스트 구성
        cot_context = f"""
## 🔗 블록 간 Chain of Thought 분석 컨텍스트

### 📊 분석 진행 상황
- 현재 단계: {current_step}/{cumulative_context['total_blocks']}
- 완료된 블록: {len(cumulative_context['previous_results'])}개
- 남은 블록: {cumulative_context['total_blocks'] - current_step + 1}개

{previous_insights_summary}

### 🎯 현재 블록 정보
- 블록명: {block_info.get('name', 'Unknown')}
- 블록 설명: {block_info.get('description', 'N/A')}

### 📄 원본 프로젝트 정보
{project_info_text}{spatial_context}

### 📄 원본 문서 내용
{cumulative_context['pdf_text'][:3000] if cumulative_context['pdf_text'] else 'PDF 문서가 없습니다.'}

## 🔗 블록 간 연결성 지시사항

**중요**: 이전 블록들의 분석 결과를 반드시 참고하여 현재 블록을 분석하세요:

1. **이전 결과 활용**: 위의 이전 블록 인사이트들을 현재 분석의 근거로 활용
2. **연관성 명시**: 이전 결과와 현재 분석 결과 간의 연결점을 명확히 제시
3. **누적 인사이트**: 이전 블록들의 핵심 발견사항을 현재 분석에 반영
4. **일관성 유지**: 전체 분석 방향성의 일관성을 유지
5. **상호 보완**: 이전 블록 결과를 보완하고 발전시키는 방향으로 분석

### 📋 현재 블록 분석 프롬프트
"""
        
        return cot_context
    
    def _format_prompt_template(self, prompt_template, block_info, cot_context):
        """프롬프트 템플릿의 플레이스홀더를 실제 값으로 치환"""
        try:
            # narrowing 정보에서 필요한 값들 추출
            narrowing = block_info.get('narrowing', {})
            
            # steps를 포맷팅
            steps = block_info.get('steps', [])
            steps_formatted = "\n".join([f"{i+1}. **{step}**" for i, step in enumerate(steps)])
            
            # narrowing의 각 항목을 포맷팅
            narrowing_items = []
            for key, value in narrowing.items():
                if isinstance(value, list):
                    value_str = ", ".join(value)
                else:
                    value_str = str(value)
                narrowing_items.append(f"- **{key.replace('_', ' ').title()}:** {value_str}")
            
            # 프롬프트 템플릿 치환
            formatted_prompt = prompt_template.format(
                role=block_info.get('role', ''),
                instructions=block_info.get('instructions', ''),
                steps_formatted=steps_formatted,
                end_goal=block_info.get('end_goal', ''),
                narrowing_output_format=narrowing.get('output_format', ''),
                narrowing_classification_criteria=narrowing.get('classification_criteria', ''),
                narrowing_evaluation_scale=narrowing.get('evaluation_scale', ''),
                narrowing_constraints=narrowing.get('constraints', ''),
                narrowing_quality_standards=narrowing.get('quality_standards', ''),
                narrowing_required_items=narrowing.get('required_items', ''),
                narrowing_required_sections=narrowing.get('required_sections', ''),
                narrowing_design_focus=narrowing.get('design_focus', ''),
                narrowing_evaluation_criteria=narrowing.get('evaluation_criteria', ''),
                narrowing_scoring_system=narrowing.get('scoring_system', ''),
                narrowing_verification_scope=narrowing.get('verification_scope', ''),
                narrowing_risk_assessment=narrowing.get('risk_assessment', ''),
                narrowing_analysis_areas=narrowing.get('analysis_areas', ''),
                narrowing_calculation_method=narrowing.get('calculation_method', ''),
                pdf_text="{pdf_text}"  # 나중에 치환될 플레이스홀더
            )
            
            return formatted_prompt
            
        except Exception as e:
            print(f"❌ 프롬프트 템플릿 포맷팅 오류: {e}")
            return prompt_template
    
    def _analyze_block_with_cot_context(self, cot_context, block_info, block_id):
        """CoT 컨텍스트를 포함한 블록 분석"""
        try:
            # 블록의 프롬프트 템플릿 가져오기
            prompt_template = block_info.get('prompt', '')
            
            # 프롬프트 템플릿의 플레이스홀더를 실제 값으로 치환
            formatted_prompt = self._format_prompt_template(prompt_template, block_info, cot_context)
            
            # CoT 컨텍스트와 블록 프롬프트 결합
            enhanced_prompt = f"""
{cot_context}

{formatted_prompt}

{self._get_output_format_template()}
"""
            
            # 블록 ID에 따라 적절한 Signature 선택
            signature_map = {                'basic_info': BasicInfoSignature,
                'requirements': RequirementsSignature,
                'design_suggestions': DesignSignature,
                'accessibility_analysis': AccessibilitySignature,
                'zoning_verification': ZoningSignature,
                'capacity_estimation': CapacitySignature,
                'feasibility_analysis': FeasibilitySignature
}
            
            signature_class = signature_map.get(block_id, SimpleAnalysisSignature)
            
            # DSPy Predict 사용
            result = dspy.Predict(signature_class)(input=enhanced_prompt)
            
            return {
                "success": True,
                "analysis": result.output,
                "model": "claude-sonnet-4-20250514 (DSPy + CoT)",
                "method": f"DSPy + {signature_class.__name__} + Block CoT",
                "block_id": block_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": "claude-sonnet-4-20250514 (DSPy)",
                "method": f"DSPy + Block CoT",
                "block_id": block_id
            }
    
    def _extract_key_insights(self, analysis_text, max_length=200):
        """분석 결과에서 핵심 인사이트 추출"""
        try:
            # 간단한 핵심 인사이트 추출 로직
            # "핵심", "주요", "중요", "결론" 등의 키워드가 포함된 문장들 추출
            import re
            
            # 핵심 키워드가 포함된 문장들 찾기
            key_patterns = [
                r'핵심[^.]*[.]',
                r'주요[^.]*[.]',
                r'중요[^.]*[.]',
                r'결론[^.]*[.]',
                r'발견[^.]*[.]',
                r'인사이트[^.]*[.]'
            ]
            
            insights = []
            for pattern in key_patterns:
                matches = re.findall(pattern, analysis_text)
                insights.extend(matches[:2])  # 패턴당 최대 2개
            
            # 중복 제거 및 길이 제한
            unique_insights = []
            for insight in insights:
                if insight not in unique_insights and len(insight) <= max_length:
                    unique_insights.append(insight)
            
            # 최대 3개까지만 반환
            return unique_insights[:3]
            
        except:
            # 오류 시 간단히 앞부분 반환
            return [analysis_text[:max_length] + "..."] if analysis_text else []
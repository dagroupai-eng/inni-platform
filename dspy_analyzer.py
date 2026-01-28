import os
# DSPy 캐시 비활성화 (import 전에 설정해야 함)
os.environ['DSP_CACHEBOOL'] = 'false'
os.environ['DSPY_CACHEBOOL'] = 'false'

import dspy
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Type, Callable, Tuple
from dotenv import load_dotenv
from web_search_helper import get_web_search_context, WebSearchHelper
# get_web_search_citations는 선택적 import (함수가 없을 수 있음)
try:
    from web_search_helper import get_web_search_citations
    WEB_SEARCH_CITATIONS_AVAILABLE = True
except ImportError:
    WEB_SEARCH_CITATIONS_AVAILABLE = False
    get_web_search_citations = None
from prompt_processor import process_prompt, UNIFIED_PROMPT_TEMPLATE

# Pydantic 지원 (선택적)
try:
    from pydantic import BaseModel
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = None

# RAG 기능 (선택적 사용)
try:
    from rag_helper import (
        build_rag_system_for_documents,
        query_rag_system,
        retrieve_relevant_contexts
    )
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("⚠️ RAG 기능을 사용하려면 embedding_helper.py와 rag_helper.py가 필요합니다.")

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

# 환경변수 로드 함수
def _load_streamlit_secrets_into_env():
    """
    Streamlit secrets.toml 값을 일반 실행 환경 변수로 주입합니다.
    Streamlit이 아닌 CLI/테스트 환경에서도 동일한 API 키를 재사용하기 위함입니다.
    """
    secrets_path = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return

    try:
        with secrets_path.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return

    # Streamlit 기본 구조는 [secrets] 섹션을 사용하지만, 루트 키일 수도 있음
    secrets_block = data.get("secrets", data)
    if not isinstance(secrets_block, dict):
        return

    for key, value in secrets_block.items():
        if isinstance(value, str) and not os.environ.get(key):
            os.environ[key] = value

# 환경변수 및 secrets 로드 (안전하게 처리)
_load_streamlit_secrets_into_env()
try:
    load_dotenv()
except UnicodeDecodeError:
    # .env 파일에 인코딩 문제가 있는 경우 무시
    pass

# API 제공자별 설정 정보 (Gemini 2.5 Pro 고성능 모델)
PROVIDER_CONFIG = {
    'gemini': {
        'api_key_env': 'GEMINI_API_KEY',  # Google AI Studio API 키
        'model': 'gemini-2.5-pro',  # LiteLLM 형식: gemini/gemini-2.5-pro
        'provider': 'gemini',  # Google AI Studio (API Key)
        'display_name': 'Gemini 2.5 Pro'
    },
    'gemini_3pro': {
        'api_key_env': 'GEMINI_API_KEY',  # Google AI Studio API 키
        'model': 'gemini-3-pro-preview',  # 가장 지능적인 모델
        'provider': 'gemini',  # Google AI Studio (API Key)
        'display_name': 'Gemini 3 Pro'
    },
    'gemini_25flash': {
        'api_key_env': 'GEMINI_API_KEY',  # Google AI Studio API 키
        'model': 'gemini-2.5-flash',  # 빠르고 가격 대비 성능 우수
        'provider': 'gemini',  # Google AI Studio (API Key)
        'display_name': 'Gemini 2.5 Flash'
    },
    'gemini_3flash': {
        'api_key_env': 'GEMINI_API_KEY',  # Google AI Studio API 키
        'model': 'gemini-3-flash-preview',  # Gemini 3.0 Flash
        'provider': 'gemini',  # Google AI Studio (API Key)
        'display_name': 'Gemini 3.0 Flash'
    }
}

# 피드백 유형 분류
FEEDBACK_TYPES = {
    'perspective_shift': {
        'name': '관점 부족',
        'description': '다른 관점에서 재분석 (환경, 경제, 사회, 기술 등)',
        'hint': '예: "환경적 측면이 부족합니다", "경제성 분석을 추가해주세요"',
        'keywords': ['관점', '측면', '시각', '고려', '부족', '누락', '추가']
    },
    'constraint_addition': {
        'name': '제약조건 추가',
        'description': '예산, 규모, 법규, 일정 등 제약사항 반영',
        'hint': '예: "예산 30억 이하로", "6개월 내 완공 가능하도록"',
        'keywords': ['예산', '비용', '규모', '법규', '규정', '일정', '기한', '제한', '이하', '이상', '범위']
    },
    'scope_expansion': {
        'name': '범위 확장',
        'description': '추가 분석 영역 요청',
        'hint': '예: "주변 교통 영향도 분석해주세요", "인근 시설과의 연계방안"',
        'keywords': ['추가', '확장', '포함', '함께', '연계', '주변', '더']
    },
    'correction': {
        'name': '오류 수정',
        'description': '잘못된 내용 수정 또는 사실관계 정정',
        'hint': '예: "면적이 잘못되었습니다", "법규 해석이 틀렸습니다"',
        'keywords': ['잘못', '오류', '틀림', '수정', '정정', '아닙니다', '아니라']
    },
    'direction_change': {
        'name': '방향 전환',
        'description': '분석 방향 자체를 변경',
        'hint': '예: "이 방향은 어렵습니다. 대안을 분석해주세요"',
        'keywords': ['안됩니다', '어렵', '불가능', '대안', '다른', '방향', '전환']
    }
}


def parse_feedback_intent(feedback_text: str, feedback_type: Optional[str] = None) -> Dict[str, Any]:
    """
    피드백 텍스트에서 의도를 분석합니다.

    Args:
        feedback_text: 사용자가 입력한 피드백 텍스트
        feedback_type: 선택된 피드백 유형 (None이면 자동 감지)

    Returns:
        분석된 피드백 의도 정보:
        - type: 피드백 유형
        - missing_perspectives: 부족한 관점 목록
        - constraints: 추출된 제약조건
        - rejection_reason: 거부 이유 (있는 경우)
        - additional_scope: 추가 분석 범위
        - correction_points: 수정 필요 사항
    """
    result = {
        'type': feedback_type,
        'original_text': feedback_text,
        'missing_perspectives': [],
        'constraints': [],
        'rejection_reason': None,
        'additional_scope': [],
        'correction_points': []
    }

    if not feedback_text:
        return result

    feedback_lower = feedback_text.lower()

    # 자동 유형 감지 (feedback_type이 없는 경우)
    if not feedback_type:
        max_score = 0
        detected_type = None
        for ftype, info in FEEDBACK_TYPES.items():
            score = sum(1 for kw in info['keywords'] if kw in feedback_lower)
            if score > max_score:
                max_score = score
                detected_type = ftype
        result['type'] = detected_type or 'general'

    # 관점 키워드 추출
    perspective_keywords = {
        '환경': '환경적 영향 분석',
        '경제': '경제성 분석',
        '사회': '사회적 영향 분석',
        '기술': '기술적 타당성',
        '법규': '법규 검토',
        '안전': '안전성 분석',
        '접근성': '접근성 분석',
        '지속가능': '지속가능성 분석',
        '교통': '교통 영향 분석',
        '문화': '문화적 가치 분석'
    }
    for kw, perspective in perspective_keywords.items():
        if kw in feedback_text:
            result['missing_perspectives'].append(perspective)

    # 제약조건 추출 (숫자 + 단위 패턴)
    import re
    constraint_patterns = [
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(억|만원|원|평|㎡|m²|층|개월|년|일)',
        r'(예산|비용|면적|규모|높이|기간)\s*[:：]?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(억|만원|원|평|㎡|m²|층|개월|년|일)?',
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(억|만원|원)\s*(이하|이상|미만|초과|내외)'
    ]
    for pattern in constraint_patterns:
        matches = re.findall(pattern, feedback_text)
        for match in matches:
            constraint_str = ' '.join(str(m) for m in match if m)
            if constraint_str and constraint_str not in result['constraints']:
                result['constraints'].append(constraint_str)

    # 거부/방향전환 이유 추출
    rejection_keywords = ['안됩니다', '어렵습니다', '불가능', '못합니다', '안 됩니다']
    for kw in rejection_keywords:
        if kw in feedback_text:
            # 해당 문장 추출
            sentences = feedback_text.split('.')
            for sent in sentences:
                if kw in sent:
                    result['rejection_reason'] = sent.strip()
                    break
            break

    # 추가 범위 추출
    scope_keywords = ['추가로', '함께', '포함해서', '연계하여', '더불어']
    for kw in scope_keywords:
        if kw in feedback_text:
            idx = feedback_text.find(kw)
            # 키워드 이후 문장 추출
            remainder = feedback_text[idx:].split('.')[0]
            if remainder:
                result['additional_scope'].append(remainder.strip())

    return result


def build_contextual_feedback_prompt(
    feedback_intent: Dict[str, Any],
    previous_result: str,
    block_info: Dict[str, Any]
) -> str:
    """
    피드백 의도에 따른 맞춤 프롬프트를 생성합니다.

    Args:
        feedback_intent: parse_feedback_intent()의 결과
        previous_result: 이전 분석 결과
        block_info: 현재 블록 정보

    Returns:
        컨텍스트 인식 피드백 프롬프트
    """
    feedback_type = feedback_intent.get('type', 'general')
    original_feedback = feedback_intent.get('original_text', '')

    prompt_parts = []

    # 기본 피드백 섹션
    prompt_parts.append("### 🔁 사용자 피드백 분석\n")

    # 피드백 유형에 따른 지시사항
    if feedback_type == 'perspective_shift':
        perspectives = feedback_intent.get('missing_perspectives', [])
        prompt_parts.append("**피드백 유형**: 관점 부족 - 다른 관점에서 재분석 필요\n")
        if perspectives:
            prompt_parts.append(f"**추가 필요 관점**: {', '.join(perspectives)}\n")
        prompt_parts.append("""
**재분석 지시사항**:
1. 이전 분석 결과를 기반으로 하되, 위에서 지적된 관점을 중심으로 재분석하세요.
2. 기존 분석에서 누락된 측면을 보완하여 종합적인 분석을 제공하세요.
3. 새로운 관점에서 발견되는 이슈와 기회를 명확히 제시하세요.
""")

    elif feedback_type == 'constraint_addition':
        constraints = feedback_intent.get('constraints', [])
        prompt_parts.append("**피드백 유형**: 제약조건 추가 - 새로운 제약사항 반영 필요\n")
        if constraints:
            prompt_parts.append(f"**적용할 제약조건**: {', '.join(constraints)}\n")
        prompt_parts.append("""
**재분석 지시사항**:
1. 위의 제약조건을 반드시 반영하여 분석을 수정하세요.
2. 제약조건으로 인해 변경되는 부분을 명확히 표시하세요.
3. 제약조건 충족 여부를 검증하고, 충족하지 못하는 경우 대안을 제시하세요.
""")

    elif feedback_type == 'scope_expansion':
        additional_scope = feedback_intent.get('additional_scope', [])
        prompt_parts.append("**피드백 유형**: 범위 확장 - 추가 분석 영역 요청\n")
        if additional_scope:
            prompt_parts.append(f"**추가 분석 범위**: {'; '.join(additional_scope)}\n")
        prompt_parts.append("""
**재분석 지시사항**:
1. 기존 분석 결과를 유지하면서 요청된 추가 범위를 분석에 포함하세요.
2. 추가된 범위와 기존 분석 간의 연관성을 명확히 설명하세요.
3. 확장된 범위에서 새롭게 발견되는 시사점을 제시하세요.
""")

    elif feedback_type == 'correction':
        correction_points = feedback_intent.get('correction_points', [])
        prompt_parts.append("**피드백 유형**: 오류 수정 - 잘못된 내용 정정 필요\n")
        prompt_parts.append("""
**재분석 지시사항**:
1. 사용자가 지적한 오류 사항을 주의 깊게 검토하세요.
2. 잘못된 부분을 정확한 정보로 수정하세요.
3. 수정된 내용이 전체 분석에 미치는 영향을 반영하세요.
4. 수정 사항을 명확히 표시하여 변경점을 알 수 있게 하세요.
""")

    elif feedback_type == 'direction_change':
        rejection_reason = feedback_intent.get('rejection_reason', '')
        prompt_parts.append("**피드백 유형**: 방향 전환 - 분석 방향 변경 요청\n")
        if rejection_reason:
            prompt_parts.append(f"**사용자가 제시한 이유**: {rejection_reason}\n")
        prompt_parts.append("""
**재분석 지시사항**:
1. 사용자가 현재 방향이 어려운 이유를 이해하고 수용하세요.
2. 완전히 새로운 대안적 접근 방식을 제시하세요.
3. 대안이 사용자가 언급한 문제를 어떻게 해결하는지 설명하세요.
4. 여러 대안이 있다면 각각의 장단점을 비교하세요.
""")

    else:  # general
        prompt_parts.append("**피드백 유형**: 일반 피드백\n")
        prompt_parts.append("""
**재분석 지시사항**:
1. 사용자 피드백의 핵심 요청사항을 파악하세요.
2. 요청에 따라 분석을 보완하거나 수정하세요.
3. 변경된 내용을 명확히 설명하세요.
""")

    # 원본 피드백 포함
    prompt_parts.append(f"\n**원본 피드백**: {original_feedback}\n")

    # 이전 결과 요약 (너무 길면 자르기)
    if previous_result:
        summary_length = min(len(previous_result), 1500)
        prompt_parts.append(f"\n**이전 분석 결과 요약**:\n{previous_result[:summary_length]}")
        if len(previous_result) > summary_length:
            prompt_parts.append("\n[이전 결과 일부 생략...]")

    return '\n'.join(prompt_parts)


# API 키 가져오기 함수
def get_api_key(provider: str) -> Optional[str]:
    """
    선택된 제공자에 맞는 API 키를 가져옵니다.
    우선순위: 1) 세션 상태 -> 2) DB 저장 키 -> 3) Streamlit secrets -> 4) 환경변수

    Args:
        provider: 제공자 이름 ('anthropic', 'openai', 'gemini', 'deepseek')

    Returns:
        API 키 문자열 또는 None (Vertex AI는 None 반환)
    """
    if provider not in PROVIDER_CONFIG:
        return None

    config = PROVIDER_CONFIG[provider]
    api_key_env = config.get('api_key_env')

    # Vertex AI는 API 키 불필요 (ADC 사용)
    if not api_key_env:
        return None

    try:
        import streamlit as st
        # 1. 먼저 세션 상태에서 확인 (사용자가 웹에서 입력한 키)
        session_key = f'user_api_key_{api_key_env}'
        if session_key in st.session_state and st.session_state[session_key]:
            return st.session_state[session_key]

        # 2. DB에 저장된 사용자별 API 키 확인
        try:
            from security.api_key_manager import get_api_key_for_current_user
            db_api_key = get_api_key_for_current_user(api_key_env)
            if db_api_key:
                return db_api_key
        except ImportError:
            pass

        # 3. Streamlit secrets에서 확인 (secrets 파일이 없을 수 있으므로 안전하게 처리)
        # 4. 환경변수에서 확인
        try:
            api_key = st.secrets.get(api_key_env) or os.environ.get(api_key_env)
        except (FileNotFoundError, AttributeError, KeyError):
            api_key = os.environ.get(api_key_env)
    except Exception:
        # Streamlit이 없는 환경 (예: 스크립트 실행)
        api_key = os.environ.get(api_key_env)

    return api_key

# 현재 제공자 가져오기 함수
def get_current_provider() -> str:
    """
    현재 선택된 제공자를 반환합니다. 기본값은 'gemini_25flash'입니다.
    
    Returns:
        제공자 이름
    """
    env_override = os.environ.get('LLM_PROVIDER')
    
    # 환경변수 우선 (CLI/테스트 실행 등을 위해)
    if env_override and env_override in PROVIDER_CONFIG:
        return env_override
    
    try:
        import streamlit as st
        provider = st.session_state.get('llm_provider', env_override or 'gemini_25flash')
        if provider not in PROVIDER_CONFIG:
            provider = 'gemini_25flash'
        return provider
    except Exception:
        # Streamlit이 없는 환경
        if env_override and env_override in PROVIDER_CONFIG:
            return env_override
        return 'gemini'

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

class AnalysisQualityValidator(dspy.Signature):
    """분석 결과 품질 검증을 위한 Signature"""
    analysis_result = dspy.InputField(desc="검증할 분석 결과")
    validation_criteria = dspy.InputField(desc="품질 검증 기준")
    output = dspy.OutputField(desc="품질 점수, 개선 사항, 완성도 평가를 포함한 검증 결과")

class 건축요구사항분석CotSignature(dspy.Signature):
    """건축 요구사항 분석 (CoT)을 위한 Signature"""
    input = dspy.InputField(desc="건축 요구사항 분석 (CoT)을 위한 입력 데이터")
    output = dspy.OutputField(desc="Chain of Thought로 건축 관련 요구사항을 분석하고 정리한 결과")

class 건축요구사항분석22Signature(dspy.Signature):
    """건축 요구사항 분석22을 위한 Signature"""
    input = dspy.InputField(desc="건축 요구사항 분석22을 위한 입력 데이터")
    output = dspy.OutputField(desc="Chain of Thought로 건축 관련 요구사항을 분석하고 정리한 결과")

class EnhancedArchAnalyzer:
    """dA_AI와 동일한 방식으로 DSPy를 사용하는 건축 분석기"""
    
    _lm_initialized = False
    _last_provider = None
    
    def __init__(self, use_gemini_native_pdf: bool = False):
        """
        DSPy 설정 초기화 (dA_AI와 동일한 방식)
        
        Args:
            use_gemini_native_pdf: PDF 처리를 Gemini 네이티브 방식으로 할지 여부
                                  (이미지, 다이어그램, 차트까지 이해)
        """
        self._provider_lms: Dict[str, Any] = {}
        self._active_provider: Optional[str] = None
        self.use_gemini_native_pdf = use_gemini_native_pdf
        try:
            self.setup_dspy()
        except Exception as e:
            # 초기화 실패해도 객체는 생성 (나중에 재시도 가능)
            print(f"⚠️ DSPy 초기화 경고: {e}")
            # 에러를 저장하여 나중에 확인 가능하도록
            self._init_error = str(e)
    
    @classmethod
    def reset_lm(cls):
        """LM 초기화 상태를 완전히 리셋합니다. 제공자가 변경되었을 때 사용합니다."""
        cls._last_provider = None
        cls._lm_initialized = False
    
    def _get_current_model_info(self, suffix: str = "") -> str:
        """
        현재 사용 중인 모델 정보를 반환합니다.

        Args:
            suffix: 모델 이름 뒤에 추가할 접미사 (예: " (DSPy)")

        Returns:
            모델 정보 문자열
        """
        provider = get_current_provider()
        provider_config = PROVIDER_CONFIG.get(provider, {})
        model_name = provider_config.get('model', 'unknown')
        display_name = provider_config.get('display_name', provider)

        if suffix:
            return f"{display_name} {model_name}{suffix}"
        return f"{display_name} {model_name}"

    def _is_long_context_model(self) -> bool:
        """
        현재 활성화된 모델이 Long Context 모델인지 확인합니다.

        Returns:
            Long Context 모델이면 True, 아니면 False
        """
        current_provider = self._active_provider or get_current_provider()
        return current_provider in ['gemini', 'gemini_3pro', 'gemini_25pro', 'gemini_25flash']

    def _get_pdf_content_for_context(self, pdf_text: str, max_length: int = 4000, use_long_context: bool = False) -> str:
        """
        PDF 텍스트를 컨텍스트에 맞게 자르거나 전체를 반환합니다.

        Args:
            pdf_text: PDF 텍스트
            max_length: 최대 길이 (Long Context 모델이 아닐 때 사용)
            use_long_context: Long Context 모델 여부

        Returns:
            처리된 PDF 텍스트
        """
        if not pdf_text:
            return "PDF 문서가 없습니다."

        if use_long_context:
            # Long Context 모델: 전체 텍스트 사용
            return pdf_text
        else:
            # 일반 모델: 지정된 길이로 자르기
            if len(pdf_text) > max_length:
                return pdf_text[:max_length] + "\n\n[문서 내용이 길어 일부만 표시됩니다...]"
            return pdf_text

    def _get_output_format_template(self):
        """출력 형식 템플릿을 반환하는 공통 함수"""
        return """
## 📝 출력 형식 요구사항

**⚠️ 중요**: 표만으로는 부족합니다. 반드시 아래 형식을 정확히 따르세요.

### 필수 구조:
1. **소제목** (예: ### 필수 시설 분석)
2. **소제목 해설** (3-5문장, 200-400자) - 표 이전에 반드시 상세한 서술형 분석 작성
3. **표** (정보 정리)
4. **표 해설** (4-8문장, 300-600자) - 표의 내용을 분석하고 해석

### 형식 예시:

### [소제목 1]
[소제목에 대한 상세한 해설을 반드시 작성하세요. 이 섹션은 표 이전에 필수입니다. 최소 200자 이상의 서술형 분석을 포함해야 합니다. 단순히 "다음과 같습니다" 같은 짧은 문장으로 끝나면 안 됩니다. 구체적인 수치, 근거, 분석 내용을 포함하여 작성하세요.]

| 항목 | 내용 | 비고 |
|------|------|------|
| 항목1 | 내용1 | 비고1 |
| 항목2 | 내용2 | 비고2 |

**[표 해설]**
위 표에 대한 상세한 해설을 4-8문장(300-600자)로 작성해주세요. 표의 내용을 분석하고 해석하며, 각 항목의 의미와 중요성을 설명해주세요. 단순히 표의 내용을 반복하는 것이 아니라, 표에서 드러나는 패턴, 관계, 인사이트를 도출하여 설명하세요.

### [소제목 2]
[소제목에 대한 상세한 해설 (3-5문장, 200-400자)]

| 항목 | 내용 | 비고 |
|------|------|------|
| 항목1 | 내용1 | 비고1 |
| 항목2 | 내용2 | 비고2 |

**[표 해설]**
위 표에 대한 상세한 해설을 4-8문장(300-600자)로 작성해주세요.

### [소제목 3]
[소제목에 대한 상세한 해설 (3-5문장, 200-400자)]

| 항목 | 내용 | 비고 |
|------|------|------|
| 항목1 | 내용1 | 비고1 |
| 항목2 | 내용2 | 비고2 |

**[표 해설]**
위 표에 대한 상세한 해설을 4-8문장(300-600자)로 작성해주세요.

### [소제목 4]
[소제목에 대한 상세한 해설 (3-5문장, 200-400자)]

| 항목 | 내용 | 비고 |
|------|------|------|
| 항목1 | 내용1 | 비고1 |
| 항목2 | 내용2 | 비고2 |

**[표 해설]**
위 표에 대한 상세한 해설을 4-8문장(300-600자)로 작성해주세요.

## ⚠️ 필수 준수 사항

1. **표 이전 서술 필수**: 모든 표 앞에 반드시 200-400자의 상세한 서술형 분석을 작성하세요. 표만으로는 절대 부족합니다.

2. **구체적 수치 제시**: 모든 분석에 구체적인 수치를 포함하세요 (면적, 인원, 비용, 이용률, 시간, 비율 등).

3. **근거 명시**: 모든 결론과 판단에 명확한 근거를 제시하세요. "~라고 판단했습니다"만으로는 부족하며, 왜 그렇게 판단했는지 구체적으로 설명하세요.

4. **분량 준수**: 각 소제목 해설은 최소 200자, 표 해설은 최소 300자 이상 작성하세요.

5. **서술형 문장**: 불릿 포인트나 키워드 나열이 아닌 완성된 문장으로 설명하세요.
"""
    
    def _get_extended_thinking_template(self):
        """확장 사고(Extended Thinking) 지시사항 템플릿을 반환하는 시스템 레벨 함수"""
        return """

## 🧠 확장 사고 (Extended Thinking) 지시사항

이 분석은 복잡한 다차원적 문제를 다루므로, **확장 사고(Extended Thinking)** 방식을 사용하여 깊이 있는 추론을 수행해주세요:

1. **단계별 사고 과정 명시**: 각 분석 단계에서 어떻게 생각했는지 명시적으로 기록
2. **다각도 분석**: 각 문제를 다양한 관점(경제적, 법적, 사회적, 기술적, 환경적)에서 분석
3. **가정과 불확실성 명시**: 분석에 사용된 가정과 불확실한 부분을 명확히 표시
4. **대안 검토**: 주요 결정사항에 대해 대안을 검토하고 비교 분석
5. **검증 가능한 결론**: 모든 결론이 검증 가능한 근거를 가지도록 함

**확장 사고 형식 예시:**
- **사고 단계 1**: [단계별 사고 과정]
- **가정**: [분석에 사용된 가정]
- **불확실성**: [불확실한 부분과 해결 방안]
- **대안 검토**: [고려한 대안과 비교]
- **결론**: [검증 가능한 결론]
"""
    
    def _build_signature_map(self) -> Dict[str, Type]:
        """
        블록 ID와 Signature 클래스를 매핑하는 딕셔너리를 동적으로 생성합니다.
        기본 블록은 하드코딩된 매핑을 사용하고, 커스텀 블록은 blocks.json에서 읽어서 동적으로 매핑합니다.
        
        Returns:
            블록 ID를 키로, Signature 클래스를 값으로 하는 딕셔너리
        """
        # 기본 블록들의 하드코딩된 매핑 (기존 블록 호환성 유지)
        signature_map = {            'basic_info': BasicInfoSignature,
            'requirements': RequirementsSignature,
            'design_suggestions': DesignSignature,
            'accessibility_analysis': AccessibilitySignature,
            'zoning_verification': ZoningSignature,
            'capacity_estimation': CapacitySignature,
            'feasibility_analysis': FeasibilitySignature,
            'phase1_facility_program': SimpleAnalysisSignature,
            'phase1_facility_area_reference': SimpleAnalysisSignature,
            'phase1_facility_area_calculation': SimpleAnalysisSignature,
            'phase1_candidate_generation': SimpleAnalysisSignature,
            'phase1_candidate_evaluation': SimpleAnalysisSignature
}
        
        # blocks.json에서 블록을 읽어서 동적으로 Signature 클래스 매핑 추가
        try:
            from prompt_processor import load_blocks
            blocks = load_blocks()
            
            # 현재 모듈의 globals()에서 Signature 클래스 찾기
            current_module_globals = globals()
            
            for block in blocks:
                block_id = block.get('id')
                if not block_id or block_id in signature_map:
                    # 이미 매핑된 블록은 건너뛰기
                    continue
                
                # 블록 ID에서 Signature 클래스명 생성 (Block Generator와 동일한 규칙)
                # 예: "my_analysis" -> "MyAnalysisSignature"
                signature_name = ''.join(word.capitalize() for word in block_id.split('_')) + 'Signature'
                
                # globals()에서 Signature 클래스 찾기
                signature_class = current_module_globals.get(signature_name)
                if signature_class and issubclass(signature_class, dspy.Signature):
                    signature_map[block_id] = signature_class
                    print(f"✅ 동적 Signature 매핑: {block_id} -> {signature_name}")
                else:
                    # Signature 클래스를 찾을 수 없으면 SimpleAnalysisSignature 사용
                    signature_map[block_id] = SimpleAnalysisSignature
                    if block.get('created_by') == 'user':
                        # 사용자가 생성한 블록인 경우에만 로그 출력
                        print(f"⚠️ Signature 클래스를 찾을 수 없음 ({signature_name}), SimpleAnalysisSignature 사용: {block_id}")
                        print(f"   💡 팁: 새로 생성한 블록의 경우 Streamlit 페이지를 새로고침하면 Signature가 로드됩니다.")
                        print(f"   💡 또는 dspy_analyzer.py 파일에 '{signature_name}' 클래스가 올바르게 추가되었는지 확인하세요.")
        except Exception as e:
            # blocks.json 로드 실패 시 기본 매핑만 사용
            print(f"⚠️ blocks.json 로드 실패, 기본 Signature 매핑만 사용: {e}")
        
        return signature_map
    
    def setup_dspy(self):
        """선택된 제공자에 따라 DSPy 설정"""
        current_provider = get_current_provider()
        
        # Provider가 변경된 경우 기존 캐시 클리어
        if hasattr(self, '_active_provider') and self._active_provider != current_provider:
            if current_provider in self._provider_lms:
                # Provider가 변경되었으므로 해당 provider의 캐시를 재생성
                del self._provider_lms[current_provider]
        
        self._active_provider = current_provider
        
        # 기존 LM 인스턴스가 있으면 재사용 (같은 provider인 경우)
        if current_provider in self._provider_lms:
            return
        
        temperature = 0.2
        max_tokens = 16000
        thinking_budget = None  # None이면 기본값 사용 (Gemini 2.5는 thinking 활성화)
        thinking_level = None  # Gemini 3 Pro용: "low" 또는 "high"
        include_thoughts = False  # Thought Summaries 포함 여부
        try:
            import streamlit as st
            temperature = float(st.session_state.get('llm_temperature', temperature))
            max_tokens = int(st.session_state.get('llm_max_tokens', max_tokens))
            thinking_budget = st.session_state.get('llm_thinking_budget', None)
            thinking_level = st.session_state.get('llm_thinking_level', None)
            include_thoughts = st.session_state.get('llm_include_thoughts', False)
        except Exception:
            temperature = float(os.environ.get('LLM_TEMPERATURE', temperature))
            max_tokens = int(os.environ.get('LLM_MAX_TOKENS', max_tokens))
            thinking_budget_str = os.environ.get('LLM_THINKING_BUDGET')
            if thinking_budget_str:
                try:
                    thinking_budget = int(thinking_budget_str)
                except ValueError:
                    thinking_budget = None
            thinking_level = os.environ.get('LLM_THINKING_LEVEL', None)
            include_thoughts_str = os.environ.get('LLM_INCLUDE_THOUGHTS', 'false').lower()
            include_thoughts = include_thoughts_str == 'true'

        temperature = max(0.0, min(1.0, temperature))
        max_tokens = max(1000, min(16000, max_tokens))

        # 선택된 제공자 정보 가져오기
        provider_config = PROVIDER_CONFIG.get(current_provider)
        if not provider_config:
            raise ValueError(f"지원하지 않는 제공자입니다: {current_provider}")

        # API 키 가져오기 (Vertex AI는 ADC 사용, API 키 불필요)
        api_key = None
        if provider_config.get('api_key_env'):
            api_key = get_api_key(current_provider)
            if not api_key:
                provider_name = provider_config.get('display_name', current_provider)
                api_key_env = provider_config['api_key_env']
                raise ValueError(f"{provider_name} API 키({api_key_env})를 설정해주세요.")

        # DSPy LM 설정
        try:
            provider_name = provider_config['provider']
            base_model_name = provider_config['model']
            
            # Google AI Studio (Gemini)의 경우 특별 처리
            if current_provider in ['gemini', 'gemini_3pro', 'gemini_25pro', 'gemini_25flash']:
                # Google AI Studio API 키 방식
                # models/ 접두사 제거
                clean_model = base_model_name.replace('models/', '').replace('model/', '')
                
                # LiteLLM Google AI Studio 모델 이름 형식
                # 여러 모델 이름 시도: gemini-pro가 가장 안정적
                # gemini-1.5-flash, gemini-1.5-pro는 일부 지역에서 사용 불가능할 수 있음
                litellm_model = f"gemini/{clean_model}"
                
                print(f"🔧 Google AI Studio Gemini 설정:")
                print(f"   base_model_name: {base_model_name}")
                print(f"   clean_model: {clean_model}")
                print(f"   litellm_model: {litellm_model}")
                print(f"   api_key 설정됨: {bool(api_key)}")
                if api_key:
                    print(f"   api_key 시작: {api_key[:10]}...")
                
                lm_kwargs = {
                    'model': litellm_model,
                    'api_key': api_key,
                    'max_tokens': max_tokens,
                    'temperature': temperature
                }
                extra_body = {
                    # Gemini 검색 연동을 기본 활성화 (grounded response 기대)
                    'tools': [{'google_search': {}}]
                }
                print("   Google Search Grounding: enabled (tools.google_search)")
                
                # Gemini 2.5 및 3 모델의 Thinking Config 지원
                # gemini-2.5-pro, gemini-2.5-flash, gemini-3-pro-preview 모델 감지
                is_thinking_model = (
                    'gemini-2.5' in clean_model or 
                    'gemini-3' in clean_model or
                    'gemini-2.0' in clean_model
                )
                
                if is_thinking_model:
                    # Thinking Config 설정
                    # 모델별로 다른 Thinking 파라미터 지원
                    is_gemini_3 = 'gemini-3' in clean_model
                    is_gemini_25_pro = 'gemini-2.5-pro' in clean_model
                    is_gemini_25_flash = 'gemini-2.5-flash' in clean_model or 'gemini-2.5-flash-lite' in clean_model
                    
                    thinking_config = {}
                    
                    # Gemini 3 Pro: thinking_level 우선 사용
                    if is_gemini_3:
                        if thinking_level:
                            if thinking_level.lower() in ['low', 'high']:
                                thinking_config['thinking_level'] = thinking_level.lower()
                                print(f"   Thinking Level: {thinking_level.lower()}")
                            else:
                                print(f"   경고: thinking_level은 'low' 또는 'high'만 지원됩니다.")
                        # Gemini 3 Pro는 thinking 비활성화 불가
                        # thinking_budget은 호환성을 위해 지원하지만 thinking_level 사용 권장
                        if thinking_budget is not None and not thinking_level:
                            print(f"   경고: Gemini 3 Pro는 thinking_level 사용을 권장합니다.")
                            if thinking_budget > 0:
                                thinking_config['thinking_budget'] = thinking_budget
                                print(f"   Thinking Budget: {thinking_budget} (호환성 모드)")
                    # Gemini 2.5 Pro: thinking_budget만 지원, 비활성화 불가
                    elif is_gemini_25_pro:
                        if thinking_budget is not None:
                            if thinking_budget == 0:
                                print(f"   경고: Gemini 2.5 Pro에서는 thinking을 비활성화할 수 없습니다.")
                            elif thinking_budget == -1:
                                thinking_config['thinking_budget'] = -1
                                print(f"   Thinking: 동적 사고 (thinking_budget=-1)")
                            elif 128 <= thinking_budget <= 32768:
                                thinking_config['thinking_budget'] = thinking_budget
                                print(f"   Thinking Budget: {thinking_budget}")
                            else:
                                print(f"   경고: Gemini 2.5 Pro의 thinking_budget 범위는 128-32768입니다.")
                        else:
                            print(f"   Thinking: 기본값 사용 (동적 사고)")
                    # Gemini 2.5 Flash: thinking_budget 지원, 비활성화 가능
                    elif is_gemini_25_flash:
                        if thinking_budget is not None:
                            if thinking_budget == 0:
                                thinking_config['thinking_budget'] = 0
                                print(f"   Thinking: 비활성화 (thinking_budget=0)")
                            elif thinking_budget == -1:
                                thinking_config['thinking_budget'] = -1
                                print(f"   Thinking: 동적 사고 (thinking_budget=-1)")
                            elif 0 <= thinking_budget <= 24576:
                                thinking_config['thinking_budget'] = thinking_budget
                                print(f"   Thinking Budget: {thinking_budget}")
                            else:
                                print(f"   경고: Gemini 2.5 Flash의 thinking_budget 범위는 0-24576입니다.")
                        else:
                            print(f"   Thinking: 기본값 사용 (동적 사고)")
                    
                    # Thought Summaries 지원 (모든 thinking 모델)
                    if include_thoughts:
                        thinking_config['include_thoughts'] = True
                        print(f"   Thought Summaries: 활성화")
                    
                    # extra_body에 thinking_config 추가
                    if thinking_config:
                        extra_body['thinking_config'] = thinking_config
                    else:
                        print(f"   Thinking: 기본값 사용 (모델 기본 설정)")
                
                if extra_body:
                    lm_kwargs['extra_body'] = extra_body
                
                # provider는 명시하지 않음 (모델 이름에서 자동 인식)
                print(f"🔧 Google AI Studio LM kwargs: model={lm_kwargs['model']}")
            else:
                litellm_model = (
                    f"{provider_name}/{base_model_name}"
                    if provider_name and "/" not in base_model_name
                    else base_model_name
                )
                lm_kwargs = {
                    'model': litellm_model,
                    'provider': provider_name,
                    'api_key': api_key,
                    'max_tokens': max_tokens,
                    'temperature': temperature
                }
            
            if current_provider == 'deepseek' and 'base_url' in provider_config:
                lm_kwargs['base_url'] = provider_config['base_url']
            
            lm = dspy.LM(**lm_kwargs)
            self._provider_lms[current_provider] = lm
            
            if not EnhancedArchAnalyzer._lm_initialized:
                try:
                    dspy.configure(lm=lm, track_usage=True, cache=False)
                    print("DSPy 전역 LM이 초기화되었습니다. (캐싱 비활성화)")
                except RuntimeError as thread_error:
                    print(f"전역 LM 설정 경고: {thread_error}. 활성 컨텍스트 방식으로 진행합니다.")
                EnhancedArchAnalyzer._lm_initialized = True
            
            provider_name = provider_config.get('display_name', current_provider)
            model_name = provider_config['model']
            print(f"{provider_name} ({model_name}) 모델이 준비되었습니다.")
            
            EnhancedArchAnalyzer._last_provider = current_provider
            try:
                import streamlit as st
                st.session_state['_last_llm_provider'] = current_provider
            except Exception:
                pass
                
        except Exception as e:
            provider_name = provider_config.get('display_name', current_provider)
            print(f"{provider_name} 모델 설정 실패: {e}")
            
            if current_provider != 'gemini':
                fallback_provider = 'gemini'
                fallback_config = PROVIDER_CONFIG.get(fallback_provider)
                fallback_api_key = get_api_key(fallback_provider)
                
                if fallback_config and fallback_api_key:
                    try:
                        lm = dspy.LM(
                            model=fallback_config['model'],
                            provider=fallback_config['provider'],
                            api_key=fallback_api_key,
                            max_tokens=max_tokens,
                            temperature=temperature
                        )
                        self._provider_lms[fallback_provider] = lm
                        self._active_provider = fallback_provider
                        if not EnhancedArchAnalyzer._lm_initialized:
                            try:
                                dspy.configure(lm=lm, track_usage=True, cache=False)
                                print("DSPy 전역 LM이 초기화되었습니다. (폴백, 캐싱 비활성화)")
                            except RuntimeError as thread_error:
                                print(f"전역 LM 설정 경고: {thread_error}. 활성 컨텍스트 방식으로 진행합니다.")
                            EnhancedArchAnalyzer._lm_initialized = True
                        print(f"폴백: {fallback_config.get('display_name')} 모델로 설정되었습니다.")
                        return
                    except Exception as e2:
                        print(f"폴백 모델 설정도 실패: {e2}")
            
            raise
    
    @contextmanager
    def _lm_context(self, provider: Optional[str] = None):
        """선택된 LM을 컨텍스트로 적용"""
        target_provider = provider or self._active_provider or get_current_provider()
        lm = None
        if hasattr(self, "_provider_lms"):
            lm = self._provider_lms.get(target_provider)
            if lm is None and self._provider_lms:
                lm = next(iter(self._provider_lms.values()))
        if lm is None:
            yield
            return
        try:
            ctx = dspy.settings.context(lm=lm)
        except Exception:
            yield
        else:
            with ctx:
                yield
    
    @contextmanager
    def _lm_context_with_system_instruction(self, system_instruction: str, provider: Optional[str] = None):
        """System Instruction을 포함한 LM 컨텍스트"""
        target_provider = provider or self._active_provider or get_current_provider()
        lm = None
        if hasattr(self, "_provider_lms"):
            lm = self._provider_lms.get(target_provider)
            if lm is None and self._provider_lms:
                lm = next(iter(self._provider_lms.values()))
        
        if lm is None:
            yield
            return
        
        # System Instruction을 LM에 적용
        original_extra_body = None
        try:
            # LiteLLM의 extra_body에 system_instruction 추가
            if hasattr(lm, 'kwargs') and 'extra_body' in lm.kwargs:
                original_extra_body = lm.kwargs.get('extra_body', {}).copy()
                if not isinstance(lm.kwargs.get('extra_body'), dict):
                    lm.kwargs['extra_body'] = {}
                lm.kwargs['extra_body']['system_instruction'] = {
                    "parts": [{"text": system_instruction}]
                }
            elif hasattr(lm, 'kwargs'):
                lm.kwargs['extra_body'] = {
                    'system_instruction': {
                        "parts": [{"text": system_instruction}]
                    }
                }
            
            # System instruction을 extra_body에 직접 추가 (LiteLLM 형식)
            if hasattr(lm, 'kwargs'):
                if 'extra_body' not in lm.kwargs:
                    lm.kwargs['extra_body'] = {}
                # LiteLLM은 system_instruction을 extra_body에 추가
                lm.kwargs['extra_body']['system_instruction'] = system_instruction
            
            try:
                ctx = dspy.settings.context(lm=lm)
            except Exception:
                yield
            else:
                with ctx:
                    yield
        finally:
            # 원래 상태로 복원
            if original_extra_body is not None and hasattr(lm, 'kwargs'):
                lm.kwargs['extra_body'] = original_extra_body
            elif hasattr(lm, 'kwargs') and 'extra_body' in lm.kwargs:
                # system_instruction만 제거
                if 'system_instruction' in lm.kwargs['extra_body']:
                    del lm.kwargs['extra_body']['system_instruction']
    
    @contextmanager
    def _lm_context_with_params(self, thinking_budget: Optional[int] = None, temperature: Optional[float] = None, system_instruction: Optional[str] = None, provider: Optional[str] = None):
        """Thinking Budget, Temperature, System Instruction을 포함한 LM 컨텍스트"""
        """Thinking Budget과 System Instruction을 포함한 LM 컨텍스트"""
        target_provider = provider or self._active_provider or get_current_provider()
        lm = None
        if hasattr(self, "_provider_lms"):
            lm = self._provider_lms.get(target_provider)
            if lm is None and self._provider_lms:
                lm = next(iter(self._provider_lms.values()))
        
        if lm is None:
            yield
            return
        
        # 현재 모델이 thinking을 지원하는지 확인
        current_provider = get_current_provider()
        provider_config = PROVIDER_CONFIG.get(current_provider, {})
        model_name = provider_config.get('model', '')
        clean_model = model_name.replace('models/', '').replace('model/', '')
        
        is_thinking_model = (
            'gemini-2.5' in clean_model or 
            'gemini-3' in clean_model or
            'gemini-2.0' in clean_model
        )
        
        # Temperature 적용
        original_temperature = None
        if temperature is not None and hasattr(lm, 'kwargs'):
            original_temperature = lm.kwargs.get('temperature')
            lm.kwargs['temperature'] = max(0.0, min(1.0, temperature))
        
        if not is_thinking_model:
            # Thinking을 지원하지 않는 모델인 경우 system_instruction과 temperature만 적용
            try:
                if system_instruction:
                    with self._lm_context_with_system_instruction(system_instruction, provider):
                        yield
                else:
                    with self._lm_context(provider):
                        yield
            finally:
                # Temperature 복원
                if original_temperature is not None and hasattr(lm, 'kwargs'):
                    lm.kwargs['temperature'] = original_temperature
            return
        
        # Thinking Budget과 System Instruction을 LM에 적용
        original_extra_body = None
        try:
            if hasattr(lm, 'kwargs'):
                if 'extra_body' in lm.kwargs:
                    original_extra_body = lm.kwargs.get('extra_body', {}).copy()
                else:
                    lm.kwargs['extra_body'] = {}
                
                # System Instruction 추가
                if system_instruction:
                    lm.kwargs['extra_body']['system_instruction'] = system_instruction
                
                # Thinking Config 추가
                is_gemini_3 = 'gemini-3' in clean_model
                is_gemini_25_pro = 'gemini-2.5-pro' in clean_model
                is_gemini_25_flash = 'gemini-2.5-flash' in clean_model or 'gemini-2.5-flash-lite' in clean_model
                
                thinking_config = {}
                
                if is_gemini_3:
                    # Gemini 3는 thinking_level 사용 권장, 하지만 thinking_budget도 지원
                    if thinking_budget > 0:
                        thinking_config['thinking_budget'] = thinking_budget
                elif is_gemini_25_pro:
                    # Gemini 2.5 Pro는 thinking_budget만 지원
                    if thinking_budget > 0:
                        thinking_config['thinking_budget'] = max(128, min(32768, thinking_budget))
                elif is_gemini_25_flash:
                    # Gemini 2.5 Flash는 thinking_budget 지원, 0으로 비활성화 가능
                    thinking_config['thinking_budget'] = max(0, min(24576, thinking_budget))
                
                if thinking_config:
                    if 'thinking_config' not in lm.kwargs['extra_body']:
                        lm.kwargs['extra_body']['thinking_config'] = {}
                    lm.kwargs['extra_body']['thinking_config'].update(thinking_config)
            
            # Temperature 적용
            if temperature is not None:
                original_temperature = lm.kwargs.get('temperature')
                lm.kwargs['temperature'] = max(0.0, min(1.0, temperature))
            
            try:
                ctx = dspy.settings.context(lm=lm)
            except Exception:
                yield
            else:
                with ctx:
                    yield
        finally:
            # 원래 상태로 복원
            if original_extra_body is not None and hasattr(lm, 'kwargs'):
                lm.kwargs['extra_body'] = original_extra_body
            elif hasattr(lm, 'kwargs') and 'extra_body' in lm.kwargs:
                # 추가한 항목만 제거
                if 'system_instruction' in lm.kwargs['extra_body']:
                    del lm.kwargs['extra_body']['system_instruction']
                if 'thinking_config' in lm.kwargs['extra_body']:
                    del lm.kwargs['extra_body']['thinking_config']
            
            # Temperature 복원
            if 'original_temperature' in locals() and original_temperature is not None and hasattr(lm, 'kwargs'):
                lm.kwargs['temperature'] = original_temperature
    
    def _get_structured_output_config(self, schema: Optional[Union[Type, Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
        """
        Pydantic 모델 또는 JSON 스키마를 구조화된 출력 설정으로 변환
        
        Args:
            schema: Pydantic 모델 클래스 또는 JSON 스키마 딕셔너리
        
        Returns:
            구조화된 출력 설정 딕셔너리 또는 None
        """
        if schema is None:
            return None
        
        try:
            # Pydantic 모델 클래스인 경우
            if PYDANTIC_AVAILABLE and isinstance(schema, type) and issubclass(schema, BaseModel):
                return {
                    "response_mime_type": "application/json",
                    "response_json_schema": schema.model_json_schema()
                }
            # JSON 스키마 딕셔너리인 경우
            elif isinstance(schema, dict):
                return {
                    "response_mime_type": "application/json",
                    "response_json_schema": schema
                }
        except Exception as e:
            print(f"⚠️ 구조화된 출력 스키마 변환 오류: {e}")
        
        return None
    
    def _parse_structured_response(self, response_text: str, schema: Optional[Union[Type, Dict[str, Any]]]) -> Any:
        """
        구조화된 응답을 Pydantic 모델로 파싱
        
        Args:
            response_text: JSON 문자열 응답
            schema: Pydantic 모델 클래스 또는 None
        
        Returns:
            Pydantic 모델 인스턴스 또는 파싱된 딕셔너리
        """
        if schema is None:
            return response_text
        
        try:
            # JSON 파싱
            response_data = json.loads(response_text)
            
            # Pydantic 모델이 제공된 경우 검증 및 변환
            if PYDANTIC_AVAILABLE and isinstance(schema, type) and issubclass(schema, BaseModel):
                return schema.model_validate(response_data)
            else:
                # JSON 스키마만 제공된 경우 딕셔너리 반환
                return response_data
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 파싱 오류: {e}")
            return response_text
        except Exception as e:
            print(f"⚠️ 구조화된 응답 파싱 오류: {e}")
            return response_text
    
    def _convert_function_declarations(self, function_declarations: List[Union[Dict[str, Any], Callable]]) -> List[Dict[str, Any]]:
        """
        Function declarations를 LiteLLM 형식으로 변환
        
        Args:
            function_declarations: Function declaration 딕셔너리 리스트 또는 Python 함수 리스트
        
        Returns:
            변환된 function declaration 리스트
        """
        converted = []
        
        for func_decl in function_declarations:
            if isinstance(func_decl, dict):
                # 이미 딕셔너리 형식인 경우
                converted.append(func_decl)
            elif callable(func_decl):
                # Python 함수인 경우 - Google GenAI SDK 스타일로 변환 시도
                try:
                    # 함수의 시그니처와 docstring을 기반으로 declaration 생성
                    import inspect
                    
                    sig = inspect.signature(func_decl)
                    docstring = inspect.getdoc(func_decl) or ""
                    
                    # Function declaration 생성
                    func_decl_dict = {
                        "name": func_decl.__name__,
                        "description": docstring,
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                    
                    # 파라미터 추출
                    for param_name, param in sig.parameters.items():
                        param_type = param.annotation
                        param_desc = ""
                        
                        # 타입을 문자열로 변환
                        type_str = "string"
                        if param_type == int:
                            type_str = "integer"
                        elif param_type == float:
                            type_str = "number"
                        elif param_type == bool:
                            type_str = "boolean"
                        elif param_type == list or getattr(param_type, '__origin__', None) == list:
                            type_str = "array"
                        
                        func_decl_dict["parameters"]["properties"][param_name] = {
                            "type": type_str,
                            "description": param_desc
                        }
                        
                        if param.default == inspect.Parameter.empty:
                            func_decl_dict["parameters"]["required"].append(param_name)
                    
                    converted.append(func_decl_dict)
                except Exception as e:
                    print(f"⚠️ 함수를 function declaration으로 변환 실패: {e}")
                    continue
            else:
                print(f"⚠️ 지원하지 않는 function declaration 형식: {type(func_decl)}")
        
        return converted
    
    def _extract_function_calls(self, response) -> List[Dict[str, Any]]:
        """
        LiteLLM 응답에서 function calls 추출
        
        Args:
            response: LiteLLM completion 응답
        
        Returns:
            Function call 리스트
        """
        function_calls = []
        
        try:
            if hasattr(response, 'choices') and len(response.choices) > 0:
                message = response.choices[0].message
                
                # tool_calls 확인 (OpenAI 형식)
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    for tool_call in message.tool_calls:
                        if hasattr(tool_call, 'function'):
                            function_calls.append({
                                "id": getattr(tool_call, 'id', None),
                                "name": tool_call.function.name,
                                "arguments": json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
                            })
                
                # function_call 확인 (구형 형식)
                elif hasattr(message, 'function_call') and message.function_call:
                    func_call = message.function_call
                    try:
                        # name 안전 추출
                        try:
                            func_name = func_call.name if hasattr(func_call, 'name') else func_call.get('name') if hasattr(func_call, 'get') else 'unknown'
                        except (AttributeError, Exception) as e:
                            print(f"[WARNING] func_call.name 접근 실패 (구형): {e}, 타입: {type(func_call)}")
                            func_name = 'unknown'

                        # arguments 안전 추출
                        try:
                            func_args = func_call.arguments if hasattr(func_call, 'arguments') else func_call.get('arguments', {}) if hasattr(func_call, 'get') else {}
                        except (AttributeError, Exception) as e:
                            print(f"[WARNING] func_call.arguments 접근 실패 (구형): {e}, 타입: {type(func_call)}")
                            func_args = {}

                        function_calls.append({
                            "id": None,
                            "name": func_name,
                            "arguments": func_args
                        })
                    except Exception as e:
                        print(f"[WARNING] function_call 처리 실패 (구형): {e}, 타입: {type(func_call)}")
        except Exception as e:
            print(f"⚠️ Function calls 추출 오류: {e}")
        
        return function_calls
    
    def _execute_function_call(self, function_name: str, arguments: Dict[str, Any], function_implementations: Dict[str, Callable]) -> Any:
        """
        Function call 실행
        
        Args:
            function_name: 실행할 함수 이름
            arguments: 함수 인자
            function_implementations: 함수 이름 -> 함수 구현 매핑
        
        Returns:
            함수 실행 결과
        """
        if function_name not in function_implementations:
            return {"error": f"Function '{function_name}' not found in implementations"}
        
        try:
            func = function_implementations[function_name]
            result = func(**arguments)
            return result
        except Exception as e:
            return {"error": f"Function execution failed: {str(e)}"}
    
    def _analyze_with_function_calling(
        self,
        prompt: str,
        pdf_text: str = None,
        function_declarations: List[Union[Dict[str, Any], Callable]] = None,
        function_implementations: Dict[str, Callable] = None,
        automatic_function_calling: bool = False,
        function_calling_mode: str = "AUTO",
        max_iterations: int = 10,
        response_schema: Optional[Union[Type, Dict[str, Any]]] = None,
        block_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Function calling을 사용한 분석
        
        Args:
            prompt: 사용자 프롬프트
            pdf_text: PDF 텍스트
            function_declarations: Function declaration 리스트
            function_implementations: 함수 이름 -> 함수 구현 매핑
            automatic_function_calling: 자동 함수 실행 여부
            function_calling_mode: Function calling 모드
            max_iterations: 최대 반복 횟수 (compositional calling)
            response_schema: 구조화된 출력 스키마 (선택사항)
            block_id: 블록 ID
        
        Returns:
            분석 결과 딕셔너리
        """
        import litellm
        
        current_provider = self._active_provider or get_current_provider()
        provider_config = PROVIDER_CONFIG.get(current_provider)
        api_key = get_api_key(current_provider)
        base_model_name = provider_config['model']
        clean_model = base_model_name.replace('models/', '').replace('model/', '')
        litellm_model = f"gemini/{clean_model}"
        
        # temperature와 max_tokens 가져오기
        temp_value = 0.2
        max_tokens_value = 16000
        try:
            import streamlit as st
            temp_value = float(st.session_state.get('llm_temperature', 0.2))
            max_tokens_value = int(st.session_state.get('llm_max_tokens', 16000))
        except Exception:
            temp_value = float(os.environ.get('LLM_TEMPERATURE', 0.2))
            max_tokens_value = int(os.environ.get('LLM_MAX_TOKENS', 16000))
        
        # Function declarations 변환
        converted_declarations = self._convert_function_declarations(function_declarations)
        if not converted_declarations:
            raise ValueError("유효한 function declarations가 없습니다.")
        
        print(f"🔧 Function Calling 사용: {len(converted_declarations)}개 함수")
        
        # LiteLLM tools 형식으로 변환
        tools = [{
            "type": "function",
            "function": decl
        } for decl in converted_declarations]
        
        # Tool config 설정
        tool_config = None
        if function_calling_mode != "AUTO":
            tool_config = {
                "tool_choice": {
                    "type": "function" if function_calling_mode == "ANY" else "none" if function_calling_mode == "NONE" else "auto"
                }
            }
        
        # 구조화된 출력 설정 (있는 경우)
        extra_body = {}
        structured_output_config = self._get_structured_output_config(response_schema)
        if structured_output_config:
            extra_body.update(structured_output_config)
        
        # 대화 히스토리 초기화
        messages = [{"role": "user", "content": prompt}]
        
        # Compositional function calling을 위한 루프
        iteration = 0
        function_calls_history = []
        
        while iteration < max_iterations:
            iteration += 1
            print(f"🔄 Function calling 반복 {iteration}/{max_iterations}")
            
            # API 호출
            try:
                call_kwargs = {
                    "model": litellm_model,
                    "messages": messages,
                    "api_key": api_key,
                    "temperature": temp_value,
                    "max_tokens": max_tokens_value
                }
                
                # 첫 번째 요청에만 tools 전달
                if iteration == 1:
                    call_kwargs["tools"] = tools
                    if tool_config:
                        call_kwargs["tool_choice"] = tool_config.get("tool_choice")
                
                if extra_body:
                    call_kwargs["extra_body"] = extra_body
                
                response = litellm.completion(**call_kwargs)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"API 호출 실패: {str(e)}",
                    "model": self._get_current_model_info(" (Function Calling)"),
                    "block_id": block_id
                }
            
            # 응답에서 function calls 추출
            function_calls = self._extract_function_calls(response)
            
            if not function_calls:
                # Function call이 없으면 최종 텍스트 응답
                response_text = response.choices[0].message.content if response.choices[0].message.content else ""
                
                # 구조화된 출력 파싱
                if response_schema and response_text:
                    parsed_response = self._parse_structured_response(response_text, response_schema)
                    return {
                        "success": True,
                        "analysis": parsed_response if PYDANTIC_AVAILABLE and isinstance(parsed_response, BaseModel) else response_text,
                        "parsed_data": parsed_response if response_schema else None,
                        "model": self._get_current_model_info(" (Function Calling)"),
                        "method": "Function Calling",
                        "block_id": block_id,
                        "function_calls": function_calls_history
                    }
                else:
                    return {
                        "success": True,
                        "analysis": response_text,
                        "model": self._get_current_model_info(" (Function Calling)"),
                        "method": "Function Calling",
                        "block_id": block_id,
                        "function_calls": function_calls_history
                    }
            
            # Function calls 실행 (Parallel function calling 지원)
            function_responses = []
            for func_call in function_calls:
                function_name = func_call["name"]
                arguments = func_call.get("arguments", {})
                
                print(f"🔧 Function 호출: {function_name}({arguments})")
                
                if automatic_function_calling and function_implementations:
                    # 자동 실행
                    result = self._execute_function_call(function_name, arguments, function_implementations)
                    function_responses.append({
                        "role": "tool",
                        "tool_call_id": func_call.get("id"),
                        "name": function_name,
                        "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                    })
                    function_calls_history.append({
                        "name": function_name,
                        "arguments": arguments,
                        "result": result
                    })
                else:
                    # 수동 실행 - function calls 반환
                    return {
                        "success": True,
                        "analysis": f"Function call required: {function_name}",
                        "function_calls": [func_call],
                        "model": self._get_current_model_info(" (Function Calling)"),
                        "method": "Function Calling (Manual)",
                        "block_id": block_id,
                        "requires_manual_execution": True
                    }
            
            # Function responses를 대화 히스토리에 추가
            # 이전 모델 응답 추가
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": fc.get("id", f"call_{i}"),
                        "type": "function",
                        "function": {
                            "name": fc["name"],
                            "arguments": json.dumps(fc["arguments"])
                        }
                    }
                    for i, fc in enumerate(function_calls)
                ]
            })
            
            # Function responses 추가 (Parallel calling - 모든 응답을 한 번에 추가)
            messages.extend(function_responses)
        
        # 최대 반복 횟수 도달
        return {
            "success": False,
            "error": f"최대 반복 횟수({max_iterations})에 도달했습니다.",
            "model": self._get_current_model_info(" (Function Calling)"),
            "block_id": block_id,
            "function_calls": function_calls_history
        }
    
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
{self._get_pdf_content_for_context(pdf_text, max_length=4000, use_long_context=self._is_long_context_model()) if pdf_text else "PDF 문서가 없습니다."}

## 확장 사고 (Extended Thinking) 및 Chain of Thought 분석

**중요**: 이 분석은 확장 사고(Extended Thinking) 방식을 사용합니다. 복잡한 문제를 단계별로 깊이 있게 사고하고, 각 단계에서 발견한 내용을 명시적으로 기록하세요.

### 확장 사고 단계별 가이드:

#### 1단계: 정보 수집 및 분류 (확장 사고)
- **명시적 정보 식별**: 문서에서 직접 언급된 모든 정보를 체계적으로 나열
- **암시적 정보 추론**: 문서에서 직접 언급되지 않았지만 추론 가능한 정보 식별
  - 각 추론의 근거를 명확히 제시
  - 추론의 신뢰도를 평가 (높음/중간/낮음)
- **정보 신뢰도 평가**: 각 정보의 출처와 신뢰도를 3단계로 평가
  - **높음**: 문서에 명시적으로 언급됨
  - **중간**: 문서의 맥락에서 합리적으로 추론 가능
  - **낮음**: 일반적인 지식이나 가정에 기반

#### 2단계: 핵심 요소 추출 (확장 사고)
- **프로젝트 목표 및 비전 분석**
  - 명시적 목표와 암시적 목표를 구분하여 정리
  - 각 목표의 우선순위와 중요도 평가
  - 목표 간 상호관계 분석
- **주요 제약조건 및 기회요소 분석**
  - 각 제약조건이 프로젝트에 미치는 영향 분석
  - 기회요소의 실현 가능성과 기대 효과 평가
  - 제약조건과 기회요소 간의 상호작용 분석
- **이해관계자 및 영향 범위 분석**
  - 이해관계자별 관심사와 기대 효과 분석
  - 프로젝트가 각 이해관계자에게 미치는 영향 범위 평가

#### 3단계: 분석 및 종합 (확장 사고)
- **각 요소의 중요도 평가**
  - 정량적 점수(1-5점)와 정성적 평가를 함께 제시
  - 중요도 평가의 근거를 명확히 제시
- **요소 간 상호관계 분석**
  - 요소 간 상호작용을 다이어그램이나 표로 시각화
  - 긍정적/부정적 상호작용을 구분하여 분석
- **종합적 해석 및 인사이트 도출**
  - 모든 분석 결과를 통합하여 종합 해석
  - 핵심 인사이트 3-5개를 명확히 제시
  - 각 인사이트의 실무적 의미와 적용 방안 제시

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

{self._get_output_format_template()}
"""
        
        try:
            with self._lm_context():
                result = dspy.Predict(SimpleAnalysisSignature)(input=prompt)
            
            return {
                "success": True,
                "analysis": result.output,
                "model": self._get_current_model_info(" (DSPy)"),
                "method": "DSPy + CoT"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": self._get_current_model_info(" (DSPy)"),
                "method": "DSPy + CoT"
            }
    
    def analyze_custom_block(
        self, 
        prompt, 
        pdf_text, 
        block_id=None, 
        project_info=None, 
        pdf_path=None, 
        response_schema=None,
        function_declarations: Optional[List[Union[Dict[str, Any], Callable]]] = None,
        function_implementations: Optional[Dict[str, Callable]] = None,
        automatic_function_calling: bool = False,
        function_calling_mode: str = "AUTO",
        max_iterations: int = 10,
        many_shot_examples: Optional[List[str]] = None
    ):
        """
        사용자 정의 블록 분석 - 블록별 고유 프롬프트와 Signature 사용
        
        Args:
            prompt: 분석 프롬프트
            pdf_text: PDF 텍스트 (기존 방식)
            block_id: 블록 ID
            project_info: 프로젝트 정보
            pdf_path: PDF 파일 경로 (Gemini 네이티브 처리용, 선택사항)
            response_schema: 구조화된 출력 스키마 (Pydantic 모델 클래스 또는 JSON 스키마 딕셔너리, 선택사항)
            function_declarations: Function declaration 리스트 (딕셔너리 또는 Python 함수)
            function_implementations: 함수 이름 -> 함수 구현 매핑 (자동 실행용)
            automatic_function_calling: 자동 함수 실행 여부
            function_calling_mode: Function calling 모드 ("AUTO", "ANY", "NONE")
            max_iterations: 최대 반복 횟수 (compositional calling)
            many_shot_examples: Many-shot learning 예제 리스트 (선택사항)
        """
        try:
            # Gemini 네이티브 PDF 처리 사용 (pdf_path가 제공되고 옵션이 활성화된 경우)
            if self.use_gemini_native_pdf and pdf_path:
                try:
                    from pdf_analyzer import extract_text_with_gemini_pdf
                    
                    print(f"📄 Gemini 네이티브 PDF 처리 사용: {pdf_path}")
                    gemini_result = extract_text_with_gemini_pdf(
                        pdf_path=pdf_path,
                        prompt="이 PDF 문서를 전체적으로 분석하여 텍스트, 이미지, 다이어그램, 차트, 테이블을 포함한 모든 내용을 구조화된 형식으로 추출해주세요."
                    )
                    
                    if gemini_result.get("success"):
                        pdf_text = gemini_result.get("text", pdf_text)
                        print(f"✅ Gemini PDF 처리 완료 (방식: {gemini_result.get('method', 'unknown')})")
                    else:
                        print(f"⚠️ Gemini PDF 처리 실패, 기존 텍스트 사용: {gemini_result.get('error')}")
                except Exception as e:
                    print(f"⚠️ Gemini PDF 처리 오류, 기존 텍스트 사용: {e}")
            
            # 블록 ID에 따라 적절한 Signature 선택 (동적 생성)
            signature_map = self._build_signature_map()
            
            # 기본 Signature 사용 (블록 ID가 없거나 매핑되지 않은 경우)
            signature_class = signature_map.get(block_id, SimpleAnalysisSignature)
            
            # 디버깅 정보 출력
            print(f"🔍 DSPy 분석 디버깅:")
            print(f"   블록 ID: {block_id}")
            print(f"   사용할 Signature: {signature_class.__name__}")
            print(f"   프롬프트 길이: {len(prompt)}자")
            print(f"   PDF 텍스트 길이: {len(pdf_text) if pdf_text else 0}자")
            print(f"   프롬프트 미리보기: {prompt[:200]}...")
            
            # 웹 검색 수행 (특정 블록에 대해서만)
            web_search_context = ""
            if block_id and project_info:
                try:
                    web_search_context = get_web_search_context(block_id, project_info, pdf_text)
                    if web_search_context:
                        print(f"🌐 웹 검색 결과 수집 완료: {block_id}")
                except Exception as e:
                    print(f"⚠️ 웹 검색 오류 (계속 진행): {e}")
            
            # RAG 기반 문서 검색 (PDF 텍스트가 길거나 참고 문서가 있을 때)
            rag_context = ""
            if RAG_AVAILABLE and pdf_text and len(pdf_text) > 5000:
                try:
                    # 프롬프트에서 핵심 키워드 추출 (간단한 방식)
                    query_keywords = prompt[:500] if prompt else ""
                    
                    # RAG 시스템으로 관련 문서 부분 검색
                    rag_system = build_rag_system_for_documents(
                        documents=[pdf_text],
                        chunk_size=1000,
                        overlap=200
                    )
                    
                    # 프롬프트 기반 쿼리로 관련 컨텍스트 검색
                    relevant_contexts = query_rag_system(
                        rag_system=rag_system,
                        query=query_keywords,
                        top_k=3,
                        build_prompt=False
                    )
                    
                    if relevant_contexts:
                        context_texts = [ctx for ctx, _ in relevant_contexts]
                        rag_context = "\n\n".join(context_texts)
                        print(f"📚 RAG 기반 문서 검색 완료: {len(relevant_contexts)}개 관련 컨텍스트 발견")
                except Exception as e:
                    print(f"⚠️ RAG 검색 오류 (계속 진행): {e}")
            
            # 프롬프트 템플릿의 플레이스홀더를 실제 PDF 텍스트로 치환 (단일 블록 분석용)
            formatted_prompt = prompt
            if "{pdf_text}" in prompt:
                # 실제 PDF 텍스트를 삽입 (길이 제한 고려)
                pdf_content = pdf_text if pdf_text else "PDF 문서가 업로드되지 않았습니다."
                
                # RAG 컨텍스트가 있으면 우선 사용
                if rag_context:
                    pdf_content = rag_context
                    print("📚 RAG로 추출한 관련 컨텍스트를 사용합니다.")
                # 너무 길면 자르기 (토큰 제한 고려)
                else:
                    # Long Context 모델 감지 및 제한 완화
                    current_provider = self._active_provider or get_current_provider()
                    is_long_context_model = current_provider in ['gemini', 'gemini_3pro', 'gemini_25pro', 'gemini_25flash']

                    # Long Context 모델의 경우 더 긴 텍스트 허용
                    # 1M 토큰 ≈ 750,000 문자 (대략적인 변환: 1 토큰 ≈ 0.75 문자)
                    # 안전 마진을 두고 500,000 문자로 제한
                    long_context_limit = 500000 if is_long_context_model else 12000

                    if len(pdf_content) > long_context_limit:
                        if is_long_context_model:
                            # Long Context 모델: 경고만 표시하고 전체 사용
                            print(f"📄 긴 문서 감지 ({len(pdf_content):,}자). Long Context 모델이므로 전체 내용을 사용합니다.")
                            print(f"   참고: 매우 긴 컨텍스트는 비용과 지연시간이 증가할 수 있습니다.")
                        else:
                            # 일반 모델: 기존 제한 적용
                            pdf_content = pdf_content[:12000] + "\n\n[문서 내용이 길어 일부만 표시됩니다. 위 내용을 중심으로 분석해주세요...]"
                            print(f"⚠️ 문서가 너무 깁니다 ({len(pdf_content)}자). 앞부분만 사용합니다.")
                
                formatted_prompt = prompt.replace("{pdf_text}", pdf_content)
            
            # 문서 기반 추론 강조 지시사항 추가
            document_based_instruction = f"""

## 📄 문서 기반 분석 필수 지시사항

**⚠️ 매우 중요**: 아래 지시사항을 반드시 준수하세요.

### 1. 문서 내용 기반 추론 필수
- **위에 제공된 문서 내용을 정확히 읽고 이해한 후 분석하세요**
- **문서에 명시적으로 언급된 모든 사실, 수치, 요구사항을 추출하고 분석에 활용하세요**
- **일반적인 템플릿이나 일반론적인 내용이 아닌, 이 특정 프로젝트 문서의 실제 내용을 기반으로 분석하세요**

### 2. 문서 인용 및 근거 제시 필수
- **분석 결과의 모든 주요 주장은 문서의 구체적인 내용을 인용하여 뒷받침하세요**
- **예시**: "문서 3페이지에 '대지면적 5,000㎡'라고 명시되어 있어..." 형식으로 근거를 제시하세요
- **수치나 사실을 제시할 때는 반드시 문서의 출처를 명시하세요**

### 3. 문서에 없는 내용은 생성하지 말 것
- **문서에 명시되지 않은 내용은 추측하지 마세요**
- **정보가 없는 경우 '문서에 명시되지 않음' 또는 '추가 확인 필요'로 표시하세요**
- **일반적인 건축 프로젝트의 일반론적인 내용을 나열하지 마세요**

### 4. 문서 내용의 구체적 활용
- **문서에서 추출한 구체적인 수치, 명칭, 위치, 규모 등을 분석에 반드시 포함하세요**
- **문서의 맥락과 배경을 이해하고, 이를 바탕으로 심층적인 추론을 수행하세요**
- **문서의 암시적 의미나 연관된 요구사항을 추론하여 분석을 풍부하게 만들되, 추론의 근거를 명확히 제시하세요**

### 5. 분석 결과의 차별화
- **이 프로젝트만의 고유한 특징과 요구사항을 강조하세요**
- **다른 프로젝트와 구별되는 특별한 내용을 찾아 분석하세요**
- **문서에서 발견한 특이사항, 제약조건, 기회요소 등을 구체적으로 분석하세요**

**위 지시사항을 준수하지 않으면 분석이 반복되거나 일반론적일 수 있습니다. 반드시 위 문서 내용을 중심으로 분석하세요.**
"""
            
            # 웹 검색 결과를 프롬프트에 추가
            if web_search_context:
                formatted_prompt = f"""{formatted_prompt}

{web_search_context}

**중요**: 위 웹 검색 결과를 참고하여 최신 정보와 시장 동향을 반영한 분석을 수행해주세요. 단, 웹 검색 결과는 문서 내용을 보완하는 역할이며, 분석의 주 근거는 반드시 위에 제공된 문서 내용이어야 합니다. 웹 검색 결과에서 얻은 정보는 반드시 출처를 명시하고, 문서 내용과 교차 검증하여 사용하세요.
"""
            else:
                # 웹 검색 결과가 없어도 문서 기반 분석 강조
                formatted_prompt = f"""{formatted_prompt}{document_based_instruction}"""
            
            # 확장 사고 지시사항 추가 (모든 블록에 기본 적용)
            # 블록 프롬프트에 이미 Chain of Thought 지시사항이 포함되어 있는 블록 목록
            # (이 블록들은 중복 방지를 위해 시스템 레벨 지시사항을 추가하지 않음)
            blocks_with_builtin_cot = ['phase1_facility_program']
            
            # 모든 블록에 기본적으로 확장 사고 지시사항 적용 (중복 방지 제외)
            extended_thinking_note = ""
            if block_id and block_id not in blocks_with_builtin_cot:
                # 시스템 레벨 확장 사고 템플릿 사용
                extended_thinking_note = self._get_extended_thinking_template()
            
            # Many-shot Learning 지원
            many_shot_section = ""
            if many_shot_examples:
                is_long_context_model = self._is_long_context_model()
                if is_long_context_model:
                    print(f"📚 Many-shot Learning 활성화: {len(many_shot_examples)}개 예제")
                    many_shot_section = "\n\n## 예제 (Many-shot Learning)\n\n"
                    for i, example in enumerate(many_shot_examples, 1):
                        many_shot_section += f"### 예제 {i}\n{example}\n\n"
            
            # 프롬프트 최적화: Long Context에서는 쿼리를 끝에 배치
            # Long Context에서는 쿼리를 컨텍스트의 끝에 배치하는 것이 더 효과적
            is_long_context = self._is_long_context_model()
            
            if is_long_context and "{pdf_text}" in prompt:
                # Long Context 최적화: 쿼리(프롬프트)를 끝에 배치
                # formatted_prompt는 이미 PDF 텍스트가 포함되어 있음
                # 프롬프트에서 PDF 텍스트를 제외한 쿼리 부분 추출
                prompt_without_pdf = prompt.replace("{pdf_text}", "").strip()
                if not prompt_without_pdf:
                    prompt_without_pdf = "위 문서를 분석해주세요."
                
                # 출력 형식 요구사항 추가
                enhanced_prompt = f"""
{formatted_prompt}

{extended_thinking_note}

{many_shot_section}

{self._get_output_format_template() if response_schema is None else ""}

---
## 분석 요청
{prompt_without_pdf}
"""
            else:
                # 기존 방식: 프롬프트 → 지시사항
                enhanced_prompt = f"""
{formatted_prompt}{extended_thinking_note}

{many_shot_section}

{self._get_output_format_template() if response_schema is None else ""}
"""
            
            # Function Calling 지원 (Gemini 모델에서 function_declarations가 제공된 경우)
            if function_declarations:
                current_provider = self._active_provider or get_current_provider()
                if current_provider in ['gemini', 'gemini_3pro', 'gemini_25pro', 'gemini_25flash']:
                    try:
                        return self._analyze_with_function_calling(
                            prompt=enhanced_prompt,
                            pdf_text=pdf_text,
                            function_declarations=function_declarations,
                            function_implementations=function_implementations or {},
                            automatic_function_calling=automatic_function_calling,
                            function_calling_mode=function_calling_mode,
                            max_iterations=max_iterations,
                            response_schema=response_schema,
                            block_id=block_id
                        )
                    except Exception as e:
                        print(f"⚠️ Function calling 사용 실패, 기존 DSPy 방식으로 폴백: {e}")
                        # 폴백: 기존 DSPy 방식 사용
            
            # 구조화된 출력 지원 (Gemini 모델에서 response_schema가 제공된 경우)
            structured_output_config = self._get_structured_output_config(response_schema)
            if structured_output_config:
                current_provider = self._active_provider or get_current_provider()
                if current_provider in ['gemini', 'gemini_3pro', 'gemini_25pro', 'gemini_25flash']:
                    try:
                        # LiteLLM을 직접 호출하여 구조화된 출력 사용
                        import litellm
                        
                        provider_config = PROVIDER_CONFIG.get(current_provider)
                        api_key = get_api_key(current_provider)
                        base_model_name = provider_config['model']
                        clean_model = base_model_name.replace('models/', '').replace('model/', '')
                        litellm_model = f"gemini/{clean_model}"
                        
                        # temperature와 max_tokens 가져오기
                        temp_value = 0.2
                        max_tokens_value = 16000
                        try:
                            import streamlit as st
                            temp_value = float(st.session_state.get('llm_temperature', 0.2))
                            max_tokens_value = int(st.session_state.get('llm_max_tokens', 16000))
                        except Exception:
                            temp_value = float(os.environ.get('LLM_TEMPERATURE', 0.2))
                            max_tokens_value = int(os.environ.get('LLM_MAX_TOKENS', 16000))
                        
                        schema_name = 'JSON Schema'
                        if isinstance(response_schema, dict):
                            schema_name = 'JSON Schema'
                        elif PYDANTIC_AVAILABLE and hasattr(response_schema, '__name__'):
                            schema_name = response_schema.__name__
                        
                        print(f"🔷 구조화된 출력 사용: {schema_name}")
                        
                        # Context Caching 지원 (긴 컨텍스트가 있고 재사용 가능한 경우)
                        use_context_caching = False
                        if pdf_text and len(pdf_text) > 50000:  # 50,000자 이상일 때 캐싱 고려
                            try:
                                import hashlib
                                cache_key = hashlib.md5(pdf_text.encode()).hexdigest()
                                use_context_caching = True
                                print(f"💾 Context Caching 활성화: 긴 문서 ({len(pdf_text):,}자)")
                            except Exception:
                                pass
                        
                        # LiteLLM 호출
                        call_kwargs = {
                            "model": litellm_model,
                            "messages": [{"role": "user", "content": enhanced_prompt}],
                            "api_key": api_key,
                            "extra_body": structured_output_config,
                            "temperature": temp_value,
                            "max_tokens": max_tokens_value
                        }
                        
                        # Context Caching 활성화
                        if use_context_caching:
                            call_kwargs["caching"] = True
                        
                        response = litellm.completion(**call_kwargs)
                        
                        # 응답 파싱
                        response_text = response.choices[0].message.content
                        parsed_response = self._parse_structured_response(response_text, response_schema)
                        
                        return {
                            "success": True,
                            "analysis": parsed_response if PYDANTIC_AVAILABLE and isinstance(parsed_response, BaseModel) else response_text,
                            "parsed_data": parsed_response,
                            "model": self._get_current_model_info(" (Structured Output)"),
                            "method": f"Structured Output + {signature_class.__name__}",
                            "block_id": block_id
                        }
                    except Exception as e:
                        print(f"⚠️ 구조화된 출력 사용 실패, 기존 DSPy 방식으로 폴백: {e}")
                        # 폴백: 기존 DSPy 방식 사용
            
            # DSPy Predict 사용 (블록별 특화 signature 포함)
            result = dspy.Predict(signature_class)(input=enhanced_prompt)
            
            return {
                "success": True,
                "analysis": result.output,
                "model": self._get_current_model_info(" (DSPy)"),
                "method": f"DSPy + {signature_class.__name__}",
                "block_id": block_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": self._get_current_model_info(" (DSPy)"),
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
            
            with self._lm_context():
                result = dspy.Predict(AnalysisQualityValidator)(
                    analysis_result=validation_prompt,
                    validation_criteria=str(criteria_info['criteria'])
                )
            
            return {
                "success": True,
                "validation": result.output,
                "block_type": block_type,
                "criteria_info": criteria_info,
                "model": self._get_current_model_info(" (DSPy)"),
                "method": "DSPy + Enhanced AnalysisQualityValidator"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "block_type": block_type,
                "model": self._get_current_model_info(" (DSPy)"),
                "method": "DSPy + AnalysisQualityValidator"
            }
    
    def enhanced_analyze_with_validation(self, project_info, pdf_text, block_type="general"):
        """검증이 포함된 향상된 분석"""
        try:
            # 분석 수행
            analysis_result = self.analyze_project(project_info, pdf_text)
            
            if not analysis_result["success"]:
                return analysis_result
            
            # 결과 반환
            return {
                "success": True,
                "analysis": analysis_result["analysis"],
                "model": analysis_result["model"],
                "method": analysis_result["method"],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": self._get_current_model_info(" (DSPy)"),
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
    
    def initialize_cot_session(self, project_info: Dict[str, Any], pdf_text: str, total_blocks: int) -> Dict[str, Any]:
        """단계별 CoT 세션 컨텍스트를 초기화합니다."""
        return {
            "project_info": project_info,
            "pdf_text": pdf_text or "",
            "previous_results": {},
            "cot_history": [],
            "total_blocks": total_blocks
        }

    def run_cot_step(
        self,
        block_id: str,
        block_info: Dict[str, Any],
        cot_session: Dict[str, Any],
        progress_callback=None,
        step_index: Optional[int] = None,
        feedback: Optional[str] = None,
        feedback_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """단일 블록에 대한 CoT 분석을 실행하고 세션 컨텍스트를 갱신합니다.

        Args:
            block_id: 블록 ID
            block_info: 블록 정보
            cot_session: CoT 세션 컨텍스트
            progress_callback: 진행 콜백 함수
            step_index: 현재 단계 인덱스
            feedback: 피드백 텍스트
            feedback_type: 피드백 유형 (perspective_shift, constraint_addition 등)
        """
        try:
            print(f"[DEBUG] run_cot_step 시작: block_id={block_id}")
            print(f"[DEBUG] cot_session previous_results keys: {list(cot_session.get('previous_results', {}).keys())}")
            current_step = step_index if step_index is not None else len(cot_session["previous_results"]) + 1
            print(f"[DEBUG] current_step={current_step}")
            context_for_current_block = self._build_cot_context(
                cot_session,
                block_info,
                current_step,
                feedback_notes=feedback,
                feedback_type=feedback_type
            )
            project_info = cot_session.get("project_info")
            
            # 최적화된 thinking_budget 계산
            current_provider = get_current_provider()
            provider_config = PROVIDER_CONFIG.get(current_provider, {})
            model_name = provider_config.get('model', '')
            optimal_thinking_budget = self._get_optimal_thinking_budget(block_id, block_info, model_name)
            
            # 최적화된 temperature 계산
            optimal_temperature = self._get_optimal_temperature(block_id, block_info)
            
            print(f"[DEBUG] _analyze_block_with_cot_context 호출 시작...")
            import time
            start_time = time.time()

            result = self._analyze_block_with_cot_context(
                context_for_current_block,
                block_info,
                block_id,
                project_info,
                thinking_budget=optimal_thinking_budget,
                temperature=optimal_temperature,
                enable_streaming=True,  # CoT 분석에서는 스트리밍 활성화
                progress_callback=progress_callback
            )

            elapsed_time = time.time() - start_time
            print(f"[DEBUG] _analyze_block_with_cot_context 완료. 소요시간: {elapsed_time:.2f}초")
            print(f"[DEBUG] result success: {result.get('success')}, method: {result.get('method')}")

            if not result.get("success"):
                return result

            key_insights = self._extract_key_insights(result['analysis'])
            cot_session["previous_results"][block_id] = result['analysis']
            cot_session["cot_history"] = [
                entry for entry in cot_session["cot_history"] if entry.get('block_id') != block_id
            ]
            cot_session["cot_history"].append({
                "block_id": block_id,
                "block_name": block_info.get('name', 'Unknown'),
                "step": current_step,
                "key_insights": key_insights
            })
            cot_session["cot_history"].sort(key=lambda entry: entry.get('step', 0))

            if progress_callback:
                block_name = block_info.get('name', block_id)
                progress_callback(f"✅ {block_name} 블록 분석 완료")

            return {
                "success": True,
                "analysis": result['analysis'],
                "cot_session": cot_session,
                "key_insights": key_insights,
                "feedback": feedback,
                "model": result.get("model"),
                "method": result.get("method"),
                "all_citations": result.get("all_citations", [])
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": self._get_current_model_info(" (DSPy)"),
                "method": "Block Chain of Thought Analysis"
            }

    def analyze_blocks_with_cot(self, selected_blocks, project_info, pdf_text, block_infos, progress_callback=None):
        """블록 간 Chain of Thought 분석"""
        try:
            cumulative_context = self.initialize_cot_session(project_info, pdf_text, len(selected_blocks))
            
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
                    print(f"[X] 블록 정보를 찾을 수 없습니다: {block_id}")
                    if progress_callback:
                        progress_callback(f"[X] 블록 정보를 찾을 수 없습니다: {block_id}")
                    continue
                
                step_result = self.run_cot_step(
                    block_id,
                    block_info,
                    cumulative_context,
                    progress_callback=progress_callback,
                    step_index=i + 1
                )
                
                if step_result.get('success'):
                    analysis_results[block_id] = step_result['analysis']
                    cumulative_context = step_result['cot_session']
                    print(f"✅ {block_id} 블록 완료")
                else:
                    print(f"[X] {block_id} 블록 실패: {step_result.get('error', '알 수 없는 오류')}")
                    if progress_callback:
                        progress_callback(f"[X] {block_name} 블록 실패: {step_result.get('error', '알 수 없는 오류')}")
            
            print("🎉 모든 블록 분석 완료!")
            if progress_callback:
                progress_callback("🎉 모든 블록 분석 완료!")
            
            return {
                "success": True,
                "analysis_results": analysis_results,
                "cot_history": cumulative_context["cot_history"],
                "model": self._get_current_model_info(" (DSPy + Block CoT)"),
                "method": "Block Chain of Thought Analysis"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": self._get_current_model_info(" (DSPy)"),
                "method": "Block Chain of Thought Analysis"
            }
    
    def _build_cot_context(self, cumulative_context, block_info, current_step, feedback_notes: Optional[str] = None, feedback_type: Optional[str] = None):
        """현재 블록을 위한 CoT 컨텍스트 구성

        Args:
            cumulative_context: 누적 컨텍스트
            block_info: 블록 정보
            current_step: 현재 단계
            feedback_notes: 피드백 텍스트
            feedback_type: 피드백 유형 (perspective_shift, constraint_addition 등)
        """

        # 이전 블록들의 핵심 인사이트 요약
        previous_insights_summary = ""
        if cumulative_context["previous_results"]:
            previous_insights_summary = "\n### 🔗 이전 블록들의 핵심 인사이트:\n"

            for i, history_item in enumerate(cumulative_context["cot_history"]):
                previous_insights_summary += f"""
**{i+1}단계 - {history_item['block_name']}:**
{history_item['key_insights'][:300]}...

"""

        project_info = cumulative_context.get('project_info', {})

        summary_section = ""
        if isinstance(project_info, dict):
            preprocessed_summary = project_info.get('preprocessed_summary')
            preprocessing_meta = project_info.get('preprocessing_meta', {})
            if preprocessed_summary:
                summary_section += "\n### 🧾 정제된 요약 컨텍스트\n"
                summary_section += preprocessed_summary.strip() + "\n"
            if isinstance(preprocessing_meta, dict) and preprocessing_meta:
                stats_parts = []
                original_chars = preprocessing_meta.get('original_chars')
                processed_chars = preprocessing_meta.get('processed_chars')
                if original_chars is not None and processed_chars is not None:
                    stats_parts.append(f"{original_chars}자 → {processed_chars}자")
                keyword_total = preprocessing_meta.get('keyword_total')
                if keyword_total:
                    stats_parts.append(f"핵심 키워드 {keyword_total}개")
                if stats_parts:
                    summary_section += "\n**전처리 통계:** " + ", ".join(stats_parts) + "\n"

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

        # 사용자 피드백 섹션 구성 (피드백 고도화 적용)
        feedback_section = ""
        if feedback_notes:
            # 피드백 의도 분석
            feedback_intent = parse_feedback_intent(feedback_notes, feedback_type)

            # 이전 분석 결과 가져오기
            block_id = block_info.get('id', '')
            previous_result = cumulative_context.get('previous_results', {}).get(block_id, '')

            # 컨텍스트 인식 피드백 프롬프트 생성
            feedback_section = build_contextual_feedback_prompt(
                feedback_intent,
                previous_result,
                block_info
            )

        # 현재 블록을 위한 특별한 컨텍스트 구성
        cot_context = f"""
## 🔗 블록 간 Chain of Thought 분석 컨텍스트

### 📊 분석 진행 상황
- 현재 단계: {current_step}/{cumulative_context['total_blocks']}
- 완료된 블록: {len(cumulative_context['previous_results'])}개
- 남은 블록: {cumulative_context['total_blocks'] - current_step + 1}개

{previous_insights_summary}
{summary_section}

### 🎯 현재 블록 정보
- 블록명: {block_info.get('name', 'Unknown')}
- 블록 설명: {block_info.get('description', 'N/A')}

### 📄 원본 프로젝트 정보
{project_info_text}

### 📄 원본 문서 내용
{cumulative_context['pdf_text'][:3000] if cumulative_context['pdf_text'] else 'PDF 문서가 없습니다.'}

{feedback_section}

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
    
    def _format_prompt_template(self, block_info, cot_context, pdf_text: str = ""):
        """프롬프트 템플릿의 플레이스홀더를 실제 값으로 치환"""
        try:
            # 실제 PDF 텍스트 사용 (cot_context에서 추출하거나 직접 전달받은 값)
            if not pdf_text:
                # cot_context에서 PDF 텍스트 추출 시도
                if "### 📄 원본 문서 내용" in cot_context:
                    pdf_start = cot_context.find("### 📄 원본 문서 내용") + len("### 📄 원본 문서 내용")
                    pdf_end = cot_context.find("\n\n", pdf_start)
                    if pdf_end > pdf_start:
                        pdf_text = cot_context[pdf_start:pdf_end].strip()
            
            # PDF 텍스트가 없으면 빈 문자열 사용
            if not pdf_text:
                pdf_text = ""
            
            # 블록의 프롬프트 생성 (실제 PDF 텍스트 포함)
            formatted_prompt = process_prompt(block_info, pdf_text)
            
            # 디버깅: 블록 내용이 제대로 포함되었는지 확인
            print(f"🔍 블록 프롬프트 생성 확인:")
            print(f"  - 블록 ID: {block_info.get('id', 'unknown')}")
            print(f"  - 블록명: {block_info.get('name', 'unknown')}")
            if 'role' in block_info:
                print(f"  - 역할(Role): {block_info.get('role', '')[:50]}...")
            if 'instructions' in block_info:
                print(f"  - 지시(Instructions): {block_info.get('instructions', '')[:50]}...")
            if 'steps' in block_info:
                print(f"  - 단계 수: {len(block_info.get('steps', []))}개")
            print(f"  - 생성된 프롬프트 길이: {len(formatted_prompt)}자")
            
            return formatted_prompt
        except Exception as e:
            print(f"[X] 프롬프트 템플릿 포맷팅 오류: {e}")
            return UNIFIED_PROMPT_TEMPLATE.replace("{pdf_text}", pdf_text if pdf_text else "")
    
    def _analyze_block_with_cot_context(self, cot_context, block_info, block_id, project_info=None, thinking_budget: Optional[int] = None, temperature: Optional[float] = None, enable_streaming: bool = False, progress_callback=None, use_pdf_direct: bool = True):
        """CoT 컨텍스트를 포함한 블록 분석"""
        try:
            # PDF 직접 전달 시도 (옵션이 활성화되고 PDF가 있는 경우)
            if use_pdf_direct:
                pdf_bytes, pdf_path, file_size = self._extract_pdf_data(project_info)
                if pdf_bytes is not None:
                    print(f"📄 PDF 직접 전달 모드 사용: {file_size} bytes")
                    # PDF 직접 전달 방식 사용
                    return self._analyze_block_with_pdf_direct_wrapper(
                        cot_context, block_info, block_id, project_info,
                        pdf_bytes, pdf_path, thinking_budget, temperature,
                        enable_streaming, progress_callback
                    )
            
            # 기존 방식: PDF 텍스트 추출
            pdf_text = ""
            if isinstance(project_info, dict):
                pdf_text = project_info.get('file_text', '') or project_info.get('pdf_text', '')
            
            # 최적화된 thinking_budget 계산 (제공되지 않은 경우)
            if thinking_budget is None:
                current_provider = get_current_provider()
                provider_config = PROVIDER_CONFIG.get(current_provider, {})
                model_name = provider_config.get('model', '')
                thinking_budget = self._get_optimal_thinking_budget(block_id, block_info, model_name)
                if thinking_budget:
                    print(f"🧠 블록별 최적화된 Thinking Budget: {thinking_budget} (블록: {block_id})")
            
            # 최적화된 temperature 계산 (제공되지 않은 경우)
            if temperature is None:
                temperature = self._get_optimal_temperature(block_id, block_info)
                print(f"🌡️ 블록별 최적화된 Temperature: {temperature:.2f} (블록: {block_id})")
            
            # 프롬프트 템플릿의 플레이스홀더를 실제 값으로 치환 (실제 PDF 텍스트 전달)
            formatted_prompt = self._format_prompt_template(block_info, cot_context, pdf_text)
            
            # 웹 검색 수행 (특정 블록에 대해서만)
            web_search_context = ""
            if block_id and project_info:
                try:
                    web_search_context = get_web_search_context(block_id, project_info, "")
                    if web_search_context:
                        print(f"🌐 웹 검색 결과 수집 완료 (CoT): {block_id}")
                except Exception as e:
                    print(f"⚠️ 웹 검색 오류 (계속 진행): {e}")
            
            # 문서 기반 추론 강조 지시사항 추가
            document_based_instruction = f"""

## 📄 문서 기반 분석 필수 지시사항

**⚠️ 매우 중요**: 아래 지시사항을 반드시 준수하세요.

### 1. 문서 내용 기반 추론 필수
- **위에 제공된 문서 내용을 정확히 읽고 이해한 후 분석하세요**
- **문서에 명시적으로 언급된 모든 사실, 수치, 요구사항을 추출하고 분석에 활용하세요**
- **일반적인 템플릿이나 일반론적인 내용이 아닌, 이 특정 프로젝트 문서의 실제 내용을 기반으로 분석하세요**

### 2. 문서 인용 및 근거 제시 필수
- **분석 결과의 모든 주요 주장은 문서의 구체적인 내용을 인용하여 뒷받침하세요**
- **예시**: "문서에 '대지면적 5,000㎡'라고 명시되어 있어..." 형식으로 근거를 제시하세요
- **수치나 사실을 제시할 때는 반드시 문서의 출처를 명시하세요**

### 3. 문서에 없는 내용은 생성하지 말 것
- **문서에 명시되지 않은 내용은 추측하지 마세요**
- **정보가 없는 경우 '문서에 명시되지 않음' 또는 '추가 확인 필요'로 표시하세요**
- **일반적인 건축 프로젝트의 일반론적인 내용을 나열하지 마세요**

### 4. 문서 내용의 구체적 활용
- **문서에서 추출한 구체적인 수치, 명칭, 위치, 규모 등을 분석에 반드시 포함하세요**
- **문서의 맥락과 배경을 이해하고, 이를 바탕으로 심층적인 추론을 수행하세요**
- **문서의 암시적 의미나 연관된 요구사항을 추론하여 분석을 풍부하게 만들되, 추론의 근거를 명확히 제시하세요**

**위 지시사항을 준수하지 않으면 분석이 반복되거나 일반론적일 수 있습니다. 반드시 위 문서 내용을 중심으로 분석하세요.**
"""
            
            # 웹 검색 결과를 프롬프트에 추가
            if web_search_context:
                formatted_prompt = f"""{formatted_prompt}

{web_search_context}

**중요**: 위 웹 검색 결과를 참고하여 최신 정보와 시장 동향을 반영한 분석을 수행해주세요. 단, 웹 검색 결과는 문서 내용을 보완하는 역할이며, 분석의 주 근거는 반드시 위에 제공된 문서 내용이어야 합니다. 웹 검색 결과에서 얻은 정보는 반드시 출처를 명시하고, 문서 내용과 교차 검증하여 사용하세요.

{document_based_instruction}
"""
            else:
                # 웹 검색 결과가 없어도 문서 기반 분석 강조
                formatted_prompt = f"""{formatted_prompt}{document_based_instruction}"""
            
            # 확장 사고 지시사항 추가 (모든 블록에 기본 적용)
            # 블록 프롬프트에 이미 Chain of Thought 지시사항이 포함되어 있는 블록 목록
            # (이 블록들은 중복 방지를 위해 시스템 레벨 지시사항을 추가하지 않음)
            blocks_with_builtin_cot = ['phase1_facility_program']
            
            # 모든 블록에 기본적으로 확장 사고 지시사항 적용 (중복 방지 제외)
            extended_thinking_note = ""
            if block_id and block_id not in blocks_with_builtin_cot:
                # 시스템 레벨 확장 사고 템플릿 사용
                extended_thinking_note = self._get_extended_thinking_template()
            
            # CoT 컨텍스트와 블록 프롬프트 결합
            # 중요: 블록의 프롬프트(formatted_prompt)가 주요 분석 방향을 결정하므로 명확하게 포함
            # 캐시 무효화를 위한 고유 ID 생성
            import uuid
            cache_buster = str(uuid.uuid4())[:8]

            enhanced_prompt = f"""
{cot_context}

## 🎯 블록별 분석 지시사항 (핵심)

**아래 블록의 구체적인 역할, 지시사항, 단계를 정확히 따라 분석을 수행하세요.**
**이 블록의 내용이 이번 분석의 주요 방향과 목표를 결정합니다.**

{formatted_prompt}{extended_thinking_note}

{self._get_output_format_template()}

<!-- analysis_id: {cache_buster} -->
"""
            
            # 블록 ID에 따라 적절한 Signature 선택 (동적 생성)
            signature_map = self._build_signature_map()
            
            signature_class = signature_map.get(block_id, SimpleAnalysisSignature)
            
            # System Instruction 생성
            system_instruction = self._build_system_instruction(block_info)
            
            # Thinking Budget과 Temperature가 설정된 경우 LM에 적용
            lm_context = self._lm_context_with_system_instruction(system_instruction)
            if thinking_budget is not None or temperature is not None:
                # Thinking budget과 temperature를 LM에 적용하기 위해 별도 컨텍스트 사용
                lm_context = self._lm_context_with_params(
                    thinking_budget=thinking_budget,
                    temperature=temperature,
                    system_instruction=system_instruction
                )
            
            # Streaming이 활성화된 경우 streamify 사용
            if enable_streaming and progress_callback:
                try:
                    # DSPy streamify를 사용하여 스트리밍
                    stream_predict = dspy.streamify(dspy.Predict(signature_class))
                    
                    with lm_context:
                        # 스트리밍 처리 (동기 방식으로 변환)
                        accumulated_text = ""
                        final_result = None
                        
                        try:
                            # streamify는 async generator를 반환하므로 동기적으로 처리
                            import asyncio
                            
                            async def collect_stream():
                                nonlocal accumulated_text, final_result
                                async for chunk in stream_predict(input=enhanced_prompt):
                                    if isinstance(chunk, dspy.Prediction):
                                        # 최종 결과
                                        final_result = chunk
                                        if progress_callback:
                                            progress_callback(f"✅ 분석 완료")
                                        break
                                    elif hasattr(chunk, 'text') and chunk.text:
                                        # 스트리밍 청크
                                        accumulated_text += chunk.text
                                        if progress_callback and len(accumulated_text) % 100 == 0:  # 100자마다 업데이트
                                            progress_callback(f"📝 분석 중... ({len(accumulated_text)}자)")
                                    elif isinstance(chunk, str):
                                        accumulated_text += chunk
                                        if progress_callback and len(accumulated_text) % 100 == 0:
                                            progress_callback(f"📝 분석 중... ({len(accumulated_text)}자)")
                                
                                # 최종 결과가 없으면 accumulated_text 사용
                                if final_result is None:
                                    class StreamResult:
                                        def __init__(self, output):
                                            self.output = output
                                    final_result = StreamResult(accumulated_text)
                            
                            # 이벤트 루프 실행
                            # Streamlit 환경에서는 이미 실행 중인 루프가 있을 수 있으므로
                            # 먼저 확인하고, 실행 중이면 일반 모드로 전환
                            try:
                                # 실행 중인 루프가 있는지 확인
                                asyncio.get_running_loop()
                                # 실행 중인 루프가 있으면 일반 모드로 전환
                                raise RuntimeError("Event loop already running")
                            except RuntimeError:
                                # 실행 중인 루프가 없는 경우에만 스트리밍 시도
                                loop = None
                                try:
                                    try:
                                        loop = asyncio.get_event_loop()
                                        if loop.is_running():
                                            raise RuntimeError("Event loop already running")
                                    except RuntimeError:
                                        # 이벤트 루프가 없거나 실행 중인 경우 새로 생성
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                    
                                    # 이벤트 루프 실행
                                    if loop and not loop.is_running():
                                        loop.run_until_complete(collect_stream())
                                    else:
                                        raise RuntimeError("Event loop already running")
                                finally:
                                    # 이벤트 루프 정리 (새로 만든 경우에만)
                                    if loop:
                                        try:
                                            if not loop.is_running():
                                                # 보류 중인 태스크 정리
                                                try:
                                                    pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                                                    if pending:
                                                        for task in pending:
                                                            if not task.done():
                                                                task.cancel()
                                                        # 취소된 태스크들을 기다림 (타임아웃 설정)
                                                        try:
                                                            loop.run_until_complete(asyncio.wait_for(
                                                                asyncio.gather(*pending, return_exceptions=True),
                                                                timeout=1.0
                                                            ))
                                                        except (asyncio.TimeoutError, Exception):
                                                            pass
                                                except Exception:
                                                    pass
                                                # 루프 닫기
                                                try:
                                                    loop.close()
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass
                            
                            result = final_result
                        except (RuntimeError, AttributeError) as stream_error:
                            # 스트리밍이 불가능한 환경 (예: Streamlit의 실행 중인 이벤트 루프)
                            print(f"⚠️ 스트리밍 환경 제한, 일반 모드로 전환: {stream_error}")
                            if progress_callback:
                                progress_callback("📊 분석 시작...")
                            # 일반 모드로 전환
                            result = dspy.Predict(signature_class)(input=enhanced_prompt)
                            if progress_callback:
                                progress_callback("✅ 분석 완료")
                except Exception as stream_error:
                    print(f"⚠️ 스트리밍 오류, 일반 모드로 전환: {stream_error}")
                    # 스트리밍 실패 시 일반 모드로 전환
                    with lm_context:
                        result = dspy.Predict(signature_class)(input=enhanced_prompt)
            else:
                # 일반 모드 (스트리밍 없음)
                with lm_context:
                    result = dspy.Predict(signature_class)(input=enhanced_prompt)
            
            return {
                "success": True,
                "analysis": result.output,
                "model": self._get_current_model_info(" (DSPy + CoT)"),
                "method": f"DSPy + {signature_class.__name__} + Block CoT",
                "block_id": block_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": self._get_current_model_info(" (DSPy)"),
                "method": f"DSPy + Block CoT",
                "block_id": block_id
            }
    
    def _get_file_search_client(self) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
        """
        File Search용 Gemini 클라이언트를 생성하고 반환합니다.
        
        Returns:
            (client, error_dict) 튜플
            - client: 성공 시 genai.Client 객체, 실패 시 None
            - error_dict: 실패 시 에러 딕셔너리, 성공 시 None
        """
        try:
            from google import genai
            
            current_provider = get_current_provider()
            api_key = get_api_key(current_provider)
            if not api_key:
                return None, {
                    "success": False,
                    "error": "GEMINI_API_KEY가 설정되지 않았습니다."
                }
            
            client = genai.Client(api_key=api_key)
            return client, None
        except Exception as e:
            return None, {
                "success": False,
                "error": f"클라이언트 생성 오류: {str(e)}"
            }
    
    def _validate_store_name(self, store_name: str) -> Optional[Dict[str, Any]]:
        """
        Store 이름 유효성 검증
        
        Args:
            store_name: 검증할 Store 이름
            
        Returns:
            유효하지 않으면 에러 딕셔너리, 유효하면 None
        """
        if not store_name or not isinstance(store_name, str):
            return {
                "success": False,
                "error": "Store 이름이 유효하지 않습니다."
            }
        
        store_name = store_name.strip()
        if not store_name:
            return {
                "success": False,
                "error": "Store 이름이 비어있습니다."
            }
        
        return None
    
    def create_file_search_store(self, display_name: str) -> Dict[str, Any]:
        """
        File Search Store 생성
        
        Args:
            display_name: Store 표시 이름
        
        Returns:
            Store 정보 딕셔너리
        """
        if not display_name or not display_name.strip():
            return {
                "success": False,
                "error": "Store 표시 이름을 입력해주세요."
            }
        
        client, error = self._get_file_search_client()
        if error:
            return error
        
        try:
            store = client.file_search_stores.create(
                config={'display_name': display_name.strip()}
            )
            
            return {
                "success": True,
                "store_name": store.name,
                "display_name": store.display_name,
                "create_time": store.create_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"File Search Store 생성 오류: {str(e)}"
            }
    
    def list_file_search_stores(self) -> Dict[str, Any]:
        """
        File Search Store 목록 조회
        
        Returns:
            Store 목록 딕셔너리
        """
        client, error = self._get_file_search_client()
        if error:
            return error
        
        try:
            stores = list(client.file_search_stores.list())
            
            return {
                "success": True,
                "stores": [
                    {
                        "name": store.name,
                        "display_name": store.display_name,
                        "create_time": store.create_time
                    }
                    for store in stores
                ]
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"File Search Store 목록 조회 오류: {str(e)}"
            }
    
    def upload_to_file_search_store(
        self,
        file_path: Union[str, bytes],
        store_name: str,
        display_name: Optional[str] = None,
        chunking_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        파일을 File Search Store에 업로드 및 인덱싱
        
        Args:
            file_path: 파일 경로 또는 바이트 데이터
            store_name: File Search Store 이름
            display_name: 파일 표시 이름
            chunking_config: Chunking 설정 (선택사항)
        
        Returns:
            업로드 결과 딕셔너리
        """
        import os
        import tempfile
        import time
        
        # Store 이름 검증
        validation_error = self._validate_store_name(store_name)
        if validation_error:
            return validation_error
        
        # 클라이언트 생성
        client, error = self._get_file_search_client()
        if error:
            return error
        
        tmp_path = None
        
        try:
            
            # Config 구성
            config = {}
            if display_name:
                config['display_name'] = display_name
            if chunking_config:
                config['chunking_config'] = chunking_config
            
            # 파일 경로 준비
            if isinstance(file_path, bytes):
                # 바이트 데이터인 경우 임시 파일로 저장
                # 업로드 완료까지 파일을 유지해야 함
                file_ext = '.pdf'  # 기본 확장자
                if display_name:
                    ext = os.path.splitext(display_name)[1]
                    if ext:
                        file_ext = ext
                
                tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
                tmp_file.write(file_path)
                tmp_path = tmp_file.name
                tmp_file.close()
                
                file_to_upload = tmp_path
            else:
                file_to_upload = file_path
            
            # 파일 존재 및 크기 확인
            if not os.path.exists(file_to_upload):
                return {
                    "success": False,
                    "error": f"파일을 찾을 수 없습니다: {file_to_upload}"
                }
            
            file_size = os.path.getsize(file_to_upload)
            if file_size == 0:
                return {
                    "success": False,
                    "error": "빈 파일은 업로드할 수 없습니다."
                }
            
            # 업로드 시작
            try:
                operation = client.file_search_stores.upload_to_file_search_store(
                    file=file_to_upload,
                    file_search_store_name=store_name,
                    config=config if config else None
                )
            except Exception as upload_error:
                error_msg = str(upload_error)
                
                # "terminated" 또는 "already" 오류 처리
                if 'terminated' in error_msg.lower() or 'already' in error_msg.lower():
                    return {
                        "success": False,
                        "error": f"업로드가 이미 종료되었거나 중단되었습니다.\n\n"
                                f"**가능한 원인:**\n"
                                f"1. 동일한 파일명의 파일이 이미 Store에 업로드되어 있습니다\n"
                                f"2. 이전 업로드가 아직 처리 중이거나 중단되었습니다\n"
                                f"3. 네트워크 문제로 업로드가 중단되었습니다\n\n"
                                f"**해결 방법:**\n"
                                f"- 파일명을 변경하여 다시 업로드하세요\n"
                                f"- 다른 Store를 사용해보세요\n"
                                f"- 잠시 후 다시 시도하세요\n\n"
                                f"상세 오류: {error_msg}"
                    }
                return {
                    "success": False,
                    "error": f"업로드 시작 실패: {error_msg}"
                }
            
            # Operation 완료 대기
            max_wait_time = 600  # 최대 10분
            start_time = time.time()
            check_interval = 2  # 2초마다 확인
            
            while not operation.done:
                if time.time() - start_time > max_wait_time:
                    return {
                        "success": False,
                        "error": "파일 인덱싱 시간이 초과되었습니다."
                    }
                
                time.sleep(check_interval)
                try:
                    operation = client.operations.get(operation)
                except Exception as op_error:
                    return {
                        "success": False,
                        "error": f"Operation 상태 확인 실패: {str(op_error)}"
                    }
            
            # Operation 결과 확인
            if hasattr(operation, 'error') and operation.error:
                error_detail = operation.error
                if isinstance(error_detail, dict):
                    error_msg = error_detail.get('message', str(error_detail))
                else:
                    error_msg = str(error_detail)
                
                return {
                    "success": False,
                    "error": f"파일 인덱싱 실패: {error_msg}"
                }
            
            return {
                "success": True,
                "operation_name": operation.name,
                "done": operation.done
            }
            
        except Exception as e:
            error_msg = str(e)
            if 'terminated' in error_msg.lower():
                return {
                    "success": False,
                    "error": f"업로드가 이미 종료되었습니다. 동일한 파일이 이미 업로드되었거나, 이전 업로드가 중단되었을 수 있습니다. 잠시 후 다시 시도하거나 다른 파일을 업로드해보세요. 상세 오류: {error_msg}"
                }
            return {
                "success": False,
                "error": f"File Search Store 업로드 오류: {error_msg}"
            }
        finally:
            # 임시 파일 정리 (업로드 완료 후)
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception as cleanup_error:
                    print(f"임시 파일 삭제 실패 (무시): {cleanup_error}")
    
    def list_files_in_store(self, store_name: str) -> Dict[str, Any]:
        """
        File Search Store 내의 파일 목록 조회
        
        Args:
            store_name: File Search Store 이름
        
        Returns:
            파일 목록 딕셔너리
        """
        # Store 이름 검증
        validation_error = self._validate_store_name(store_name)
        if validation_error:
            return validation_error
        
        # 클라이언트 생성
        client, error = self._get_file_search_client()
        if error:
            return error
        
        try:
            # Store 정보 가져오기
            store = client.file_search_stores.get(name=store_name)
            if not store:
                return {
                    "success": False,
                    "error": f"File Search Store를 찾을 수 없습니다: {store_name}"
                }
            
            store_display_name = getattr(store, 'display_name', None) or store_name
            
            # Store 객체의 files 속성 사용
            files = []
            if hasattr(store, 'files') and store.files:
                for file in store.files:
                    file_info = {
                        "name": getattr(file, 'name', str(file)),
                        "display_name": getattr(file, 'display_name', None),
                        "create_time": getattr(file, 'create_time', None),
                        "mime_type": getattr(file, 'mime_type', None),
                        "size_bytes": getattr(file, 'size_bytes', None)
                    }
                    files.append(file_info)
            
            return {
                "success": True,
                "store_name": store_name,
                "store_display_name": store_display_name,
                "files": files,
                "file_count": len(files)
            }
        except Exception as e:
            error_msg = str(e)
            # Store를 찾을 수 없는 경우 명확한 메시지
            if 'not found' in error_msg.lower() or '404' in error_msg:
                return {
                    "success": False,
                    "error": f"File Search Store를 찾을 수 없습니다: {store_name}"
                }
            return {
                "success": False,
                "error": f"Store 파일 목록 조회 오류: {error_msg}"
            }
    
    def delete_file_search_store(self, store_name: str, force: bool = True) -> Dict[str, Any]:
        """
        File Search Store 삭제
        
        Args:
            store_name: Store 이름
            force: 강제 삭제 여부
        
        Returns:
            삭제 결과 딕셔너리
        """
        validation_error = self._validate_store_name(store_name)
        if validation_error:
            return validation_error
        
        client, error = self._get_file_search_client()
        if error:
            return error
        
        try:
            client.file_search_stores.delete(
                name=store_name,
                config={'force': force} if force else None
            )
            
            return {
                "success": True,
                "message": f"File Search Store 삭제 완료: {store_name}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"File Search Store 삭제 오류: {str(e)}"
            }
    
    def _extract_location_coordinates(self, project_info: Optional[Dict[str, Any]]) -> Optional[Dict[str, float]]:
        """
        project_info에서 위치 좌표 추출
        
        우선순위:
        1. 직접 입력된 좌표 (latitude, longitude)
        2. geo_layers의 중심점
        3. location 텍스트를 Geocoding (선택사항)
        
        Returns:
            {'latitude': float, 'longitude': float} 또는 None
        """
        # 1. 직접 좌표 확인
        if isinstance(project_info, dict):
            if 'latitude' in project_info and 'longitude' in project_info:
                try:
                    return {
                        'latitude': float(project_info['latitude']),
                        'longitude': float(project_info['longitude'])
                    }
                except (ValueError, TypeError):
                    pass
        
        # 2. geo_layers 중심점 사용
        try:
            import streamlit as st
            if st.session_state.get('geo_layers'):
                # 모든 레이어의 중심점 계산
                all_coords = []
                for layer_name, layer_data in st.session_state.geo_layers.items():
                    gdf = layer_data.get('gdf')
                    if gdf is not None and len(gdf) > 0:
                        try:
                            centroid = gdf.geometry.centroid.iloc[0]
                            all_coords.append({
                                'lat': centroid.y,
                                'lon': centroid.x
                            })
                        except Exception as e:
                            print(f"⚠️ 레이어 {layer_name} 중심점 계산 오류: {e}")
                
                if all_coords:
                    # 평균 좌표 반환
                    avg_lat = sum(c['lat'] for c in all_coords) / len(all_coords)
                    avg_lon = sum(c['lon'] for c in all_coords) / len(all_coords)
                    return {
                        'latitude': avg_lat,
                        'longitude': avg_lon
                    }
        except Exception as e:
            print(f"⚠️ geo_layers 좌표 추출 오류: {e}")
        
        # 3. location 텍스트 Geocoding (선택사항, 구현 생략)
        # 필요시 Google Geocoding API 사용
        
        return None
    
    def _extract_pdf_data(self, project_info: Optional[Dict[str, Any]]) -> Tuple[Optional[bytes], Optional[str], Optional[int]]:
        """
        project_info나 session_state에서 PDF 바이트 데이터, 경로, 파일 크기 추출
        
        Returns:
            (pdf_bytes, pdf_path, file_size) 튜플
        """
        pdf_bytes = None
        pdf_path = None
        file_size = None
        
        try:
            # 1. project_info에서 직접 PDF 바이트 데이터 확인
            if isinstance(project_info, dict):
                pdf_bytes = project_info.get('pdf_bytes')
                pdf_path = project_info.get('pdf_path') or project_info.get('file_path')
            
            # 2. Streamlit session_state에서 업로드된 파일 확인
            if pdf_bytes is None:
                try:
                    import streamlit as st
                    uploaded_file = st.session_state.get('uploaded_file')
                    if uploaded_file is not None:
                        # 파일이 업로드되어 있고 PDF인 경우
                        if hasattr(uploaded_file, 'getvalue'):
                            file_bytes = uploaded_file.getvalue()
                            # PDF 시그니처 확인 (%PDF)
                            if file_bytes[:4] == b'%PDF':
                                pdf_bytes = file_bytes
                                file_size = len(file_bytes)
                                print(f"📄 Session state에서 PDF 바이트 데이터 추출: {len(pdf_bytes)} bytes")
                except Exception:
                    pass
            
            # 3. 파일 경로가 있으면 파일에서 읽기
            if pdf_bytes is None and pdf_path:
                from pathlib import Path
                pdf_path_obj = Path(pdf_path)
                if pdf_path_obj.exists():
                    with open(pdf_path_obj, 'rb') as f:
                        pdf_bytes = f.read()
                    file_size = len(pdf_bytes)
                    print(f"📄 파일 경로에서 PDF 읽기: {pdf_path} ({file_size} bytes)")
            
            return pdf_bytes, pdf_path, file_size
            
        except Exception as e:
            print(f"⚠️ PDF 데이터 추출 오류: {e}")
            return None, None, None
    
    def _analyze_block_with_pdf_direct(
        self,
        enhanced_prompt: str,
        pdf_bytes: bytes,
        pdf_path: Optional[str],
        block_info: Dict[str, Any],
        block_id: str,
        system_instruction: str,
        thinking_budget: Optional[int],
        temperature: Optional[float],
        enable_streaming: bool = False,
        progress_callback=None,
        thinking_level: Optional[str] = None,
        include_thoughts: bool = False,
        function_declarations: Optional[List[Union[Dict[str, Any], Callable]]] = None,
        function_implementations: Optional[Dict[str, Callable]] = None,
        automatic_function_calling: bool = False,
        max_function_iterations: int = 10,
        file_search_store_names: Optional[List[str]] = None,
        reference_urls: Optional[List[str]] = None,
        use_google_search: bool = False,
        use_google_maps: bool = False,
        enable_maps_widget: bool = False,
        location_coordinates: Optional[Dict[str, float]] = None,
        web_search_citations: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        PDF를 직접 Gemini API에 전달하여 분석
        
        Args:
            enhanced_prompt: 모든 텍스트 컨텍스트가 결합된 프롬프트
            pdf_bytes: PDF 바이트 데이터
            pdf_path: PDF 파일 경로 (Files API 사용 시)
            block_info: 블록 정보
            block_id: 블록 ID
            system_instruction: System Instruction
            thinking_budget: Thinking Budget
            temperature: Temperature
            enable_streaming: 스트리밍 활성화 여부
            progress_callback: 진행 상황 콜백
        
        Returns:
            분석 결과 딕셔너리
        """
        try:
            from google import genai
            from google.genai import types
            import io
            import time
            
            # API 키 가져오기
            current_provider = get_current_provider()
            api_key = get_api_key(current_provider)
            if not api_key:
                return {
                    "success": False,
                    "error": "GEMINI_API_KEY가 설정되지 않았습니다."
                }
            
            # 모델 정보 가져오기
            provider_config = PROVIDER_CONFIG.get(current_provider, {})
            model_name = provider_config.get('model', 'gemini-2.5-flash')
            clean_model = model_name.replace('models/', '').replace('model/', '')
            
            client = genai.Client(api_key=api_key)
            
            # 파일 크기에 따른 처리 방식 선택 (10MB 기준)
            FILE_SIZE_THRESHOLD = 10 * 1024 * 1024  # 10MB
            file_size = len(pdf_bytes)
            use_files_api = file_size >= FILE_SIZE_THRESHOLD
            
            # PDF Part 준비
            pdf_part = None
            if use_files_api:
                # Files API 사용 (대용량 파일)
                if pdf_path:
                    uploaded_file = client.files.upload(
                        file=pdf_path,
                        config=dict(mime_type='application/pdf')
                    )
                else:
                    # 바이트 데이터는 BytesIO로 업로드
                    pdf_io = io.BytesIO(pdf_bytes)
                    uploaded_file = client.files.upload(
                        file=pdf_io,
                        config=dict(mime_type='application/pdf')
                    )
                
                # 파일 처리 대기
                max_wait_time = 300  # 최대 5분 대기
                start_time = time.time()
                
                while uploaded_file.state == 'PROCESSING':
                    if time.time() - start_time > max_wait_time:
                        return {
                            "success": False,
                            "error": "파일 처리 시간이 초과되었습니다."
                        }
                    
                    uploaded_file = client.files.get(name=uploaded_file.name)
                    if progress_callback:
                        progress_callback(f"📤 PDF 파일 처리 중... ({uploaded_file.state})")
                    time.sleep(2)
                
                if uploaded_file.state == 'FAILED':
                    return {
                        "success": False,
                        "error": "파일 처리에 실패했습니다."
                    }
                
                # Files API로 업로드된 파일은 URI로 참조
                pdf_part = uploaded_file
                print(f"📄 Files API 사용: {uploaded_file.uri}")
            else:
                # 인라인 처리 (작은 파일)
                pdf_part = types.Part.from_bytes(
                    data=pdf_bytes,
                    mime_type='application/pdf',
                )
                print(f"📄 인라인 PDF 처리: {file_size} bytes")
            
            # Contents 구성: 텍스트 프롬프트 → PDF Part
            # URL Context를 사용하는 경우 URL을 프롬프트에 포함
            prompt_with_urls = enhanced_prompt
            if reference_urls and len(reference_urls) > 0:
                urls_text = "\n\n## 참고 URL:\n" + "\n".join([f"- {url}" for url in reference_urls])
                prompt_with_urls = enhanced_prompt + urls_text
            
            contents = [
                prompt_with_urls,
                pdf_part
            ]
            
            # Tools 구성
            tools = []
            
            # File Search tool 추가
            if file_search_store_names:
                try:
                    tools.append(types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=file_search_store_names
                        )
                    ))
                    print(f"📚 File Search 활성화: {len(file_search_store_names)}개 Store")
                except Exception as e:
                    print(f"⚠️ File Search tool 추가 오류: {e}")
            
            # URL Context tool 추가
            if reference_urls and len(reference_urls) > 0:
                try:
                    # URL은 프롬프트에 포함 (tool은 자동으로 URL 감지)
                    tools.append(types.Tool(url_context={}))
                    print(f"🔗 URL Context 활성화: {len(reference_urls)}개 URL")
                except Exception as e:
                    print(f"⚠️ URL Context tool 추가 오류: {e}")
            
            # Google Search tool 추가
            if use_google_search:
                try:
                    tools.append(types.Tool(google_search={}))
                    print(f"🌐 Google Search 활성화")
                except Exception as e:
                    print(f"⚠️ Google Search tool 추가 오류: {e}")
            
            # Google Maps tool 추가
            if use_google_maps:
                try:
                    tools.append(types.Tool(google_maps=types.GoogleMaps(enable_widget=enable_maps_widget)))
                    print(f"🗺️ Google Maps 활성화 (Widget: {enable_maps_widget})")
                except Exception as e:
                    print(f"⚠️ Google Maps tool 추가 오류: {e}")
            
            # Function declarations를 types.Tool 형식으로 변환
            if function_declarations:
                try:
                    # Python 함수를 FunctionDeclaration으로 변환
                    converted_declarations = []
                    for func_decl in function_declarations:
                        if isinstance(func_decl, dict):
                            # 딕셔너리를 FunctionDeclaration 객체로 변환
                            try:
                                func_decl_obj = types.FunctionDeclaration(**func_decl)
                                converted_declarations.append(func_decl_obj)
                            except Exception as e:
                                print(f"⚠️ 딕셔너리를 FunctionDeclaration으로 변환 실패: {e}")
                                # 딕셔너리 그대로 사용 (API가 처리)
                                converted_declarations.append(func_decl)
                        elif callable(func_decl):
                            # Google GenAI SDK의 from_callable 사용
                            try:
                                func_decl_obj = types.FunctionDeclaration.from_callable(
                                    client=client,
                                    callable=func_decl
                                )
                                converted_declarations.append(func_decl_obj)
                            except Exception as e:
                                print(f"⚠️ 함수를 FunctionDeclaration으로 변환 실패: {e}")
                                # 수동 변환 시도
                                converted_dicts = self._convert_function_declarations([func_decl])
                                for decl_dict in converted_dicts:
                                    try:
                                        func_decl_obj = types.FunctionDeclaration(**decl_dict)
                                        converted_declarations.append(func_decl_obj)
                                    except Exception:
                                        converted_declarations.append(decl_dict)
                        else:
                            print(f"⚠️ 지원하지 않는 function declaration 형식: {type(func_decl)}")
                    
                    if converted_declarations:
                        tools.append(types.Tool(function_declarations=converted_declarations))
                        print(f"🔧 Function Calling 활성화: {len(converted_declarations)}개 함수")
                except Exception as e:
                    print(f"⚠️ Function declarations 변환 오류: {e}")
            
            # GenerateContentConfig 구성
            config_dict = {}
            
            # System Instruction 추가
            if system_instruction:
                config_dict['system_instruction'] = system_instruction
            
            # Temperature 추가
            if temperature is not None:
                config_dict['temperature'] = max(0.0, min(1.0, temperature))
            
            # Thinking Config 구성
            is_thinking_model = (
                'gemini-2.5' in clean_model or 
                'gemini-3' in clean_model or
                'gemini-2.0' in clean_model
            )
            
            if is_thinking_model:
                is_gemini_3 = 'gemini-3' in clean_model
                is_gemini_3_pro = 'gemini-3-pro' in clean_model
                is_gemini_3_flash = 'gemini-3-flash' in clean_model
                is_gemini_25_pro = 'gemini-2.5-pro' in clean_model
                is_gemini_25_flash = 'gemini-2.5-flash' in clean_model or 'gemini-2.5-flash-lite' in clean_model
                
                thinking_config = {}
                
                # Gemini 3 모델: thinking_level 사용 권장
                if is_gemini_3:
                    if thinking_level:
                        # thinking_level 직접 제공
                        valid_levels = ['low', 'high']
                        if is_gemini_3_flash:
                            valid_levels.extend(['minimal', 'medium'])
                        
                        if thinking_level.lower() in valid_levels:
                            thinking_config['thinking_level'] = thinking_level.lower()
                            print(f"🧠 Thinking Level: {thinking_level.lower()} (Gemini 3)")
                        else:
                            print(f"⚠️ 잘못된 thinking_level: {thinking_level}. 기본값 사용.")
                    elif thinking_budget is not None:
                        # thinking_budget을 thinking_level로 변환 (호환성)
                        if thinking_budget <= 1024:
                            thinking_config['thinking_level'] = "low"
                        else:
                            thinking_config['thinking_level'] = "high"
                        print(f"🧠 Thinking Budget → Level 변환: {thinking_budget} → {thinking_config['thinking_level']}")
                    
                    # include_thoughts 옵션
                    if include_thoughts:
                        thinking_config['include_thoughts'] = True
                        print(f"💭 Thought summaries 활성화")
                
                # Gemini 2.5 모델: thinking_budget 사용
                elif is_gemini_25_pro:
                    if thinking_budget is not None:
                        if thinking_budget == -1:
                            # Dynamic thinking
                            thinking_config['thinking_budget'] = -1
                            print(f"🧠 Dynamic Thinking 활성화 (Gemini 2.5 Pro)")
                        elif thinking_budget > 0:
                            thinking_config['thinking_budget'] = max(128, min(32768, thinking_budget))
                            print(f"🧠 Thinking Budget: {thinking_config['thinking_budget']} (Gemini 2.5 Pro)")
                
                elif is_gemini_25_flash:
                    if thinking_budget is not None:
                        if thinking_budget == -1:
                            # Dynamic thinking
                            thinking_config['thinking_budget'] = -1
                            print(f"🧠 Dynamic Thinking 활성화 (Gemini 2.5 Flash)")
                        elif thinking_budget == 0:
                            # Thinking 비활성화
                            thinking_config['thinking_budget'] = 0
                            print(f"🧠 Thinking 비활성화 (Gemini 2.5 Flash)")
                        else:
                            thinking_config['thinking_budget'] = max(0, min(24576, thinking_budget))
                            print(f"🧠 Thinking Budget: {thinking_config['thinking_budget']} (Gemini 2.5 Flash)")
                    
                    # include_thoughts 옵션
                    if include_thoughts:
                        thinking_config['include_thoughts'] = True
                        print(f"💭 Thought summaries 활성화")
                
                if thinking_config:
                    config_dict['thinking_config'] = types.ThinkingConfig(**thinking_config)
            
            # Tool Config 구성 (Google Maps 위치 정보)
            tool_config_dict = {}
            if use_google_maps and location_coordinates:
                try:
                    tool_config_dict['retrieval_config'] = types.RetrievalConfig(
                        lat_lng=types.LatLng(
                            latitude=location_coordinates['latitude'],
                            longitude=location_coordinates['longitude']
                        )
                    )
                    print(f"🗺️ 위치 좌표 설정: ({location_coordinates['latitude']}, {location_coordinates['longitude']})")
                except Exception as e:
                    print(f"⚠️ Tool Config 설정 오류: {e}")
            
            if tool_config_dict:
                config_dict['tool_config'] = types.ToolConfig(**tool_config_dict)
            
            # Tools 추가
            if tools:
                config_dict['tools'] = tools
            
            # GenerateContentConfig 생성
            config = types.GenerateContentConfig(**config_dict) if config_dict else None
            
            # Function Calling이 있는 경우 Compositional calling 지원
            if tools and function_implementations:
                return self._handle_function_calling_with_pdf(
                    client=client,
                    model=clean_model,
                    contents=contents,
                    config=config,
                    function_implementations=function_implementations,
                    automatic_function_calling=automatic_function_calling,
                    max_iterations=max_function_iterations,
                    enable_streaming=enable_streaming,
                    progress_callback=progress_callback,
                    include_thoughts=include_thoughts,
                    provider_config=provider_config,
                    model_name=model_name,
                    block_id=block_id,
                    use_files_api=use_files_api
                )
            
            # 분석 요청
            if progress_callback:
                progress_callback("📊 PDF 직접 분석 시작...")
            
            thought_summary = ""
            analysis_text = ""
            
            if enable_streaming and progress_callback:
                # 스트리밍 모드
                response_stream = client.models.generate_content_stream(
                    model=clean_model,
                    contents=contents,
                    config=config
                )
                
                accumulated_text = ""
                accumulated_thoughts = ""
                
                for chunk in response_stream:
                    if hasattr(chunk, 'candidates') and chunk.candidates:
                        for part in chunk.candidates[0].content.parts:
                            if not part.text:
                                continue
                            
                            # Thought summaries 처리
                            if include_thoughts and hasattr(part, 'thought') and part.thought:
                                accumulated_thoughts += part.text
                                if progress_callback and len(accumulated_thoughts) % 100 == 0:
                                    progress_callback(f"💭 추론 중... ({len(accumulated_thoughts)}자)")
                            else:
                                accumulated_text += part.text
                                if progress_callback and len(accumulated_text) % 100 == 0:
                                    progress_callback(f"📝 분석 중... ({len(accumulated_text)}자)")
                
                analysis_text = accumulated_text
                thought_summary = accumulated_thoughts
                if progress_callback:
                    progress_callback("✅ 분석 완료")
            else:
                # 일반 모드
                response = client.models.generate_content(
                    model=clean_model,
                    contents=contents,
                    config=config
                )
                
                # Thought summaries와 일반 응답 분리
                if include_thoughts and hasattr(response, 'candidates') and response.candidates:
                    for part in response.candidates[0].content.parts:
                        if not part.text:
                            continue
                        
                        if hasattr(part, 'thought') and part.thought:
                            thought_summary += part.text + "\n"
                        else:
                            analysis_text += part.text
                else:
                    analysis_text = response.text
            
            result = {
                "success": True,
                "analysis": analysis_text,
                "model": f"{provider_config.get('display_name', model_name)} (PDF Direct)",
                "method": "Gemini API Direct + PDF Native",
                "block_id": block_id,
                "pdf_method": "files_api" if use_files_api else "inline"
            }
            
            # Thought summaries 추가
            if include_thoughts and thought_summary:
                result["thought_summary"] = thought_summary.strip()
            
            # Grounding metadata 추출 (Google Search)
            grounding_supports = []
            if use_google_search:
                try:
                    if enable_streaming:
                        # 스트리밍 모드에서는 마지막 chunk에서 metadata 추출
                        # (실제로는 일반 모드에서만 metadata가 완전히 제공됨)
                        pass
                    else:
                        if hasattr(response, 'candidates') and response.candidates:
                            grounding_metadata = response.candidates[0].grounding_metadata
                            if grounding_metadata:
                                # Citations 추출
                                citations = []
                                if hasattr(grounding_metadata, 'grounding_chunks'):
                                    for chunk in grounding_metadata.grounding_chunks:
                                        if hasattr(chunk, 'web'):
                                            citations.append({
                                                'uri': chunk.web.uri,
                                                'title': chunk.web.title
                                            })
                                
                                # Grounding supports 추출 (인라인 인용용)
                                if hasattr(grounding_metadata, 'grounding_supports'):
                                    for support in grounding_metadata.grounding_supports:
                                        support_dict = {}
                                        if hasattr(support, 'segment'):
                                            segment = support.segment
                                            support_dict["text"] = segment.text if hasattr(segment, 'text') else ""
                                            support_dict["start_index"] = segment.start_index if hasattr(segment, 'start_index') else 0
                                            support_dict["end_index"] = segment.end_index if hasattr(segment, 'end_index') else 0
                                        if hasattr(support, 'grounding_chunk_indices'):
                                            support_dict["chunk_indices"] = list(support.grounding_chunk_indices) if support.grounding_chunk_indices else []
                                        grounding_supports.append(support_dict)
                                
                                # 검색 쿼리 추출
                                search_queries = []
                                if hasattr(grounding_metadata, 'web_search_queries'):
                                    search_queries = list(grounding_metadata.web_search_queries)
                                
                                result['citations'] = citations
                                result['grounding_supports'] = grounding_supports
                                result['search_queries'] = search_queries
                                print(f"📚 Citations: {len(citations)}개, Grounding Supports: {len(grounding_supports)}개, 검색 쿼리: {len(search_queries)}개")
                except Exception as e:
                    print(f"⚠️ Grounding metadata 추출 오류: {e}")
            
            # URL Context metadata 추출
            if reference_urls and len(reference_urls) > 0:
                try:
                    if not enable_streaming and hasattr(response, 'candidates') and response.candidates:
                        url_context_metadata = response.candidates[0].url_context_metadata
                        if url_context_metadata:
                            url_metadata = []
                            if hasattr(url_context_metadata, 'url_metadata'):
                                for url_meta in url_context_metadata.url_metadata:
                                    url_metadata.append({
                                        'retrieved_url': url_meta.retrieved_url,
                                        'url_retrieval_status': url_meta.url_retrieval_status
                                    })
                            result['url_context_metadata'] = url_metadata
                            print(f"🔗 URL Context: {len(url_metadata)}개 URL 처리")
                except Exception as e:
                    print(f"⚠️ URL Context metadata 추출 오류: {e}")
            
            # File Search citations 추출
            if file_search_store_names:
                try:
                    if not enable_streaming and hasattr(response, 'candidates') and response.candidates:
                        grounding_metadata = response.candidates[0].grounding_metadata
                        if grounding_metadata and hasattr(grounding_metadata, 'grounding_chunks'):
                            file_citations = []
                            for chunk in grounding_metadata.grounding_chunks:
                                if hasattr(chunk, 'file'):
                                    file_citations.append({
                                        'file_uri': chunk.file.file_uri,
                                        'display_name': chunk.file.display_name
                                    })
                            if file_citations:
                                result['file_citations'] = file_citations
                                print(f"📚 File Search Citations: {len(file_citations)}개")
                except Exception as e:
                    print(f"⚠️ File Search citations 추출 오류: {e}")
            
            # Google Maps metadata 추출
            if use_google_maps:
                try:
                    if not enable_streaming and hasattr(response, 'candidates') and response.candidates:
                        grounding_metadata = response.candidates[0].grounding_metadata
                        if grounding_metadata:
                            # Maps citations 추출
                            maps_citations = []
                            if hasattr(grounding_metadata, 'grounding_chunks'):
                                for chunk in grounding_metadata.grounding_chunks:
                                    if hasattr(chunk, 'maps'):
                                        maps_citations.append({
                                            'uri': chunk.maps.uri,
                                            'title': chunk.maps.title,
                                            'place_id': chunk.maps.place_id if hasattr(chunk.maps, 'place_id') else None
                                        })
                            
                            # Widget token 추출
                            widget_token = None
                            if hasattr(grounding_metadata, 'google_maps_widget_context_token'):
                                widget_token = grounding_metadata.google_maps_widget_context_token
                            
                            if maps_citations:
                                result['maps_citations'] = maps_citations
                                print(f"🗺️ Maps Citations: {len(maps_citations)}개")
                            
                            if widget_token:
                                result['google_maps_widget_token'] = widget_token
                                print(f"🗺️ Google Maps Widget Token 추출됨")
                except Exception as e:
                    print(f"⚠️ Maps metadata 추출 오류: {e}")
            
            # 모든 citations 통합
            all_citations = []
            
            # Google Search tool citations
            if result.get('citations'):
                for cit in result['citations']:
                    cit['source_type'] = 'google_search'
                    all_citations.append(cit)
            
            # Custom Search API citations
            if web_search_citations:
                for cit in web_search_citations:
                    cit['source_type'] = 'custom_search'
                    all_citations.append(cit)
            
            # File Search citations
            if result.get('file_citations'):
                for cit in result['file_citations']:
                    cit['source_type'] = 'file_search'
                    # file_uri를 uri로 변환
                    if 'file_uri' in cit:
                        cit['uri'] = cit.pop('file_uri')
                    all_citations.append(cit)
            
            # Maps citations
            if result.get('maps_citations'):
                for cit in result['maps_citations']:
                    cit['source_type'] = 'google_maps'
                    all_citations.append(cit)
            
            # URL Context citations
            if result.get('url_context_metadata'):
                for url_meta in result['url_context_metadata']:
                    if url_meta.get('retrieved_url'):
                        all_citations.append({
                            'uri': url_meta['retrieved_url'],
                            'title': url_meta.get('retrieved_url', 'URL'),
                            'source_type': 'url_context',
                            'status': url_meta.get('url_retrieval_status', 'unknown')
                        })
            
            # 통합된 citations 저장
            if all_citations:
                result['all_citations'] = all_citations
                print(f"📚 통합 Citations: {len(all_citations)}개")
            
            # 인라인 인용 추가 (Google Search tool의 grounding supports 사용)
            if result.get('grounding_supports') and result.get('citations'):
                try:
                    from maps_grounding_helper import format_grounding_supports_for_display
                    # Google Search citations를 sources 형식으로 변환
                    sources_for_inline = []
                    for cit in result['citations']:
                        sources_for_inline.append({
                            'title': cit.get('title', 'Unknown'),
                            'uri': cit.get('uri', '')
                        })
                    
                    # 인라인 인용이 포함된 텍스트 생성
                    analysis_with_citations = format_grounding_supports_for_display(
                        text=analysis_text,
                        grounding_supports=result['grounding_supports'],
                        sources=sources_for_inline
                    )
                    
                    # 인라인 인용이 추가된 경우 결과 업데이트
                    if analysis_with_citations != analysis_text:
                        result['analysis'] = analysis_with_citations
                        result['has_inline_citations'] = True
                        print(f"📝 인라인 인용 추가됨")
                except Exception as e:
                    print(f"⚠️ 인라인 인용 추가 오류: {e}")
            
            return result
            
        except ImportError:
            return {
                "success": False,
                "error": "google-genai 패키지가 설치되지 않았습니다. pip install google-genai를 실행하세요."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"PDF 직접 전달 분석 오류: {str(e)}",
                "model": self._get_current_model_info(" (PDF Direct)"),
                "method": "PDF Direct (Failed)"
            }
    
    def _handle_function_calling_with_pdf(
        self,
        client,
        model: str,
        contents: List,
        config: Any,  # types.GenerateContentConfig
        function_implementations: Dict[str, Callable],
        automatic_function_calling: bool,
        max_iterations: int,
        enable_streaming: bool,
        progress_callback,
        include_thoughts: bool,
        provider_config: Dict,
        model_name: str,
        block_id: str,
        use_files_api: bool
    ) -> Dict[str, Any]:
        """
        PDF 직접 전달과 Function Calling을 함께 처리
        
        Compositional function calling 지원 및 Thought Signatures 처리
        """
        try:
            from google.genai import types
            
            conversation_history = contents.copy()
            iteration = 0
            function_calls_history = []
            thought_signatures = []  # Thought signatures 저장
            
            while iteration < max_iterations:
                iteration += 1
                print(f"🔄 Function calling 반복 {iteration}/{max_iterations}")
                
                if progress_callback:
                    progress_callback(f"🔄 Function calling 반복 {iteration}/{max_iterations}")
                
                # API 호출
                if enable_streaming and progress_callback:
                    response_stream = client.models.generate_content_stream(
                        model=model,
                        contents=conversation_history,
                        config=config
                    )
                    
                    # 스트리밍 응답 수집
                    response_parts = []
                    for chunk in response_stream:
                        if hasattr(chunk, 'candidates') and chunk.candidates:
                            response_parts.append(chunk)
                    
                    # 마지막 chunk에서 response 구성
                    if response_parts:
                        response = response_parts[-1]
                    else:
                        break
                else:
                    response = client.models.generate_content(
                        model=model,
                        contents=conversation_history,
                        config=config
                    )
                
                # Function calls 추출
                function_calls = []
                thought_summary = ""
                analysis_text = ""
                
                if hasattr(response, 'candidates') and response.candidates:
                    for part in response.candidates[0].content.parts:
                        # Thought summaries 처리
                        if include_thoughts and hasattr(part, 'thought') and part.thought:
                            thought_summary += part.text + "\n"
                        # Function call 처리
                        elif hasattr(part, 'function_call') and part.function_call:
                            func_call = part.function_call
                            # func_call 전체를 안전하게 처리
                            try:
                                # name 추출
                                try:
                                    func_name = func_call.name if hasattr(func_call, 'name') else str(func_call)
                                except (AttributeError, Exception) as name_error:
                                    print(f"[WARNING] func_call.name 접근 실패: {name_error}, func_call 타입: {type(func_call)}")
                                    func_name = "unknown_function"

                                # args 추출
                                try:
                                    if hasattr(func_call, 'args'):
                                        if hasattr(func_call.args, 'items'):
                                            args_value = dict(func_call.args)
                                        else:
                                            args_value = func_call.args
                                    else:
                                        args_value = {}
                                except (AttributeError, Exception) as args_error:
                                    print(f"[WARNING] func_call.args 접근 실패: {args_error}, func_call 타입: {type(func_call)}")
                                    args_value = {}

                                function_calls.append({
                                    'name': func_name,
                                    'args': args_value
                                })
                            except Exception as func_call_error:
                                print(f"[WARNING] func_call 전체 처리 실패: {func_call_error}, func_call 타입: {type(func_call)}")
                                # 실패해도 계속 진행
                            
                            # Thought signature 추출 (Gemini 3 필수)
                            if hasattr(part, 'thought_signature') and part.thought_signature:
                                thought_signatures.append({
                                    'function_call': func_call,
                                    'signature': part.thought_signature
                                })
                                print(f"🔐 Thought signature 추출: {func_call.name}")
                        # 일반 텍스트 응답
                        elif hasattr(part, 'text') and part.text:
                            analysis_text += part.text
                
                # Function calls가 없으면 최종 응답
                if not function_calls:
                    result = {
                        "success": True,
                        "analysis": analysis_text,
                        "model": f"{provider_config.get('display_name', model_name)} (PDF Direct + Function Calling)",
                        "method": "Gemini API Direct + PDF Native + Function Calling",
                        "block_id": block_id,
                        "pdf_method": "files_api" if use_files_api else "inline",
                        "function_calls": function_calls_history
                    }
                    
                    if include_thoughts and thought_summary:
                        result["thought_summary"] = thought_summary.strip()
                    
                    return result
                
                # Function calls 실행
                function_responses = []
                for func_call in function_calls:
                    function_name = func_call['name']
                    arguments = func_call.get('args', {})
                    
                    print(f"🔧 Function 호출: {function_name}({arguments})")
                    
                    if automatic_function_calling and function_name in function_implementations:
                        try:
                            # 함수 실행
                            func_result = function_implementations[function_name](**arguments)
                            function_responses.append({
                                'name': function_name,
                                'response': func_result
                            })
                            function_calls_history.append({
                                'name': function_name,
                                'args': arguments,
                                'result': func_result
                            })
                        except Exception as e:
                            print(f"⚠️ Function 실행 오류: {e}")
                            function_responses.append({
                                'name': function_name,
                                'response': {'error': str(e)}
                            })
                
                # Function responses를 conversation history에 추가
                # 1. Model response 추가 (thought signatures 포함)
                model_content_parts = []
                
                # Response에서 원본 parts 가져오기 (thought signatures 보존)
                if hasattr(response, 'candidates') and response.candidates:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            # 원본 part를 그대로 사용 (thought signature 포함)
                            model_content_parts.append(part)
                
                conversation_history.append(
                    types.Content(
                        role="model",
                        parts=model_content_parts
                    )
                )
                
                # 2. Function responses 추가
                function_response_parts = []
                for func_response in function_responses:
                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=func_response['name'],
                            response=func_response['response']
                        )
                    )
                
                if function_response_parts:
                    conversation_history.append(
                        types.Content(
                            role="user",
                            parts=function_response_parts
                        )
                    )
            
            # 최대 반복 횟수 도달
            return {
                "success": False,
                "error": f"최대 반복 횟수({max_iterations})에 도달했습니다.",
                "model": f"{provider_config.get('display_name', model_name)} (PDF Direct + Function Calling)",
                "method": "PDF Direct + Function Calling (Max Iterations)",
                "block_id": block_id,
                "function_calls": function_calls_history
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Function calling 처리 오류: {str(e)}",
                "model": f"{provider_config.get('display_name', model_name)} (PDF Direct + Function Calling)",
                "method": "PDF Direct + Function Calling (Failed)",
                "block_id": block_id
            }
    
    def _analyze_block_with_pdf_direct_wrapper(
        self,
        cot_context: str,
        block_info: Dict[str, Any],
        block_id: str,
        project_info: Optional[Dict[str, Any]],
        pdf_bytes: bytes,
        pdf_path: Optional[str],
        thinking_budget: Optional[int],
        temperature: Optional[float],
        enable_streaming: bool,
        progress_callback
    ) -> Dict[str, Any]:
        """
        PDF 직접 전달을 위한 래퍼 메서드
        모든 텍스트 컨텍스트를 결합하고 PDF와 함께 전달
        """
        try:
            # 최적화된 thinking_budget 계산 (제공되지 않은 경우)
            if thinking_budget is None:
                current_provider = get_current_provider()
                provider_config = PROVIDER_CONFIG.get(current_provider, {})
                model_name = provider_config.get('model', '')
                thinking_budget = self._get_optimal_thinking_budget(block_id, block_info, model_name)
                if thinking_budget:
                    print(f"🧠 블록별 최적화된 Thinking Budget: {thinking_budget} (블록: {block_id})")
            
            # 최적화된 temperature 계산 (제공되지 않은 경우)
            if temperature is None:
                temperature = self._get_optimal_temperature(block_id, block_info)
                print(f"🌡️ 블록별 최적화된 Temperature: {temperature:.2f} (블록: {block_id})")
            
            # PDF 텍스트는 빈 문자열로 설정 (PDF 직접 전달이므로)
            pdf_text = ""
            
            # 프롬프트 템플릿 생성 (PDF 텍스트 없이)
            formatted_prompt = self._format_prompt_template(block_info, cot_context, pdf_text)
            
            # File Search Store 이름 추출 (project_info에서)
            file_search_store_names = None
            if isinstance(project_info, dict):
                file_search_store_names = project_info.get('file_search_store_names')
                if isinstance(file_search_store_names, str):
                    file_search_store_names = [file_search_store_names]
            
            # 참고 URL 추출 (project_info에서)
            reference_urls = None
            if isinstance(project_info, dict):
                reference_urls = project_info.get('reference_urls')
                if isinstance(reference_urls, str):
                    reference_urls = [reference_urls]
                elif reference_urls and len(reference_urls) > 20:
                    reference_urls = reference_urls[:20]  # 최대 20개 제한
                    print(f"⚠️ URL 개수가 20개를 초과하여 처음 20개만 사용합니다.")
            
            # Google Search 사용 여부 결정
            # 기존 웹 검색을 Google Search tool로 대체 (옵션)
            use_google_search = False
            if block_id and project_info:
                # 블록별로 Google Search 사용 여부 결정
                # 정보 검색이 필요한 블록에서 Google Search tool 사용
                blocks_with_google_search = [
                    'phase1_candidate_evaluation',
                    'legal_analysis',
                    'feasibility_analysis',
                    'market_research_analysis',  # 시장 조사 분석
                    'business_model_development',  # 비즈니스 모델 개발
                    'revenue_model_design',  # 수익 모델 설계
                    'competitive_analysis',  # 경쟁 분석
                    'trend_analysis',  # 트렌드 분석
                    'benchmarking_analysis'  # 벤치마킹 분석
                ]
                use_google_search = block_id in blocks_with_google_search
                
                # 기존 웹 검색은 fallback으로 유지 (Google Search tool 사용 시에도 Custom Search API로 citations 수집)
                web_search_context = ""
                web_search_citations = []
                try:
                    if not use_google_search:
                        # Google Search tool을 사용하지 않는 경우 Custom Search API 사용
                        web_search_context = get_web_search_context(block_id, project_info, "")
                        if web_search_context:
                            print(f"🌐 웹 검색 결과 수집 완료 (CoT): {block_id}")
                    # Google Search tool 사용 여부와 관계없이 Custom Search API로 citations 수집
                    if WEB_SEARCH_CITATIONS_AVAILABLE and get_web_search_citations:
                        web_search_citations = get_web_search_citations(block_id, project_info, "")
                        if web_search_citations:
                            print(f"📚 Custom Search API Citations: {len(web_search_citations)}개")
                except Exception as e:
                    print(f"⚠️ 웹 검색 오류 (계속 진행): {e}")
            
            # Google Maps 사용 여부 결정
            # 위치 기반 블록에서 자동 활성화
            use_google_maps = False
            enable_maps_widget = False
            location_coordinates = None
            
            if block_id and project_info:
                # 위치 기반 블록 식별
                location_based_blocks = [
                    'phase1_site_analysis',
                    'phase1_facility_program',
                    'phase1_candidate_evaluation',
                    'transportation_analysis',
                    'facility_analysis'
                ]
                
                # Gemini 3 모델에서는 Google Maps 사용 불가
                current_provider = get_current_provider()
                provider_config = PROVIDER_CONFIG.get(current_provider, {})
                model_name = provider_config.get('model', '')
                clean_model = model_name.replace('models/', '').replace('model/', '')
                is_gemini_3 = 'gemini-3' in clean_model
                
                if block_id in location_based_blocks and not is_gemini_3:
                    use_google_maps = True
                    # 위치 좌표 추출
                    location_coordinates = self._extract_location_coordinates(project_info)
                    if location_coordinates:
                        print(f"🗺️ 위치 좌표 추출됨: ({location_coordinates['latitude']}, {location_coordinates['longitude']})")
                    else:
                        print(f"⚠️ 위치 좌표를 찾을 수 없어 Google Maps를 비활성화합니다.")
                        use_google_maps = False
            
            # 문서 기반 추론 강조 지시사항 추가 (PDF 직접 전달용)
            document_based_instruction = f"""

## 📄 PDF 문서 기반 분석 필수 지시사항

**⚠️ 매우 중요**: 아래 지시사항을 반드시 준수하세요.

### 1. PDF 문서 내용 기반 추론 필수
- **아래에 제공된 PDF 문서를 정확히 읽고 이해한 후 분석하세요**
- **PDF 문서에 명시적으로 언급된 모든 사실, 수치, 요구사항을 추출하고 분석에 활용하세요**
- **PDF의 이미지, 다이어그램, 차트, 테이블도 모두 분석에 포함하세요**
- **일반적인 템플릿이나 일반론적인 내용이 아닌, 이 특정 프로젝트 PDF 문서의 실제 내용을 기반으로 분석하세요**

### 2. PDF 문서 인용 및 근거 제시 필수
- **분석 결과의 모든 주요 주장은 PDF 문서의 구체적인 내용을 인용하여 뒷받침하세요**
- **예시**: "PDF 문서의 X페이지에 '대지면적 5,000㎡'라고 명시되어 있어..." 형식으로 근거를 제시하세요
- **수치나 사실을 제시할 때는 반드시 PDF 문서의 출처(페이지 번호 등)를 명시하세요**

### 3. PDF 문서에 없는 내용은 생성하지 말 것
- **PDF 문서에 명시되지 않은 내용은 추측하지 마세요**
- **정보가 없는 경우 'PDF 문서에 명시되지 않음' 또는 '추가 확인 필요'로 표시하세요**
- **일반적인 건축 프로젝트의 일반론적인 내용을 나열하지 마세요**

### 4. PDF 문서 내용의 구체적 활용
- **PDF 문서에서 추출한 구체적인 수치, 명칭, 위치, 규모 등을 분석에 반드시 포함하세요**
- **PDF의 레이아웃, 구조, 다이어그램, 차트를 이해하고 이를 바탕으로 심층적인 추론을 수행하세요**
- **PDF의 암시적 의미나 연관된 요구사항을 추론하여 분석을 풍부하게 만들되, 추론의 근거를 명확히 제시하세요**

**위 지시사항을 준수하지 않으면 분석이 반복되거나 일반론적일 수 있습니다. 반드시 아래 PDF 문서 내용을 중심으로 분석하세요.**
"""
            
            # 웹 검색 결과를 프롬프트에 추가
            if web_search_context:
                formatted_prompt = f"""{formatted_prompt}

{web_search_context}

**중요**: 위 웹 검색 결과를 참고하여 최신 정보와 시장 동향을 반영한 분석을 수행해주세요. 단, 웹 검색 결과는 PDF 문서 내용을 보완하는 역할이며, 분석의 주 근거는 반드시 아래에 제공된 PDF 문서 내용이어야 합니다. 웹 검색 결과에서 얻은 정보는 반드시 출처를 명시하고, PDF 문서 내용과 교차 검증하여 사용하세요.

{document_based_instruction}
"""
            else:
                formatted_prompt = f"""{formatted_prompt}{document_based_instruction}"""
            
            # 확장 사고 지시사항 추가
            blocks_with_builtin_cot = ['phase1_facility_program']
            extended_thinking_note = ""
            if block_id and block_id not in blocks_with_builtin_cot:
                extended_thinking_note = self._get_extended_thinking_template()
            
            # CoT 컨텍스트와 블록 프롬프트 결합
            enhanced_prompt = f"""
{cot_context}

## 🎯 블록별 분석 지시사항 (핵심)

**아래 블록의 구체적인 역할, 지시사항, 단계를 정확히 따라 분석을 수행하세요.**
**이 블록의 내용이 이번 분석의 주요 방향과 목표를 결정합니다.**

{formatted_prompt}{extended_thinking_note}

{self._get_output_format_template()}
"""
            
            # System Instruction 생성
            system_instruction = self._build_system_instruction(block_info)
            
            # PDF 직접 전달 분석 실행
            return self._analyze_block_with_pdf_direct(
                enhanced_prompt=enhanced_prompt,
                pdf_bytes=pdf_bytes,
                pdf_path=pdf_path,
                block_info=block_info,
                block_id=block_id,
                system_instruction=system_instruction,
                thinking_budget=thinking_budget,
                temperature=temperature,
                enable_streaming=enable_streaming,
                progress_callback=progress_callback,
                thinking_level=None,  # 기본값, 필요시 추가 가능
                include_thoughts=False,  # 기본값, 필요시 추가 가능
                file_search_store_names=file_search_store_names,
                reference_urls=reference_urls,
                use_google_search=use_google_search,
                use_google_maps=use_google_maps,
                enable_maps_widget=enable_maps_widget,
                location_coordinates=location_coordinates,
                web_search_citations=web_search_citations
            )
            
        except Exception as e:
            print(f"⚠️ PDF 직접 전달 래퍼 오류: {e}")
            # 폴백: 기존 텍스트 추출 방식으로 전환
            return self._analyze_block_with_cot_context(
                cot_context, block_info, block_id, project_info,
                thinking_budget, temperature, enable_streaming, progress_callback,
                use_pdf_direct=False  # 재귀 방지
            )
    
    def _build_system_instruction(self, block_info: Dict[str, Any]) -> str:
        """블록 정보를 기반으로 System Instruction 생성"""
        role = block_info.get('role', '건축 프로젝트 분석 전문가')
        instructions = block_info.get('instructions', '')
        end_goal = block_info.get('end_goal', '')
        
        system_instruction = f"""당신은 {role}입니다.

{instructions}

최종 목표: {end_goal}

다음 원칙을 반드시 따라주세요:
1. 문서에 명시된 사실과 수치를 정확히 인용하세요
2. 추론 과정을 명확히 제시하세요 (Chain of Thought 방식)
3. 구체적인 수치, 단위, 산정 근거를 포함하세요
4. 문서에 없는 내용은 추측하지 말고 '문서에 명시되지 않음' 또는 '추가 확인 필요'로 표시하세요
5. 일반론적인 내용보다는 이 특정 프로젝트의 실제 내용을 기반으로 분석하세요
"""
        return system_instruction.strip()
    
    def _get_optimal_thinking_budget(self, block_id: str, block_info: Dict[str, Any], model_name: str = "") -> Optional[int]:
        """블록의 복잡도와 유형에 따라 최적화된 thinking_budget 계산"""
        # 블록 카테고리별 기본 thinking_budget 매핑
        THINKING_BUDGET_MAP = {
            # 기본 정보 추출: 낮은 thinking
            'basic_info': 1024,
            'phase1_data_inventory': 1024,
            
            # 요구사항 분석: 중간 thinking
            'requirements_analysis': 4096,
            'phase1_requirements_structuring': 4096,
            'accessibility_analysis': 4096,
            
            # 복잡한 분석: 높은 thinking
            'legal_analysis': 8192,
            'feasibility_analysis': 16384,
            'capacity_analysis': 16384,
            'phase1_facility_program': 8192,
            'phase1_facility_area_calculation': 8192,
            'phase1_candidate_generation': 12288,
            'phase1_candidate_evaluation': 16384,
            
            # 도시재개발 사회경제적 영향 분석: 매우 높은 thinking
            '도시재개발사회경제적영향분석': 16384,
        }
        
        # 블록 ID로 직접 매핑
        if block_id in THINKING_BUDGET_MAP:
            return THINKING_BUDGET_MAP[block_id]
        
        # 카테고리로 매핑 시도
        category = block_info.get('category', '').lower()
        if '기본' in category or '정보' in category:
            return 1024
        elif '요구사항' in category or '접근성' in category:
            return 4096
        elif '법규' in category or '법적' in category:
            return 8192
        elif '수용력' in category or '타당성' in category or '복합' in category:
            return 16384
        
        # 블록의 steps 수로 복잡도 추정
        steps = block_info.get('steps', [])
        if len(steps) <= 3:
            return 2048  # 단순한 분석
        elif len(steps) <= 5:
            return 4096  # 중간 복잡도
        elif len(steps) <= 7:
            return 8192  # 복잡한 분석
        else:
            return 12288  # 매우 복잡한 분석
        
        # 기본값: None (모델 기본값 사용)
        return None
    
    def _get_optimal_temperature(self, block_id: str, block_info: Dict[str, Any]) -> float:
        """블록 유형에 따라 최적화된 temperature 계산"""
        # 블록별 temperature 매핑
        TEMPERATURE_MAP = {
            # 사실 기반 분석: 낮은 temperature
            'basic_info': 0.1,
            'phase1_data_inventory': 0.1,
            'legal_analysis': 0.2,
            'phase1_facility_area_calculation': 0.2,
            
            # 일반 분석: 중간 temperature
            'requirements_analysis': 0.3,
            'phase1_requirements_structuring': 0.3,
            'accessibility_analysis': 0.3,
            'phase1_facility_program': 0.4,
            'phase1_facility_area_reference': 0.3,
            
            # 창의적 분석: 높은 temperature
            'phase1_candidate_generation': 0.7,
            'phase1_candidate_evaluation': 0.6,
            'feasibility_analysis': 0.5,
            'capacity_analysis': 0.5,
            '도시재개발사회경제적영향분석': 0.6,
        }
        
        # 블록 ID로 직접 매핑
        if block_id in TEMPERATURE_MAP:
            return TEMPERATURE_MAP[block_id]
        
        # 카테고리로 매핑 시도
        category = block_info.get('category', '').lower()
        name = block_info.get('name', '').lower()
        
        # 사실 기반 분석
        if any(keyword in category or keyword in name for keyword in ['기본', '정보', '법규', '법적', '계산', '수치']):
            return 0.2
        
        # 창의적 분석
        if any(keyword in category or keyword in name for keyword in ['후보', '제안', '생성', '아이디어', '창의', '대안']):
            return 0.7
        
        # 복합 분석
        if any(keyword in category or keyword in name for keyword in ['타당성', '수용력', '영향', '복합', '종합']):
            return 0.5
        
        # 기본값: 중간 temperature
        return 0.3
    
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
    
    def batch_analyze_blocks(self, projects: List[Dict[str, Any]], block_ids: List[str], 
                           block_infos: Dict[str, Dict], progress_callback=None):
        """
        여러 프로젝트에 대해 배치 분석 수행
        
        Args:
            projects: 프로젝트 정보 리스트 [{'project_info': {...}, 'pdf_text': '...'}, ...]
            block_ids: 분석할 블록 ID 리스트
            block_infos: 블록 정보 딕셔너리
            progress_callback: 진행 상황 콜백 함수 (선택사항)
        
        Returns:
            배치 분석 결과 딕셔너리
        """
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        try:
            total_tasks = len(projects) * len(block_ids)
            completed_tasks = 0
            batch_results = {}
            
            print(f"🔄 배치 분석 시작: {len(projects)}개 프로젝트 × {len(block_ids)}개 블록 = {total_tasks}개 작업")
            if progress_callback:
                progress_callback(f"🔄 배치 분석 시작: {total_tasks}개 작업")
            
            # 각 프로젝트별로 순차 처리 (병렬 처리로 변경 가능하지만, API 제한 고려)
            for project_idx, project_data in enumerate(projects):
                project_info = project_data.get('project_info', {})
                pdf_text = project_data.get('pdf_text', '')
                project_name = project_info.get('project_name', f'프로젝트 {project_idx + 1}')
                
                print(f"📊 프로젝트 {project_idx + 1}/{len(projects)}: {project_name}")
                if progress_callback:
                    progress_callback(f"📊 프로젝트 {project_idx + 1}/{len(projects)}: {project_name}")
                
                project_results = {}
                
                # 블록별로 순차 처리 (동일 프로젝트 내에서는 병렬 처리 가능)
                for block_idx, block_id in enumerate(block_ids):
                    block_name = block_infos.get(block_id, {}).get('name', block_id)
                    
                    print(f"  📋 블록 {block_idx + 1}/{len(block_ids)}: {block_name}")
                    if progress_callback:
                        progress_callback(f"  📋 블록 {block_idx + 1}/{len(block_ids)}: {block_name}")
                    
                    # 블록 정보 가져오기
                    block_info = block_infos.get(block_id)
                    if not block_info:
                        print(f"  ❌ 블록 정보를 찾을 수 없습니다: {block_id}")
                        continue
                    
                    # 블록 분석 수행
                    try:
                        # 프롬프트 포맷팅
                        formatted_prompt = self._format_prompt_template(
                            block_info, ""
                        )
                        
                        # PDF 텍스트 치환
                        if "{pdf_text}" in formatted_prompt:
                            formatted_prompt = formatted_prompt.replace(
                                "{pdf_text}", 
                                pdf_text[:4000] if pdf_text else "PDF 문서가 없습니다."
                            )
                        
                        # 웹 검색 수행
                        web_search_context = ""
                        try:
                            web_search_context = get_web_search_context(block_id, project_info, pdf_text)
                        except Exception as e:
                            print(f"  ⚠️ 웹 검색 오류 (계속 진행): {e}")
                        
                        # 확장 사고 지시사항 추가 (모든 블록에 기본 적용)
                        # 블록 프롬프트에 이미 Chain of Thought 지시사항이 포함되어 있는 블록 목록
                        # (이 블록들은 중복 방지를 위해 시스템 레벨 지시사항을 추가하지 않음)
                        blocks_with_builtin_cot = ['phase1_facility_program']
                        
                        # 모든 블록에 기본적으로 확장 사고 지시사항 적용 (중복 방지 제외)
                        extended_thinking_note = ""
                        if block_id and block_id not in blocks_with_builtin_cot:
                            # 시스템 레벨 확장 사고 템플릿 사용
                            extended_thinking_note = self._get_extended_thinking_template()
                        
                        # 최종 프롬프트 구성
                        enhanced_prompt = f"""
{formatted_prompt}
{web_search_context if web_search_context else ""}
{extended_thinking_note}

{self._get_output_format_template()}
"""
                        
                        # Signature 선택 (동적 생성)
                        signature_map = self._build_signature_map()
                        signature_class = signature_map.get(block_id, SimpleAnalysisSignature)
                        
                        # DSPy 분석 수행
                        with self._lm_context():
                            result = dspy.Predict(signature_class)(input=enhanced_prompt)
                        
                        project_results[block_id] = {
                            'success': True,
                            'analysis': result.output,
                            'block_name': block_name
                        }
                        
                        completed_tasks += 1
                        print(f"  ✅ {block_name} 완료 ({completed_tasks}/{total_tasks})")
                        if progress_callback:
                            progress = completed_tasks / total_tasks
                            progress_callback(f"  ✅ {block_name} 완료 ({completed_tasks}/{total_tasks})")
                    
                    except Exception as e:
                        print(f"  ❌ {block_name} 실패: {e}")
                        project_results[block_id] = {
                            'success': False,
                            'error': str(e),
                            'block_name': block_name
                        }
                        completed_tasks += 1
                    
                    # API 호출 제한을 피하기 위한 짧은 대기
                    time.sleep(0.5)
                
                batch_results[project_name] = project_results
            
            print(f"🎉 배치 분석 완료: {completed_tasks}/{total_tasks}개 작업 완료")
            if progress_callback:
                progress_callback(f"🎉 배치 분석 완료: {completed_tasks}/{total_tasks}개 작업 완료")
            
            return {
                "success": True,
                "batch_results": batch_results,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "model": self._get_current_model_info(" (DSPy + Batch)"),
                "method": "Batch Processing"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": self._get_current_model_info(" (DSPy)"),
                "method": "Batch Processing"
            }
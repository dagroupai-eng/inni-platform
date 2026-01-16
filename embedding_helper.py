"""
Gemini Embedding API를 사용하는 헬퍼 모듈
텍스트 임베딩 생성, 유사도 계산, 문서 검색 기능 제공
"""

import os
from typing import List, Dict, Optional, Tuple, Union
from pathlib import Path
from dotenv import load_dotenv
import numpy as np

# 환경변수 로드
try:
    load_dotenv()
except UnicodeDecodeError:
    pass

# Streamlit secrets 로드 (dspy_analyzer.py와 동일한 방식)
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

def _load_streamlit_secrets_into_env():
    """Streamlit secrets.toml 값을 환경변수로 주입"""
    secrets_path = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return
    
    try:
        with secrets_path.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return
    
    secrets_block = data.get("secrets", data)
    if not isinstance(secrets_block, dict):
        return
    
    for key, value in secrets_block.items():
        if isinstance(value, str) and not os.environ.get(key):
            os.environ[key] = value

_load_streamlit_secrets_into_env()


def get_gemini_api_key() -> Optional[str]:
    """Gemini API 키를 가져옵니다."""
    try:
        import streamlit as st
        # 1. 먼저 세션 상태에서 확인 (사용자가 웹에서 입력한 키)
        if 'user_api_key_GEMINI_API_KEY' in st.session_state and st.session_state['user_api_key_GEMINI_API_KEY']:
            return st.session_state['user_api_key_GEMINI_API_KEY']
        # 2. Streamlit secrets에서 확인 (secrets 파일이 없을 수 있으므로 안전하게 처리)
        # 3. 환경변수에서 확인
        try:
            api_key = st.secrets.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')
        except (FileNotFoundError, AttributeError, KeyError):
            api_key = os.environ.get('GEMINI_API_KEY')
    except Exception:
        api_key = os.environ.get('GEMINI_API_KEY')
    
    return api_key


def generate_embedding(
    text: str,
    task_type: Optional[str] = None,
    output_dimensionality: int = 768,
    model: str = "gemini-embedding-001"
) -> Optional[List[float]]:
    """
    단일 텍스트의 임베딩을 생성합니다.
    
    Args:
        text: 임베딩을 생성할 텍스트
        task_type: 작업 유형 (SEMANTIC_SIMILARITY, RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, 
                   QUESTION_ANSWERING, CLASSIFICATION, CLUSTERING, FACT_VERIFICATION)
        output_dimensionality: 출력 차원 (768, 1536, 3072 중 선택, 기본값: 768)
        model: 사용할 모델 (기본값: gemini-embedding-001)
    
    Returns:
        임베딩 벡터 (List[float]) 또는 None (실패 시)
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
    
    # Google GenAI SDK를 우선적으로 사용 (완전한 기능 지원)
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        config = None
        if task_type or output_dimensionality != 768:
            config = types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=output_dimensionality
            )
        
        result = client.models.embed_content(
            model=model,
            contents=text,
            config=config
        )
        
        if result.embeddings:
            return list(result.embeddings[0].values)
        return None
    
    except ImportError:
        # Google GenAI SDK가 없으면 OpenAI 호환 방식 사용 (fallback)
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            
            # 요청 파라미터 구성
            params = {
                "model": model,
                "input": text
            }
            
            # OpenAI 호환 방식에서 task_type 지원 (extra_body 사용)
            if task_type or output_dimensionality != 768:
                extra_body = {}
                if task_type:
                    extra_body["task_type"] = task_type
                if output_dimensionality != 768:
                    extra_body["output_dimensionality"] = output_dimensionality
                
                params["extra_body"] = extra_body
            
            response = client.embeddings.create(**params)
            
            embedding = response.data[0].embedding
            
            # 차원 조정이 필요한 경우 (OpenAI 호환 방식은 기본 3072 반환)
            if output_dimensionality < len(embedding):
                embedding = embedding[:output_dimensionality]
            elif output_dimensionality > len(embedding):
                # 차원 확장은 불가능하므로 경고
                print(f"경고: 요청한 차원({output_dimensionality})이 모델 출력 차원({len(embedding)})보다 큽니다.")
            
            return embedding
        
        except ImportError:
            raise ImportError(
                "임베딩 기능을 사용하려면 'google-genai' 또는 'openai' 패키지가 필요합니다.\n"
                "pip install google-genai 또는 pip install openai를 실행하세요."
            )
    
    except Exception as e:
        print(f"임베딩 생성 오류: {e}")
        return None


def generate_embeddings_batch(
    texts: List[str],
    task_type: Optional[str] = None,
    output_dimensionality: int = 768,
    model: str = "gemini-embedding-001"
) -> List[Optional[List[float]]]:
    """
    여러 텍스트의 임베딩을 배치로 생성합니다.
    
    Args:
        texts: 임베딩을 생성할 텍스트 목록
        task_type: 작업 유형
        output_dimensionality: 출력 차원
        model: 사용할 모델
    
    Returns:
        임베딩 벡터 목록 (각 항목은 List[float] 또는 None)
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
    
    # Google GenAI SDK를 우선적으로 사용 (완전한 기능 지원)
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        config = None
        if task_type or output_dimensionality != 768:
            config = types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=output_dimensionality
            )
        
        result = client.models.embed_content(
            model=model,
            contents=texts,
            config=config
        )
        
        embeddings = []
        for emb in result.embeddings:
            if emb:
                embedding = list(emb.values)
                if output_dimensionality < len(embedding):
                    embedding = embedding[:output_dimensionality]
                embeddings.append(embedding)
            else:
                embeddings.append(None)
        
        return embeddings
    
    except ImportError:
        # Google GenAI SDK가 없으면 OpenAI 호환 방식 사용 (fallback)
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            
            params = {
                "model": model,
                "input": texts
            }
            
            # OpenAI 호환 방식에서 task_type 지원 (extra_body 사용)
            if task_type or output_dimensionality != 768:
                extra_body = {}
                if task_type:
                    extra_body["task_type"] = task_type
                if output_dimensionality != 768:
                    extra_body["output_dimensionality"] = output_dimensionality
                
                params["extra_body"] = extra_body
            
            response = client.embeddings.create(**params)
            
            embeddings = []
            for data in response.data:
                embedding = data.embedding
                if output_dimensionality < len(embedding):
                    embedding = embedding[:output_dimensionality]
                embeddings.append(embedding)
            
            return embeddings
        
        except ImportError:
            raise ImportError(
                "임베딩 기능을 사용하려면 'google-genai' 또는 'openai' 패키지가 필요합니다.\n"
                "pip install google-genai 또는 pip install openai를 실행하세요."
            )
    
    except Exception as e:
        print(f"배치 임베딩 생성 오류: {e}")
        return [None] * len(texts)


def normalize_embedding(embedding: List[float]) -> np.ndarray:
    """
    임베딩 벡터를 정규화합니다 (L2 norm).
    
    Args:
        embedding: 정규화할 임베딩 벡터
    
    Returns:
        정규화된 임베딩 (numpy array)
    """
    embedding_array = np.array(embedding, dtype=np.float32)
    norm = np.linalg.norm(embedding_array)
    
    if norm == 0:
        return embedding_array
    
    return embedding_array / norm


def calculate_cosine_similarity(
    embedding1: Union[List[float], np.ndarray],
    embedding2: Union[List[float], np.ndarray]
) -> float:
    """
    두 임베딩 벡터 간의 코사인 유사도를 계산합니다.
    
    Args:
        embedding1: 첫 번째 임베딩 벡터
        embedding2: 두 번째 임베딩 벡터
    
    Returns:
        코사인 유사도 (0.0 ~ 1.0 사이의 값)
    """
    emb1 = np.array(embedding1, dtype=np.float32)
    emb2 = np.array(embedding2, dtype=np.float32)
    
    # 정규화
    emb1_norm = normalize_embedding(emb1)
    emb2_norm = normalize_embedding(emb2)
    
    # 코사인 유사도 계산 (내적)
    similarity = np.dot(emb1_norm, emb2_norm)
    
    return float(similarity)


def find_similar_documents(
    query_embedding: Union[List[float], np.ndarray],
    document_embeddings: List[Union[List[float], np.ndarray]],
    document_texts: Optional[List[str]] = None,
    top_k: int = 5
) -> List[Tuple[int, float, Optional[str]]]:
    """
    쿼리 임베딩과 유사한 문서를 검색합니다.
    
    Args:
        query_embedding: 쿼리의 임베딩 벡터
        document_embeddings: 문서들의 임베딩 벡터 목록
        document_texts: 문서 텍스트 목록 (선택사항, 반환 시 포함)
        top_k: 반환할 상위 문서 개수
    
    Returns:
        (인덱스, 유사도, 문서 텍스트) 튜플의 목록 (유사도 내림차순 정렬)
    """
    similarities = []
    
    query_emb = np.array(query_embedding, dtype=np.float32)
    query_emb_norm = normalize_embedding(query_emb)
    
    for idx, doc_embedding in enumerate(document_embeddings):
        if doc_embedding is None:
            continue
        
        similarity = calculate_cosine_similarity(query_embedding, doc_embedding)
        doc_text = document_texts[idx] if document_texts and idx < len(document_texts) else None
        similarities.append((idx, similarity, doc_text))
    
    # 유사도 기준 내림차순 정렬
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # 상위 k개 반환
    return similarities[:top_k]


def embed_documents(
    documents: List[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
    output_dimensionality: int = 768
) -> List[Optional[List[float]]]:
    """
    문서 목록을 임베딩으로 변환합니다 (RAG 시스템용).
    
    Args:
        documents: 문서 텍스트 목록
        task_type: 작업 유형 (기본값: RETRIEVAL_DOCUMENT)
        output_dimensionality: 출력 차원
    
    Returns:
        임베딩 벡터 목록
    """
    return generate_embeddings_batch(
        texts=documents,
        task_type=task_type,
        output_dimensionality=output_dimensionality
    )


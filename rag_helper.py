"""
RAG (Retrieval Augmented Generation) 시스템 구축을 위한 헬퍼 모듈
임베딩 기반 문서 검색 및 컨텍스트 구성 기능 제공
"""

from typing import List, Dict, Optional, Tuple, Union
import re
from typing import Any

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25Okapi = None

from embedding_helper import (
    generate_embedding,
    generate_embeddings_batch,
    find_similar_documents,
    embed_documents,
    normalize_embedding
)


def chunk_documents(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
    separators: List[str] = ["\n# ", "\n## ", "\n### ", "\n\n", "\n", " ", ""]
) -> List[str]:
    """
    문서 구조(헤더, 문단)를 인식하여 재귀적으로 청크를 분할합니다.
    
    Args:
        text: 분할할 텍스트
        chunk_size: 청크 목표 크기
        overlap: 청크 간 겹침 크기
        separators: 분할 시 시도할 구분자 목록 (우선순위 순)
    """
    if not text:
        return []

    # 최종 분할 결과
    final_chunks = []
    
    def _recursive_split(current_text: str, sep_indices: List[str]):
        if len(current_text) <= chunk_size:
            return [current_text]
        
        if not sep_indices:
            # 더 이상 나눌 구분자가 없으면 강제 분할
            return [current_text[i:i+chunk_size] for i in range(0, len(current_text), chunk_size - overlap)]

        separator = sep_indices[0]
        remaining_seps = sep_indices[1:]
        
        # 구분자로 분할
        if separator:
            splits = current_text.split(separator)
        else:
            splits = list(current_text)

        result = []
        current_chunk = ""
        
        for i, part in enumerate(splits):
            # 구분자 복원 (split으로 제거된 것 다시 붙임)
            if i < len(splits) - 1:
                part_with_sep = part + separator
            else:
                part_with_sep = part
                
            if len(current_chunk) + len(part_with_sep) <= chunk_size:
                current_chunk += part_with_sep
            else:
                if current_chunk:
                    result.append(current_chunk)
                
                # 새로운 part 자체가 chunk_size보다 크면 더 작은 구분자로 재귀 분할
                if len(part_with_sep) > chunk_size:
                    result.extend(_recursive_split(part_with_sep, remaining_seps))
                    # 재귀 결과의 마지막 부분은 current_chunk로 이어감 (overlap 고려 생략 - 단순화)
                    current_chunk = ""
                else:
                    current_chunk = part_with_sep
        
        if current_chunk:
            result.append(current_chunk)
            
        return result

    # 재귀 분할 실행
    chunks = _recursive_split(text, separators)
    
    # Overlap 처리 로직 (단순화된 방식)
    if overlap > 0 and len(chunks) > 1:
        processed = []
        for i in range(len(chunks)):
            if i == 0:
                processed.append(chunks[i])
            else:
                # 이전 청크의 끝부분을 가져와 앞에 붙임
                prev = chunks[i-1]
                overlap_text = prev[-overlap:] if len(prev) > overlap else prev
                processed.append(overlap_text + "\n" + chunks[i])
        chunks = processed
        
    return chunks


def embed_documents_for_rag(
    documents: List[str],
    chunk_size: int = 1000,
    overlap: int = 200,
    output_dimensionality: int = 768
) -> Tuple[List[str], List[List[float]]]:
    """
    문서들을 청크로 분할하고 임베딩으로 변환합니다 (RAG 시스템용).
    
    Args:
        documents: 문서 텍스트 목록
        chunk_size: 청크 크기
        overlap: 청크 간 겹치는 부분 크기
        output_dimensionality: 임베딩 출력 차원
    
    Returns:
        (청크 텍스트 목록, 임베딩 목록) 튜플
    """
    all_chunks = []
    chunk_to_doc = []  # 각 청크가 어느 문서에서 온 것인지 추적
    
    for doc_idx, doc in enumerate(documents):
        chunks = chunk_documents(doc, chunk_size=chunk_size, overlap=overlap)
        all_chunks.extend(chunks)
        chunk_to_doc.extend([doc_idx] * len(chunks))
    
    # 모든 청크 임베딩 생성
    embeddings = embed_documents(
        documents=all_chunks,
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=output_dimensionality
    )
    
    # None 제거
    valid_chunks = []
    valid_embeddings = []
    
    for chunk, embedding in zip(all_chunks, embeddings):
        if embedding is not None:
            valid_chunks.append(chunk)
            valid_embeddings.append(embedding)
    
    return valid_chunks, valid_embeddings


def retrieve_relevant_contexts(
    query: str,
    document_chunks: List[str],
    document_embeddings: List[List[float]],
    top_k: int = 5,
    min_similarity: float = 0.0
) -> List[Tuple[str, float]]:
    """
    쿼리와 관련된 컨텍스트를 검색합니다.
    
    Args:
        query: 검색 쿼리 텍스트
        document_chunks: 문서 청크 텍스트 목록
        document_embeddings: 문서 청크의 임베딩 목록
        top_k: 반환할 상위 컨텍스트 개수
        min_similarity: 최소 유사도 임계값 (이보다 낮으면 제외)
    
    Returns:
        (청크 텍스트, 유사도) 튜플의 목록 (유사도 내림차순 정렬)
    """
    # 쿼리 임베딩 생성
    query_embedding = generate_embedding(
        text=query,
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=len(document_embeddings[0]) if document_embeddings else 768
    )
    
    if query_embedding is None:
        return []
    
    # 유사 문서 검색
    similar_docs = find_similar_documents(
        query_embedding=query_embedding,
        document_embeddings=document_embeddings,
        document_texts=document_chunks,
        top_k=top_k * 2  # 더 많이 가져온 후 필터링
    )
    
    # 최소 유사도 필터링
    filtered_results = [
        (text, similarity)
        for _, similarity, text in similar_docs
        if text is not None and similarity >= min_similarity
    ]
    
    # 상위 k개 반환
    return filtered_results[:top_k]


def _tokenize_korean(text: str) -> List[str]:
    """
    한국어 텍스트를 BM25용 토큰 리스트로 변환한다.

    - 공백·특수문자 기준 어절 분리 (기본 토큰)
    - 3자 이상 한글 어절에서 2자 bigram 추가
      (예: "준주거지역" → ["준주거지역", "준주", "주거", "거지", "지역"])
    - 이유: 한국어 복합명사·정책명은 붙여쓰기 불일치가 많아
      bigram이 부분 키워드 매칭에 효과적임
    """
    text = re.sub(r'[^\w\s가-힣]', ' ', text)
    tokens = [t for t in text.split() if t]

    bigrams: List[str] = []
    for token in tokens:
        korean_chars = re.sub(r'[^\uAC00-\uD7A3]', '', token)
        if len(korean_chars) >= 3:
            bigrams.extend(korean_chars[i:i+2] for i in range(len(korean_chars) - 1))

    return tokens + bigrams


def _build_bm25_index(chunks: List[str]) -> Optional[Any]:
    """
    청크 리스트에서 BM25Okapi 인덱스를 생성한다.
    rank_bm25 미설치 시 None 반환.
    """
    if not BM25_AVAILABLE or not chunks:
        return None
    try:
        tokenized = [_tokenize_korean(chunk) for chunk in chunks]
        return BM25Okapi(tokenized)
    except Exception:
        return None


def hybrid_retrieve(
    query: str,
    chunks: List[str],
    embeddings: List[List[float]],
    bm25_index: Optional[Any] = None,
    top_k: int = 8,
    rrf_k: int = 60,
    min_similarity: float = 0.0
) -> List[Tuple[str, float]]:
    """
    BM25 키워드 검색 + 임베딩 의미 검색을 Reciprocal Rank Fusion(RRF)으로 결합한다.

    RRF 점수: score(d) = Σ 1 / (k + rank(d))
    - 스케일이 다른 두 점수를 순위 기반으로 합산 → 안정적
    - bm25_index가 None이면 임베딩 단독 검색으로 폴백

    Args:
        query: 검색 쿼리
        chunks: 문서 청크 텍스트 목록
        embeddings: 청크별 임베딩 목록
        bm25_index: _build_bm25_index()로 생성된 BM25Okapi 인스턴스
        top_k: 반환할 상위 결과 수
        rrf_k: RRF 상수 (기본 60, 낮을수록 상위 순위 가중치 강화)
        min_similarity: 임베딩 검색 최소 유사도

    Returns:
        (청크 텍스트, RRF 점수) 튜플 목록 (점수 내림차순)
    """
    if not chunks or not embeddings:
        return []

    # ── 임베딩 검색 순위 ─────────────────────────────────────────────────
    embed_results = retrieve_relevant_contexts(
        query=query,
        document_chunks=chunks,
        document_embeddings=embeddings,
        top_k=len(chunks),         # 전체 순위를 얻기 위해 모두 가져옴
        min_similarity=min_similarity
    )
    # (text, similarity) → {text: embed_rank}
    embed_rank: Dict[str, int] = {text: rank for rank, (text, _) in enumerate(embed_results)}

    # ── BM25 검색 순위 ─────────────────────────────────────────────────
    bm25_rank: Dict[str, int] = {}
    if bm25_index is not None and BM25_AVAILABLE:
        try:
            query_tokens = _tokenize_korean(query)
            bm25_scores = bm25_index.get_scores(query_tokens)
            # 점수 내림차순으로 인덱스 정렬 → 순위 부여
            sorted_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
            bm25_rank = {chunks[i]: rank for rank, i in enumerate(sorted_indices)}
        except Exception:
            pass  # BM25 실패 시 임베딩 단독으로 폴백

    # ── RRF 결합 ────────────────────────────────────────────────────────
    rrf_scores: Dict[str, float] = {}
    all_texts = set(embed_rank.keys()) | set(bm25_rank.keys())

    for text in all_texts:
        score = 0.0
        if text in embed_rank:
            score += 1.0 / (rrf_k + embed_rank[text])
        if text in bm25_rank:
            score += 1.0 / (rrf_k + bm25_rank[text])
        rrf_scores[text] = score

    # ── 상위 top_k 반환 ──────────────────────────────────────────────────
    sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [(text, score) for text, score in sorted_results[:top_k]]


def build_rag_prompt(
    query: str,
    relevant_contexts: List[Tuple[str, float]],
    system_message: Optional[str] = None,
    include_similarity_scores: bool = False
) -> str:
    """
    RAG 프롬프트를 구성합니다.
    
    Args:
        query: 사용자 쿼리
        relevant_contexts: 관련 컨텍스트 목록 (텍스트, 유사도) 튜플
        system_message: 시스템 메시지 (선택사항)
        include_similarity_scores: 유사도 점수를 프롬프트에 포함할지 여부
    
    Returns:
        구성된 프롬프트 문자열
    """
    prompt_parts = []
    
    if system_message:
        prompt_parts.append(f"## 시스템 지시사항\n{system_message}\n")
    
    if relevant_contexts:
        prompt_parts.append("## 참고 문서 컨텍스트\n")
        prompt_parts.append("아래는 질문과 관련된 참고 문서 내용입니다. 이 정보를 활용하여 답변해주세요.\n\n")
        
        for idx, (context, similarity) in enumerate(relevant_contexts, 1):
            prompt_parts.append(f"### 참고 문서 {idx}")
            if include_similarity_scores:
                prompt_parts.append(f"(관련도: {similarity:.3f})\n")
            prompt_parts.append(f"{context}\n\n")
    
    prompt_parts.append("## 질문\n")
    prompt_parts.append(f"{query}\n\n")
    prompt_parts.append("위 참고 문서 컨텍스트를 바탕으로 질문에 답변해주세요. 참고 문서에 없는 내용은 추측하지 마세요.")
    
    return "\n".join(prompt_parts)


def get_block_relevant_context(
    block: dict,
    rag_system: dict,
    top_k: int = 8,
    min_similarity: float = 0.0
) -> str:
    """
    블록의 description/steps/narrowing을 쿼리로 변환해 문서에서 관련 청크만 추출한다.
    RAG 시스템이 없거나 빈 경우 빈 문자열을 반환한다.

    Args:
        block: blocks.json의 블록 객체 (id, description, steps, end_goal, narrowing 포함)
        rag_system: build_rag_system_for_documents()로 생성된 RAG 시스템
        top_k: 반환할 최대 청크 수
        min_similarity: 최소 유사도 임계값

    Returns:
        관련 청크들을 구분자로 이어붙인 문자열
    """
    if not rag_system or not rag_system.get("chunks"):
        return ""

    # 블록 메타데이터에서 쿼리 생성
    query_parts = []

    description = block.get("description", "")
    if description:
        query_parts.append(description)

    end_goal = block.get("end_goal", "")
    if end_goal:
        query_parts.append(end_goal)

    steps = block.get("steps", [])
    if steps:
        query_parts.append(" ".join(steps))

    narrowing = block.get("narrowing", {})
    if narrowing:
        narrowing_texts = []
        for v in narrowing.values():
            if isinstance(v, str) and v:
                narrowing_texts.append(v)
            elif isinstance(v, list):
                narrowing_texts.extend(str(item) for item in v if item)
        if narrowing_texts:
            query_parts.append(" ".join(narrowing_texts))

    if not query_parts:
        return ""

    query = "\n".join(query_parts)

    bm25_index = rag_system.get("bm25_index")
    if bm25_index is not None:
        # 하이브리드 검색 (BM25 + 임베딩 RRF)
        contexts = hybrid_retrieve(
            query=query,
            chunks=rag_system["chunks"],
            embeddings=rag_system["embeddings"],
            bm25_index=bm25_index,
            top_k=top_k,
            min_similarity=min_similarity
        )
    else:
        # 임베딩 단독 검색 (폴백)
        contexts = retrieve_relevant_contexts(
            query=query,
            document_chunks=rag_system["chunks"],
            document_embeddings=rag_system["embeddings"],
            top_k=top_k,
            min_similarity=min_similarity
        )

    if not contexts:
        return ""

    return "\n\n---\n\n".join(chunk for chunk, _ in contexts)


def _jaccard_similarity(text1: str, text2: str) -> float:
    """두 텍스트의 Jaccard 유사도를 계산한다 (토큰 집합 기준)."""
    tokens1 = set(_tokenize_korean(text1))
    tokens2 = set(_tokenize_korean(text2))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union)


def extract_key_claims(text: str, max_claims: int = 6) -> List[str]:
    """
    분석 결과 텍스트에서 검증할 핵심 주장 문장을 추출한다.

    우선순위:
    1. 수치 / 법령명 / 지명이 포함된 문장
    2. 정책 / 전략 키워드가 있는 문장
    필터: 30자 이상
    """
    sentences = re.split(r'(?<=[.!?。])\s+|\n', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 30]

    priority: List[str] = []
    secondary: List[str] = []
    for s in sentences:
        has_number = bool(re.search(r'\d', s))
        has_proper = bool(re.search(r'[가-힣]{2,}(?:구|시|동|로|길|법|조|항|계획|지역|지구)', s))
        if has_number or has_proper:
            priority.append(s)
        else:
            secondary.append(s)

    return (priority + secondary)[:max_claims]


def verify_claim(claim: str, chunks: List[str], bm25_index: Optional[Any]) -> Dict:
    """
    단일 주장 문장의 근거를 BM25로 검색하고 Jaccard 신뢰도를 반환한다.

    반환:
        claim: 주장 문장
        evidence: 가장 유사한 원본 청크 (앞 300자)
        confidence: Jaccard 유사도 (0~1)
        is_grounded: confidence >= 0.15
    """
    if not chunks or not bm25_index or not BM25_AVAILABLE:
        return {"claim": claim, "evidence": "", "confidence": 0.0, "is_grounded": False}
    try:
        query_tokens = _tokenize_korean(claim)
        scores = bm25_index.get_scores(query_tokens)
        best_idx = int(max(range(len(scores)), key=lambda i: scores[i]))
        best_chunk = chunks[best_idx]
        confidence = _jaccard_similarity(claim, best_chunk)
    except Exception:
        return {"claim": claim, "evidence": "", "confidence": 0.0, "is_grounded": False}

    return {
        "claim": claim,
        "evidence": best_chunk[:300],
        "confidence": round(confidence, 4),
        "is_grounded": confidence >= 0.15,
    }


def verify_analysis(analysis_text: str, rag_system: dict, max_claims: int = 6) -> List[Dict]:
    """
    분석 결과 전체에서 핵심 주장을 추출하고 원본 문서 근거를 검증한다.
    BM25 인덱스가 없으면 빈 리스트를 반환한다.
    """
    if not rag_system or not rag_system.get("chunks"):
        return []
    claims = extract_key_claims(analysis_text, max_claims=max_claims)
    if not claims:
        return []
    chunks = rag_system["chunks"]
    bm25_index = rag_system.get("bm25_index")
    return [verify_claim(claim, chunks, bm25_index) for claim in claims]


def build_rag_system_for_documents(
    documents: List[str],
    chunk_size: int = 1000,
    overlap: int = 200,
    output_dimensionality: int = 768
) -> Dict:
    """
    문서 집합에 대한 RAG 시스템을 구축합니다.
    
    Args:
        documents: 문서 텍스트 목록
        chunk_size: 청크 크기
        overlap: 청크 간 겹치는 부분 크기
        output_dimensionality: 임베딩 출력 차원
    
    Returns:
        RAG 시스템 딕셔너리 (문서 청크, 임베딩 포함)
    """
    chunks, embeddings = embed_documents_for_rag(
        documents=documents,
        chunk_size=chunk_size,
        overlap=overlap,
        output_dimensionality=output_dimensionality
    )

    # BM25 인덱스 사전 구축 (rank_bm25 설치된 경우만)
    bm25_index = _build_bm25_index(chunks)

    return {
        "chunks": chunks,
        "embeddings": embeddings,
        "num_chunks": len(chunks),
        "num_documents": len(documents),
        "bm25_index": bm25_index,
        "bm25_available": bm25_index is not None
    }


def query_rag_system(
    rag_system: Dict,
    query: str,
    top_k: int = 5,
    min_similarity: float = 0.0,
    build_prompt: bool = True,
    system_message: Optional[str] = None
) -> Union[str, List[Tuple[str, float]]]:
    """
    RAG 시스템에 쿼리를 실행합니다.
    
    Args:
        rag_system: build_rag_system_for_documents로 생성된 RAG 시스템
        query: 검색 쿼리
        top_k: 반환할 상위 컨텍스트 개수
        min_similarity: 최소 유사도 임계값
        build_prompt: 프롬프트를 구성하여 반환할지 여부
        system_message: 시스템 메시지 (build_prompt=True일 때 사용)
    
    Returns:
        build_prompt=True면 프롬프트 문자열, False면 (청크, 유사도) 튜플 목록
    """
    chunks = rag_system.get("chunks", [])
    embeddings = rag_system.get("embeddings", [])
    
    if not chunks or not embeddings:
        return [] if not build_prompt else ""
    
    relevant_contexts = retrieve_relevant_contexts(
        query=query,
        document_chunks=chunks,
        document_embeddings=embeddings,
        top_k=top_k,
        min_similarity=min_similarity
    )
    
    if build_prompt:
        return build_rag_prompt(
            query=query,
            relevant_contexts=relevant_contexts,
            system_message=system_message
        )
    else:
        return relevant_contexts


"""
RAG (Retrieval Augmented Generation) 시스템 구축을 위한 헬퍼 모듈
임베딩 기반 문서 검색 및 컨텍스트 구성 기능 제공
"""

from typing import List, Dict, Optional, Tuple, Union
import re
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
    separator: str = "\n\n"
) -> List[str]:
    """
    긴 문서를 작은 청크로 분할합니다.
    
    Args:
        text: 분할할 텍스트
        chunk_size: 각 청크의 최대 크기 (문자 수)
        overlap: 청크 간 겹치는 부분의 크기 (문자 수)
        separator: 청크 분할 시 우선 사용할 구분자
    
    Returns:
        텍스트 청크 목록
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    
    # 먼저 구분자로 나누기 시도
    if separator in text:
        parts = text.split(separator)
        current_chunk = ""
        
        for part in parts:
            # 현재 청크에 추가했을 때 크기 확인
            test_chunk = current_chunk + separator + part if current_chunk else part
            
            if len(test_chunk) <= chunk_size:
                current_chunk = test_chunk
            else:
                # 현재 청크가 있으면 저장
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 새로운 part가 너무 크면 강제로 분할
                if len(part) > chunk_size:
                    # 재귀적으로 작은 부분 분할
                    sub_chunks = chunk_documents(
                        part,
                        chunk_size=chunk_size,
                        overlap=overlap,
                        separator=" "
                    )
                    chunks.extend(sub_chunks[:-1])  # 마지막은 다음 루프에서 처리
                    current_chunk = sub_chunks[-1] if sub_chunks else ""
                else:
                    current_chunk = part
        
        # 마지막 청크 추가
        if current_chunk:
            chunks.append(current_chunk)
    else:
        # 구분자가 없으면 공백으로 분할
        words = text.split()
        current_chunk = ""
        
        for word in words:
            test_chunk = current_chunk + " " + word if current_chunk else word
            
            if len(test_chunk) <= chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = word
        
        if current_chunk:
            chunks.append(current_chunk)
    
    # 오버랩 적용 (연속된 청크 간 일부 내용 겹치기)
    if overlap > 0 and len(chunks) > 1:
        overlapped_chunks = [chunks[0]]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]
            
            # 이전 청크의 마지막 부분 추출
            prev_suffix = prev_chunk[-overlap:] if len(prev_chunk) > overlap else prev_chunk
            
            # 현재 청크 앞에 이전 청크의 마지막 부분 추가
            overlapped_chunk = prev_suffix + "\n" + current_chunk
            overlapped_chunks.append(overlapped_chunk)
        
        chunks = overlapped_chunks
    
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
    
    return {
        "chunks": chunks,
        "embeddings": embeddings,
        "num_chunks": len(chunks),
        "num_documents": len(documents)
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


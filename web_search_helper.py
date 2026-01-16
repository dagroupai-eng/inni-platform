"""
웹 검색 기능을 제공하는 헬퍼 모듈
여러 검색 API를 지원하며, 검색 결과 캐싱 기능 포함
"""

import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import requests
from pathlib import Path

# 캐시 디렉토리
CACHE_DIR = Path("cache/web_search")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 캐시 유효 기간 (시간)
CACHE_EXPIRY_HOURS = 24


class WebSearchHelper:
    """웹 검색 기능을 제공하는 클래스"""
    
    def __init__(self, search_provider: str = "auto"):
        """
        Args:
            search_provider: 검색 제공자 ("duckduckgo", "serper", "google", "auto")
        """
        self.search_provider = search_provider
        self._init_api_keys()
    
    def _init_api_keys(self):
        """API 키 초기화"""
        try:
            import streamlit as st
            try:
                self.serper_api_key = st.secrets.get('SERPER_API_KEY') or os.environ.get('SERPER_API_KEY')
                self.google_api_key = st.secrets.get('GOOGLE_SEARCH_API_KEY') or os.environ.get('GOOGLE_SEARCH_API_KEY')
                self.google_cx = st.secrets.get('GOOGLE_SEARCH_CX') or os.environ.get('GOOGLE_SEARCH_CX')
            except (FileNotFoundError, AttributeError, KeyError):
                self.serper_api_key = os.environ.get('SERPER_API_KEY')
                self.google_api_key = os.environ.get('GOOGLE_SEARCH_API_KEY')
                self.google_cx = os.environ.get('GOOGLE_SEARCH_CX')
        except:
            self.serper_api_key = os.environ.get('SERPER_API_KEY')
            self.google_api_key = os.environ.get('GOOGLE_SEARCH_API_KEY')
            self.google_cx = os.environ.get('GOOGLE_SEARCH_CX')
        
        # 자동으로 사용 가능한 검색 제공자 선택
        if self.search_provider == "auto":
            if self.serper_api_key:
                self.search_provider = "serper"
            elif self.google_api_key and self.google_cx:
                self.search_provider = "google"
            else:
                self.search_provider = "duckduckgo"
    
    def _get_cache_key(self, query: str, num_results: int = 5) -> str:
        """캐시 키 생성"""
        cache_str = f"{query}_{num_results}_{self.search_provider}"
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """캐시 파일 경로 반환"""
        return CACHE_DIR / f"{cache_key}.json"
    
    def _load_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """캐시에서 검색 결과 로드"""
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 캐시 만료 확인
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cache_time > timedelta(hours=CACHE_EXPIRY_HOURS):
                cache_path.unlink()  # 만료된 캐시 삭제
                return None
            
            return cache_data['results']
        except Exception as e:
            print(f"캐시 로드 오류: {e}")
            return None
    
    def _save_cache(self, cache_key: str, results: List[Dict[str, Any]]):
        """검색 결과를 캐시에 저장"""
        cache_path = self._get_cache_path(cache_key)
        
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'results': results
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"캐시 저장 오류: {e}")
    
    def search_duckduckgo(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """DuckDuckGo 검색 (무료, API 키 불필요)"""
        try:
            from duckduckgo_search import DDGS
            
            ddgs = DDGS()
            results = []
            
            # DuckDuckGo 검색
            search_results = ddgs.text(
                query,
                max_results=num_results,
                region='kr-ko'  # 한국 지역
            )
            
            for result in search_results:
                results.append({
                    'title': result.get('title', ''),
                    'snippet': result.get('body', ''),
                    'url': result.get('href', ''),
                    'source': 'DuckDuckGo'
                })
            
            return results
        except ImportError:
            print("DuckDuckGo 검색을 사용하려면 'duckduckgo-search' 패키지가 필요합니다.")
            return []
        except Exception as e:
            print(f"DuckDuckGo 검색 오류: {e}")
            return []
    
    def search_serper(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Serper API 검색 (유료, 하지만 정확함)"""
        if not self.serper_api_key:
            print("Serper API 키가 설정되지 않았습니다.")
            return []
        
        try:
            url = "https://google.serper.dev/search"
            headers = {
                'X-API-KEY': self.serper_api_key,
                'Content-Type': 'application/json'
            }
            payload = {
                'q': query,
                'num': num_results
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # organic 검색 결과
            for item in data.get('organic', [])[:num_results]:
                results.append({
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'url': item.get('link', ''),
                    'source': 'Serper API'
                })
            
            return results
        except Exception as e:
            print(f"Serper API 검색 오류: {e}")
            return []
    
    def search_google(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Google Custom Search API 검색"""
        if not self.google_api_key or not self.google_cx:
            print("Google Search API 키 또는 CX가 설정되지 않았습니다.")
            return []
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_api_key,
                'cx': self.google_cx,
                'q': query,
                'num': min(num_results, 10)  # Google API는 최대 10개
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get('items', [])[:num_results]:
                results.append({
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'url': item.get('link', ''),
                    'source': 'Google Custom Search'
                })
            
            return results
        except Exception as e:
            print(f"Google 검색 오류: {e}")
            return []
    
    def search(self, query: str, num_results: int = 5, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        웹 검색 수행
        
        Args:
            query: 검색 쿼리
            num_results: 결과 개수 (기본값: 5)
            use_cache: 캐시 사용 여부 (기본값: True)
        
        Returns:
            검색 결과 리스트
        """
        # 캐시 확인
        if use_cache:
            cache_key = self._get_cache_key(query, num_results)
            cached_results = self._load_cache(cache_key)
            if cached_results:
                print(f"✅ 캐시에서 검색 결과 로드: {query}")
                return cached_results
        
        # 검색 수행
        print(f"🔍 웹 검색 수행: {query} (Provider: {self.search_provider})")
        
        if self.search_provider == "serper":
            results = self.search_serper(query, num_results)
        elif self.search_provider == "google":
            results = self.search_google(query, num_results)
        else:
            results = self.search_duckduckgo(query, num_results)
        
        # 캐시 저장
        if use_cache and results:
            cache_key = self._get_cache_key(query, num_results)
            self._save_cache(cache_key, results)
        
        return results
    
    def format_search_results(self, results: List[Dict[str, Any]], max_snippet_length: int = 300) -> str:
        """
        검색 결과를 프롬프트에 포함할 수 있는 형식으로 포맷팅
        
        Args:
            results: 검색 결과 리스트
            max_snippet_length: 스니펫 최대 길이
        
        Returns:
            포맷팅된 문자열
        """
        if not results:
            return "검색 결과가 없습니다."
        
        formatted = "## 🌐 웹 검색 결과\n\n"
        
        for i, result in enumerate(results, 1):
            title = result.get('title', '제목 없음')
            snippet = result.get('snippet', '설명 없음')
            url = result.get('url', '')
            source = result.get('source', 'Unknown')
            
            # 스니펫 길이 제한
            if len(snippet) > max_snippet_length:
                snippet = snippet[:max_snippet_length] + "..."
            
            formatted += f"### {i}. {title}\n"
            formatted += f"**출처:** {source}\n"
            formatted += f"**URL:** {url}\n"
            formatted += f"**내용:** {snippet}\n\n"
        
        return formatted
    
    def get_citations_from_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        검색 결과를 citations 형식으로 변환
        
        Args:
            results: 검색 결과 리스트
        
        Returns:
            citations 리스트 (uri, title 포함)
        """
        citations = []
        for result in results:
            url = result.get('url', '')
            title = result.get('title', '')
            if url:  # URL이 있는 경우만 citations에 추가
                citations.append({
                    'uri': url,
                    'title': title or url,  # 제목이 없으면 URL 사용
                    'source': result.get('source', 'Web Search'),
                    'snippet': result.get('snippet', '')
                })
        return citations
    
    def search_multiple_queries(self, queries: List[str], num_results_per_query: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """
        여러 검색 쿼리를 동시에 수행
        
        Args:
            queries: 검색 쿼리 리스트
            num_results_per_query: 쿼리당 결과 개수
        
        Returns:
            쿼리별 검색 결과 딕셔너리
        """
        results_dict = {}
        
        for query in queries:
            results = self.search(query, num_results=num_results_per_query)
            results_dict[query] = results
            # API 호출 제한을 피하기 위해 짧은 대기
            time.sleep(0.5)
        
        return results_dict


def get_web_search_context(block_id: str, project_info: Dict[str, Any], pdf_text: str = "") -> Optional[str]:
    """
    블록 ID에 따라 적절한 웹 검색 쿼리 생성 및 검색 수행
    
    Args:
        block_id: 분석 블록 ID
        project_info: 프로젝트 정보
        pdf_text: PDF 문서 내용 (선택사항)
    
    Returns:
        포맷팅된 검색 결과 문자열 또는 None
    """
    web_search_queries = {
        'market_research_analysis': [
            f"{project_info.get('project_type', '스포츠 아카데미')} 글로벌 시장 규모",
            f"{project_info.get('project_type', '스포츠 아카데미')} 국내 시장 현황",
            f"{project_info.get('location', '')} 스포츠 시설 벤치마킹",
            "스포츠 재활 관광 산업 트렌드"
        ],
        'business_model_development': [
            f"{project_info.get('project_type', '스포츠 아카데미')} 비즈니스 모델",
            f"{project_info.get('location', '')} 지역 경제 연계 산업",
            "스포츠 IP 사업 사례",
            "스포츠 아카데미 수익 모델"
        ],
        'revenue_model_design': [
            f"{project_info.get('project_type', '스포츠 아카데미')} 수익 구조",
            "스포츠 시설 운영 수익 모델",
            "전지훈련 유치 전략"
        ]
    }
    
    queries = web_search_queries.get(block_id)
    if not queries:
        return None
    
    # 웹 검색 수행
    search_helper = WebSearchHelper()
    all_results = []
    
    for query in queries:
        results = search_helper.search(query, num_results=3)
        all_results.extend(results)
    
    if not all_results:
        return None
    
    # 결과 포맷팅
    return search_helper.format_search_results(all_results, max_snippet_length=250)


def get_web_search_citations(block_id: str, project_info: Dict[str, Any], pdf_text: str = "") -> List[Dict[str, Any]]:
    """
    블록 ID에 따라 웹 검색을 수행하고 citations 형식으로 반환
    
    Args:
        block_id: 분석 블록 ID
        project_info: 프로젝트 정보
        pdf_text: PDF 문서 내용 (선택사항)
    
    Returns:
        citations 리스트 (uri, title 포함)
    """
    web_search_queries = {
        'market_research_analysis': [
            f"{project_info.get('project_type', '스포츠 아카데미')} 글로벌 시장 규모",
            f"{project_info.get('project_type', '스포츠 아카데미')} 국내 시장 현황",
            f"{project_info.get('location', '')} 스포츠 시설 벤치마킹",
            "스포츠 재활 관광 산업 트렌드"
        ],
        'business_model_development': [
            f"{project_info.get('project_type', '스포츠 아카데미')} 비즈니스 모델",
            f"{project_info.get('location', '')} 지역 경제 연계 산업",
            "스포츠 IP 사업 사례",
            "스포츠 아카데미 수익 모델"
        ],
        'revenue_model_design': [
            f"{project_info.get('project_type', '스포츠 아카데미')} 수익 구조",
            "스포츠 시설 운영 수익 모델",
            "전지훈련 유치 전략"
        ]
    }
    
    queries = web_search_queries.get(block_id)
    if not queries:
        return []
    
    # 웹 검색 수행
    search_helper = WebSearchHelper()
    all_results = []
    
    for query in queries:
        results = search_helper.search(query, num_results=3)
        all_results.extend(results)
    
    if not all_results:
        return []
    
    # citations 형식으로 변환
    return search_helper.get_citations_from_results(all_results)


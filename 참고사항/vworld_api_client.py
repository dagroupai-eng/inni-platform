"""
VWorld API 2.0 클라이언트
Geocoder API 2.0 및 Search API 2.0 공식 스펙에 맞춰 구현
"""

import requests
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class GeocodeResult:
    """지오코딩 결과"""
    success: bool
    address: Optional[str] = None
    full_address: Optional[str] = None
    coordinates: Optional[Tuple[float, float]] = None
    x: Optional[float] = None
    y: Optional[float] = None
    level0: Optional[str] = None  # 국가
    level1: Optional[str] = None  # 시도
    level2: Optional[str] = None  # 시군구
    level3: Optional[str] = None  # 구
    level4L: Optional[str] = None  # 도로명/법정동
    level5: Optional[str] = None  # 길/번지
    zipcode: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ReverseGeocodeResult:
    """역지오코딩 결과"""
    success: bool
    road_address: Optional[str] = None
    parcel_address: Optional[str] = None
    coordinates: Optional[Tuple[float, float]] = None
    zipcode: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class AddressSearchItem:
    """주소 검색 결과 항목"""
    id: str
    road_address: Optional[str] = None
    parcel_address: Optional[str] = None
    zipcode: Optional[str] = None
    building_name: Optional[str] = None
    building_detail: Optional[str] = None
    coordinates: Optional[Tuple[float, float]] = None
    x: Optional[float] = None
    y: Optional[float] = None


@dataclass
class PlaceSearchItem:
    """장소 검색 결과 항목"""
    id: str
    title: str
    category: str
    road_address: Optional[str] = None
    parcel_address: Optional[str] = None
    coordinates: Optional[Tuple[float, float]] = None
    x: Optional[float] = None
    y: Optional[float] = None


@dataclass
class DistrictSearchItem:
    """행정구역 검색 결과 항목"""
    id: str
    title: str
    geometry_url: Optional[str] = None
    coordinates: Optional[Tuple[float, float]] = None
    x: Optional[float] = None
    y: Optional[float] = None


@dataclass
class RoadSearchItem:
    """도로명 검색 결과 항목"""
    id: str
    title: str
    district: Optional[str] = None
    geometry_url: Optional[str] = None


@dataclass
class SearchResult:
    """검색 결과"""
    success: bool
    items: List[Any] = None
    total: int = 0
    current: int = 0
    page_total: int = 0
    page_current: int = 0
    page_size: int = 0
    error_message: Optional[str] = None


class VWorldAPIClient:
    """VWorld API 2.0 클라이언트"""

    def __init__(self, api_key: str = None):
        """
        VWorld API 클라이언트 초기화

        Args:
            api_key: VWorld API 키 (None이면 환경변수에서 가져옴)
        """
        # API 키 가져오기 (우선순위: 1. 파라미터, 2. Streamlit secrets, 3. 환경변수)
        if api_key:
            self.api_key = api_key
        else:
            try:
                import streamlit as st
                self.api_key = st.secrets.get("VWORLD_API_KEY")
            except Exception:
                self.api_key = None

            if not self.api_key:
                self.api_key = os.getenv("VWORLD_API_KEY")

            if not self.api_key:
                logger.warning("⚠️ VWORLD_API_KEY가 설정되지 않았습니다. .env 파일이나 Streamlit secrets에 추가하세요.")

        # API 엔드포인트
        self.geocoder_url = "https://api.vworld.kr/req/address"
        self.search_url = "https://api.vworld.kr/req/search"
        self.timeout = int(os.getenv("VWORLD_API_TIMEOUT", "30"))

    # ==================== Geocoder API 2.0 ====================

    def get_coord(self, address: str, type: str = "ROAD", refine: bool = True,
                  simple: bool = False, crs: str = "EPSG:4326") -> GeocodeResult:
        """
        주소를 좌표로 변환 (GetCoord)

        Args:
            address: 검색할 주소
            type: 주소 유형 ("ROAD": 도로명주소, "PARCEL": 지번주소)
            refine: 주소 정제 여부 (기본값: True)
            simple: 간략 출력 여부 (기본값: False)
            crs: 좌표계 (기본값: EPSG:4326)

        Returns:
            GeocodeResult: 지오코딩 결과
        """
        try:
            if not self.api_key:
                return GeocodeResult(
                    success=False,
                    error_message="VWORLD_API_KEY가 설정되지 않았습니다"
                )

            logger.info(f"주소 → 좌표 변환 시작: {address} (type={type})")

            params = {
                "service": "address",
                "request": "GetCoord",  # 대문자 G, 대문자 C
                "version": "2.0",
                "key": self.api_key,
                "crs": crs.lower(),  # 소문자로 변환
                "address": address,
                "type": type,  # ROAD 또는 PARCEL
                "refine": "true" if refine else "false",
                "simple": "true" if simple else "false",
                "format": "json",
                "errorFormat": "json"
            }

            response = requests.get(self.geocoder_url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # 응답 처리
            if "response" in data:
                response_data = data["response"]
                status = response_data.get("status", "")

                if status == "OK":
                    result = response_data.get("result", {})
                    if result:
                        point = result.get("point", {})
                        x = point.get("x", "")
                        y = point.get("y", "")

                        # 좌표 추출
                        coordinates = None
                        x_float = None
                        y_float = None
                        if x and y:
                            try:
                                x_float = float(x)
                                y_float = float(y)
                                coordinates = (x_float, y_float)
                            except (ValueError, TypeError):
                                pass

                        # 구조화된 주소 정보
                        structure = result.get("refined", {}).get("structure", {}) if not simple else {}

                        geocode_result = GeocodeResult(
                            success=True,
                            address=address,
                            full_address=result.get("refined", {}).get("text", "") if not simple else "",
                            coordinates=coordinates,
                            x=x_float,
                            y=y_float,
                            level0=structure.get("level0", ""),
                            level1=structure.get("level1", ""),
                            level2=structure.get("level2", ""),
                            level3=structure.get("level3", ""),
                            level4L=structure.get("level4L", ""),
                            level5=structure.get("level5", ""),
                            zipcode=result.get("refined", {}).get("zipcode", "") if not simple else ""
                        )

                        logger.info(f"주소 → 좌표 변환 성공: ({x_float}, {y_float})")
                        return geocode_result
                    else:
                        return GeocodeResult(
                            success=False,
                            error_message="검색 결과가 없습니다"
                        )
                elif status == "NOT_FOUND":
                    logger.warning(f"검색 결과 없음: {address}")
                    return GeocodeResult(
                        success=False,
                        error_message="검색 결과가 없습니다"
                    )
                elif status == "ERROR":
                    error_obj = response_data.get("error", {})
                    error_text = error_obj.get("text", "알 수 없는 오류")
                    logger.error(f"VWorld API 오류: {error_text}")
                    return GeocodeResult(
                        success=False,
                        error_message=f"API 오류: {error_text}"
                    )
                else:
                    logger.error(f"알 수 없는 상태: {status}")
                    return GeocodeResult(
                        success=False,
                        error_message=f"알 수 없는 상태: {status}"
                    )
            else:
                return GeocodeResult(
                    success=False,
                    error_message="응답 형식이 올바르지 않습니다"
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"주소 → 좌표 변환 중 네트워크 오류: {e}")
            return GeocodeResult(
                success=False,
                error_message=f"네트워크 오류: {str(e)}"
            )
        except Exception as e:
            logger.error(f"주소 → 좌표 변환 중 오류: {e}", exc_info=True)
            return GeocodeResult(
                success=False,
                error_message=f"오류: {str(e)}"
            )

    def get_address(self, point: Tuple[float, float], type: str = "BOTH",
                    zipcode: bool = True, simple: bool = False,
                    crs: str = "EPSG:4326") -> ReverseGeocodeResult:
        """
        좌표를 주소로 변환 (GetAddress)

        Args:
            point: 좌표 (x, y) - 경도, 위도
            type: 주소 유형 ("BOTH": 도로명+지번, "ROAD": 도로명, "PARCEL": 지번)
            zipcode: 우편번호 반환 여부 (기본값: True)
            simple: 간략 출력 여부 (기본값: False)
            crs: 좌표계 (기본값: EPSG:4326)

        Returns:
            ReverseGeocodeResult: 역지오코딩 결과
        """
        try:
            if not self.api_key:
                return ReverseGeocodeResult(
                    success=False,
                    error_message="VWORLD_API_KEY가 설정되지 않았습니다"
                )

            x, y = point
            logger.info(f"좌표 → 주소 변환 시작: ({x}, {y}) (type={type})")

            params = {
                "service": "address",
                "request": "GetAddress",  # 대문자 G, 대문자 A
                "version": "2.0",
                "key": self.api_key,
                "crs": crs.lower(),
                "point": f"{x},{y}",
                "type": type,  # BOTH, ROAD, PARCEL
                "zipcode": "true" if zipcode else "false",
                "simple": "true" if simple else "false",
                "format": "json",
                "errorFormat": "json"
            }

            response = requests.get(self.geocoder_url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # 응답 처리
            if "response" in data:
                response_data = data["response"]
                status = response_data.get("status", "")

                if status == "OK":
                    result = response_data.get("result", {})
                    if result:
                        # result가 리스트인 경우와 딕셔너리인 경우 모두 처리
                        if isinstance(result, list):
                            items = result
                        elif isinstance(result, dict):
                            items = result.get("items", [])
                            # items가 리스트가 아닌 경우 (단일 항목인 경우)
                            if not isinstance(items, list):
                                items = [items] if items else []
                        else:
                            items = []

                        # items가 리스트가 아닌 경우 (단일 항목인 경우)
                        if not isinstance(items, list):
                            items = [items] if items else []

                        if items:
                            item = items[0]  # 첫 번째 결과 사용

                            reverse_result = ReverseGeocodeResult(
                                success=True,
                                road_address=item.get("text", "") if item.get("type") == "ROAD" or type in ["BOTH", "ROAD"] else None,
                                parcel_address=item.get("text", "") if item.get("type") == "PARCEL" or type in ["BOTH", "PARCEL"] else None,
                                coordinates=point,
                                zipcode=item.get("zipcode", "") if zipcode else None
                            )

                            # BOTH 타입인 경우 도로명과 지번을 구분
                            if type == "BOTH" and len(items) >= 2:
                                for item_data in items:
                                    if item_data.get("type") == "ROAD":
                                        reverse_result.road_address = item_data.get("text", "")
                                    elif item_data.get("type") == "PARCEL":
                                        reverse_result.parcel_address = item_data.get("text", "")

                            logger.info(f"좌표 → 주소 변환 성공: {reverse_result.road_address or reverse_result.parcel_address}")
                            return reverse_result
                        else:
                            return ReverseGeocodeResult(
                                success=False,
                                error_message="검색 결과가 없습니다"
                            )
                    else:
                        return ReverseGeocodeResult(
                            success=False,
                            error_message="검색 결과가 없습니다"
                        )
                elif status == "NOT_FOUND":
                    logger.warning(f"검색 결과 없음: ({x}, {y})")
                    return ReverseGeocodeResult(
                        success=False,
                        error_message="검색 결과가 없습니다"
                    )
                elif status == "ERROR":
                    error_obj = response_data.get("error", {})
                    error_text = error_obj.get("text", "알 수 없는 오류")
                    logger.error(f"VWorld API 오류: {error_text}")
                    return ReverseGeocodeResult(
                        success=False,
                        error_message=f"API 오류: {error_text}"
                    )
                else:
                    return ReverseGeocodeResult(
                        success=False,
                        error_message=f"알 수 없는 상태: {status}"
                    )
            else:
                return ReverseGeocodeResult(
                    success=False,
                    error_message="응답 형식이 올바르지 않습니다"
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"좌표 → 주소 변환 중 네트워크 오류: {e}")
            return ReverseGeocodeResult(
                success=False,
                error_message=f"네트워크 오류: {str(e)}"
            )
        except Exception as e:
            logger.error(f"좌표 → 주소 변환 중 오류: {e}", exc_info=True)
            return ReverseGeocodeResult(
                success=False,
                error_message=f"오류: {str(e)}"
            )

    # ==================== Search API 2.0 ====================

    def search_address(self, query: str, category: str = "ROAD",
                       size: int = 10, page: int = 1,
                       bbox: Optional[Tuple[float, float, float, float]] = None,
                       crs: str = "EPSG:4326") -> SearchResult:
        """
        주소 검색 (Search API - type=ADDRESS)

        Args:
            query: 검색 키워드
            category: 주소 유형 ("ROAD": 도로명, "PARCEL": 지번)
            size: 페이지당 결과 수 (기본값: 10, 최대: 1000)
            page: 페이지 번호 (기본값: 1)
            bbox: 검색 영역 (minx, miny, maxx, maxy) - 선택사항
            crs: 좌표계 (기본값: EPSG:4326)

        Returns:
            SearchResult: 검색 결과
        """
        try:
            if not self.api_key:
                return SearchResult(
                    success=False,
                    error_message="VWORLD_API_KEY가 설정되지 않았습니다"
                )

            logger.info(f"주소 검색 시작: {query} (category={category})")

            params = {
                "service": "search",
                "request": "search",
                "version": "2.0",
                "key": self.api_key,
                "query": query,
                "type": "ADDRESS",
                "category": category,  # ROAD 또는 PARCEL
                "size": min(size, 1000),  # 최대 1000건
                "page": page,
                "format": "json",
                "errorFormat": "json",
                "crs": crs
            }

            if bbox:
                minx, miny, maxx, maxy = bbox
                params["bbox"] = f"{minx},{miny},{maxx},{maxy}"

            response = requests.get(self.search_url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # 응답 처리
            if "response" in data:
                response_data = data["response"]
                status = response_data.get("status", "")

                if status == "OK":
                    result = response_data.get("result", {})
                    items_data = result.get("items", {})
                    items_list = items_data.get("item", []) if isinstance(items_data, dict) else []

                    # 단일 항목인 경우 리스트로 변환
                    if isinstance(items_list, dict):
                        items_list = [items_list]

                    items = []
                    for item_data in items_list:
                        address_info = item_data.get("address", {})
                        point_info = item_data.get("point", {})

                        x = point_info.get("x", "")
                        y = point_info.get("y", "")
                        coordinates = None
                        x_float = None
                        y_float = None
                        if x and y:
                            try:
                                x_float = float(x)
                                y_float = float(y)
                                coordinates = (x_float, y_float)
                            except (ValueError, TypeError):
                                pass

                        item = AddressSearchItem(
                            id=item_data.get("id", ""),
                            road_address=address_info.get("road", ""),
                            parcel_address=address_info.get("parcel", ""),
                            zipcode=str(address_info.get("zipcode", "")) if address_info.get("zipcode") else None,
                            building_name=address_info.get("bldnm", ""),
                            building_detail=address_info.get("bldnmdc", ""),
                            coordinates=coordinates,
                            x=x_float,
                            y=y_float
                        )
                        items.append(item)

                    record = response_data.get("record", {})
                    page_info = response_data.get("page", {})

                    search_result = SearchResult(
                        success=True,
                        items=items,
                        total=record.get("total", 0),
                        current=record.get("current", 0),
                        page_total=page_info.get("total", 0),
                        page_current=page_info.get("current", 0),
                        page_size=page_info.get("size", 0)
                    )

                    logger.info(f"주소 검색 성공: {len(items)}건")
                    return search_result
                elif status == "NOT_FOUND":
                    logger.warning(f"검색 결과 없음: {query}")
                    return SearchResult(
                        success=True,
                        items=[],
                        total=0,
                        current=0
                    )
                elif status == "ERROR":
                    error_obj = response_data.get("error", {})
                    error_text = error_obj.get("text", "알 수 없는 오류")
                    logger.error(f"VWorld API 오류: {error_text}")
                    return SearchResult(
                        success=False,
                        error_message=f"API 오류: {error_text}"
                    )
                else:
                    return SearchResult(
                        success=False,
                        error_message=f"알 수 없는 상태: {status}"
                    )
            else:
                return SearchResult(
                    success=False,
                    error_message="응답 형식이 올바르지 않습니다"
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"주소 검색 중 네트워크 오류: {e}")
            return SearchResult(
                success=False,
                error_message=f"네트워크 오류: {str(e)}"
            )
        except Exception as e:
            logger.error(f"주소 검색 중 오류: {e}", exc_info=True)
            return SearchResult(
                success=False,
                error_message=f"오류: {str(e)}"
            )

    def search_place(self, query: str, size: int = 10, page: int = 1,
                     bbox: Optional[Tuple[float, float, float, float]] = None,
                     crs: str = "EPSG:4326") -> SearchResult:
        """
        장소 검색 (Search API - type=PLACE)

        Args:
            query: 검색 키워드 (건물명, 시설명, 기관/상호명 등)
            size: 페이지당 결과 수 (기본값: 10, 최대: 1000)
            page: 페이지 번호 (기본값: 1)
            bbox: 검색 영역 (minx, miny, maxx, maxy) - 선택사항
            crs: 좌표계 (기본값: EPSG:4326)

        Returns:
            SearchResult: 검색 결과
        """
        try:
            if not self.api_key:
                return SearchResult(
                    success=False,
                    error_message="VWORLD_API_KEY가 설정되지 않았습니다"
                )

            logger.info(f"장소 검색 시작: {query}")

            params = {
                "service": "search",
                "request": "search",
                "version": "2.0",
                "key": self.api_key,
                "query": query,
                "type": "PLACE",
                "size": min(size, 1000),
                "page": page,
                "format": "json",
                "errorFormat": "json",
                "crs": crs
            }

            if bbox:
                minx, miny, maxx, maxy = bbox
                params["bbox"] = f"{minx},{miny},{maxx},{maxy}"

            response = requests.get(self.search_url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # 응답 처리
            if "response" in data:
                response_data = data["response"]
                status = response_data.get("status", "")

                if status == "OK":
                    result = response_data.get("result", {})
                    items_data = result.get("items", {})
                    items_list = items_data.get("item", []) if isinstance(items_data, dict) else []

                    if isinstance(items_list, dict):
                        items_list = [items_list]

                    items = []
                    for item_data in items_list:
                        address_info = item_data.get("address", {})
                        point_info = item_data.get("point", {})

                        x = point_info.get("x", "")
                        y = point_info.get("y", "")
                        coordinates = None
                        x_float = None
                        y_float = None
                        if x and y:
                            try:
                                x_float = float(x)
                                y_float = float(y)
                                coordinates = (x_float, y_float)
                            except (ValueError, TypeError):
                                pass

                        item = PlaceSearchItem(
                            id=item_data.get("id", ""),
                            title=item_data.get("title", ""),
                            category=item_data.get("category", ""),
                            road_address=address_info.get("road", ""),
                            parcel_address=address_info.get("parcel", ""),
                            coordinates=coordinates,
                            x=x_float,
                            y=y_float
                        )
                        items.append(item)

                    record = response_data.get("record", {})
                    page_info = response_data.get("page", {})

                    search_result = SearchResult(
                        success=True,
                        items=items,
                        total=record.get("total", 0),
                        current=record.get("current", 0),
                        page_total=page_info.get("total", 0),
                        page_current=page_info.get("current", 0),
                        page_size=page_info.get("size", 0)
                    )

                    logger.info(f"장소 검색 성공: {len(items)}건")
                    return search_result
                elif status == "NOT_FOUND":
                    return SearchResult(
                        success=True,
                        items=[],
                        total=0,
                        current=0
                    )
                elif status == "ERROR":
                    error_obj = response_data.get("error", {})
                    error_text = error_obj.get("text", "알 수 없는 오류")
                    logger.error(f"VWorld API 오류: {error_text}")
                    return SearchResult(
                        success=False,
                        error_message=f"API 오류: {error_text}"
                    )
                else:
                    return SearchResult(
                        success=False,
                        error_message=f"알 수 없는 상태: {status}"
                    )
            else:
                return SearchResult(
                    success=False,
                    error_message="응답 형식이 올바르지 않습니다"
                )

        except Exception as e:
            logger.error(f"장소 검색 중 오류: {e}", exc_info=True)
            return SearchResult(
                success=False,
                error_message=f"오류: {str(e)}"
            )

    def search_district(self, query: str, category: str = "L4",
                       size: int = 10, page: int = 1,
                       bbox: Optional[Tuple[float, float, float, float]] = None,
                       crs: str = "EPSG:4326") -> SearchResult:
        """
        행정구역 검색 (Search API - type=DISTRICT)

        Args:
            query: 검색 키워드 (행정구역명)
            category: 행정구역 레벨 ("L1": 시도, "L2": 시군구, "L3": 일반구, "L4": 읍면동)
            size: 페이지당 결과 수 (기본값: 10, 최대: 1000)
            page: 페이지 번호 (기본값: 1)
            bbox: 검색 영역 (minx, miny, maxx, maxy) - 선택사항
            crs: 좌표계 (기본값: EPSG:4326)

        Returns:
            SearchResult: 검색 결과
        """
        try:
            if not self.api_key:
                return SearchResult(
                    success=False,
                    error_message="VWORLD_API_KEY가 설정되지 않았습니다"
                )

            logger.info(f"행정구역 검색 시작: {query} (category={category})")

            params = {
                "service": "search",
                "request": "search",
                "version": "2.0",
                "key": self.api_key,
                "query": query,
                "type": "DISTRICT",
                "category": category,
                "size": min(size, 1000),
                "page": page,
                "format": "json",
                "errorFormat": "json",
                "crs": crs
            }

            if bbox:
                minx, miny, maxx, maxy = bbox
                params["bbox"] = f"{minx},{miny},{maxx},{maxy}"

            response = requests.get(self.search_url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # 응답 처리
            if "response" in data:
                response_data = data["response"]
                status = response_data.get("status", "")

                if status == "OK":
                    result = response_data.get("result", {})
                    items_data = result.get("items", {})
                    items_list = items_data.get("item", []) if isinstance(items_data, dict) else []

                    if isinstance(items_list, dict):
                        items_list = [items_list]

                    items = []
                    for item_data in items_list:
                        point_info = item_data.get("point", {})

                        x = point_info.get("x", "")
                        y = point_info.get("y", "")
                        coordinates = None
                        x_float = None
                        y_float = None
                        if x and y:
                            try:
                                x_float = float(x)
                                y_float = float(y)
                                coordinates = (x_float, y_float)
                            except (ValueError, TypeError):
                                pass

                        item = DistrictSearchItem(
                            id=item_data.get("id", ""),
                            title=item_data.get("title", ""),
                            geometry_url=item_data.get("geometry", ""),
                            coordinates=coordinates,
                            x=x_float,
                            y=y_float
                        )
                        items.append(item)

                    record = response_data.get("record", {})
                    page_info = response_data.get("page", {})

                    search_result = SearchResult(
                        success=True,
                        items=items,
                        total=record.get("total", 0),
                        current=record.get("current", 0),
                        page_total=page_info.get("total", 0),
                        page_current=page_info.get("current", 0),
                        page_size=page_info.get("size", 0)
                    )

                    logger.info(f"행정구역 검색 성공: {len(items)}건")
                    return search_result
                elif status == "NOT_FOUND":
                    return SearchResult(
                        success=True,
                        items=[],
                        total=0,
                        current=0
                    )
                elif status == "ERROR":
                    error_obj = response_data.get("error", {})
                    error_text = error_obj.get("text", "알 수 없는 오류")
                    logger.error(f"VWorld API 오류: {error_text}")
                    return SearchResult(
                        success=False,
                        error_message=f"API 오류: {error_text}"
                    )
                else:
                    return SearchResult(
                        success=False,
                        error_message=f"알 수 없는 상태: {status}"
                    )
            else:
                return SearchResult(
                    success=False,
                    error_message="응답 형식이 올바르지 않습니다"
                )

        except Exception as e:
            logger.error(f"행정구역 검색 중 오류: {e}", exc_info=True)
            return SearchResult(
                success=False,
                error_message=f"오류: {str(e)}"
            )

    def search_road(self, query: str, size: int = 10, page: int = 1,
                   bbox: Optional[Tuple[float, float, float, float]] = None,
                   crs: str = "EPSG:4326") -> SearchResult:
        """
        도로명 검색 (Search API - type=ROAD)

        Args:
            query: 검색 키워드 (도로명)
            size: 페이지당 결과 수 (기본값: 10, 최대: 1000)
            page: 페이지 번호 (기본값: 1)
            bbox: 검색 영역 (minx, miny, maxx, maxy) - 선택사항
            crs: 좌표계 (기본값: EPSG:4326)

        Returns:
            SearchResult: 검색 결과
        """
        try:
            if not self.api_key:
                return SearchResult(
                    success=False,
                    error_message="VWORLD_API_KEY가 설정되지 않았습니다"
                )

            logger.info(f"도로명 검색 시작: {query}")

            params = {
                "service": "search",
                "request": "search",
                "version": "2.0",
                "key": self.api_key,
                "query": query,
                "type": "ROAD",
                "size": min(size, 1000),
                "page": page,
                "format": "json",
                "errorFormat": "json",
                "crs": crs
            }

            if bbox:
                minx, miny, maxx, maxy = bbox
                params["bbox"] = f"{minx},{miny},{maxx},{maxy}"

            response = requests.get(self.search_url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # 응답 처리
            if "response" in data:
                response_data = data["response"]
                status = response_data.get("status", "")

                if status == "OK":
                    result = response_data.get("result", {})
                    items_data = result.get("items", {})
                    items_list = items_data.get("item", []) if isinstance(items_data, dict) else []

                    if isinstance(items_list, dict):
                        items_list = [items_list]

                    items = []
                    for item_data in items_list:
                        item = RoadSearchItem(
                            id=item_data.get("id", ""),
                            title=item_data.get("title", ""),
                            district=item_data.get("district", ""),
                            geometry_url=item_data.get("geometry", "")
                        )
                        items.append(item)

                    record = response_data.get("record", {})
                    page_info = response_data.get("page", {})

                    search_result = SearchResult(
                        success=True,
                        items=items,
                        total=record.get("total", 0),
                        current=record.get("current", 0),
                        page_total=page_info.get("total", 0),
                        page_current=page_info.get("current", 0),
                        page_size=page_info.get("size", 0)
                    )

                    logger.info(f"도로명 검색 성공: {len(items)}건")
                    return search_result
                elif status == "NOT_FOUND":
                    return SearchResult(
                        success=True,
                        items=[],
                        total=0,
                        current=0
                    )
                elif status == "ERROR":
                    error_obj = response_data.get("error", {})
                    error_text = error_obj.get("text", "알 수 없는 오류")
                    logger.error(f"VWorld API 오류: {error_text}")
                    return SearchResult(
                        success=False,
                        error_message=f"API 오류: {error_text}"
                    )
                else:
                    return SearchResult(
                        success=False,
                        error_message=f"알 수 없는 상태: {status}"
                    )
            else:
                return SearchResult(
                    success=False,
                    error_message="응답 형식이 올바르지 않습니다"
                )

        except Exception as e:
            logger.error(f"도로명 검색 중 오류: {e}", exc_info=True)
            return SearchResult(
                success=False,
                error_message=f"오류: {str(e)}"
            )


# 전역 인스턴스
_vworld_api_client = None


def get_vworld_api_client() -> VWorldAPIClient:
    """VWorld API 클라이언트 인스턴스 반환 (싱글톤)"""
    global _vworld_api_client
    if _vworld_api_client is None:
        _vworld_api_client = VWorldAPIClient()
    return _vworld_api_client


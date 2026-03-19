"""
VWorld API 2.0 클라이언트
Geocoder API 2.0 및 Search API 2.0 공식 스펙에 맞춰 구현
"""

import requests
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

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
    level0: Optional[str] = None
    level1: Optional[str] = None
    level2: Optional[str] = None
    level3: Optional[str] = None
    level4L: Optional[str] = None
    level5: Optional[str] = None
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

        self.geocoder_url = "https://api.vworld.kr/req/address"
        self.search_url = "https://api.vworld.kr/req/search"
        self.timeout = int(os.getenv("VWORLD_API_TIMEOUT", "30"))

    # ==================== Geocoder API 2.0 ====================

    def get_coord(self, address: str, type: str = "ROAD", refine: bool = True,
                  simple: bool = False, crs: str = "EPSG:4326") -> GeocodeResult:
        try:
            if not self.api_key:
                return GeocodeResult(success=False, error_message="VWORLD_API_KEY 미설정")

            params = {
                "service": "address",
                "request": "GetCoord",
                "version": "2.0",
                "key": self.api_key,
                "crs": crs.lower(),
                "address": address,
                "type": type,
                "refine": "true" if refine else "false",
                "simple": "true" if simple else "false",
                "format": "json",
                "errorFormat": "json"
            }

            response = requests.get(self.geocoder_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if "response" in data:
                response_data = data["response"]
                status = response_data.get("status", "")

                if status == "OK":
                    result = response_data.get("result", {})
                    if result:
                        point = result.get("point", {})
                        x = point.get("x", "")
                        y = point.get("y", "")
                        coordinates = (float(x), float(y)) if x and y else None
                        
                        structure = result.get("refined", {}).get("structure", {}) if not simple else {}

                        return GeocodeResult(
                            success=True,
                            address=address,
                            full_address=result.get("refined", {}).get("text", "") if not simple else "",
                            coordinates=coordinates,
                            x=coordinates[0] if coordinates else None,
                            y=coordinates[1] if coordinates else None,
                            level0=structure.get("level0", ""),
                            level1=structure.get("level1", ""),
                            level2=structure.get("level2", ""),
                            level3=structure.get("level3", ""),
                            level4L=structure.get("level4L", ""),
                            level5=structure.get("level5", ""),
                            zipcode=result.get("refined", {}).get("zipcode", "") if not simple else ""
                        )
                return GeocodeResult(success=False, error_message=f"API Status: {status}")
            return GeocodeResult(success=False, error_message="응답 형식 오류")
        except Exception as e:
            return GeocodeResult(success=False, error_message=str(e))

    def get_address(self, point: Tuple[float, float], type: str = "BOTH",
                    zipcode: bool = True, simple: bool = False,
                    crs: str = "EPSG:4326") -> ReverseGeocodeResult:
        try:
            if not self.api_key:
                return ReverseGeocodeResult(success=False, error_message="VWORLD_API_KEY 미설정")

            x, y = point
            params = {
                "service": "address",
                "request": "GetAddress",
                "version": "2.0",
                "key": self.api_key,
                "crs": crs.lower(),
                "point": f"{x},{y}",
                "type": type,
                "zipcode": "true" if zipcode else "false",
                "simple": "true" if simple else "false",
                "format": "json",
                "errorFormat": "json"
            }

            response = requests.get(self.geocoder_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if "response" in data:
                resp = data["response"]
                if resp.get("status") == "OK":
                    result = resp.get("result", [])
                    items = result if isinstance(result, list) else result.get("items", [])
                    if not isinstance(items, list): items = [items]
                    
                    res = ReverseGeocodeResult(success=True, coordinates=point)
                    for item in items:
                        if item.get("type") == "ROAD": res.road_address = item.get("text")
                        elif item.get("type") == "PARCEL": res.parcel_address = item.get("text")
                        if zipcode: res.zipcode = item.get("zipcode")
                    return res
                return ReverseGeocodeResult(success=False, error_message=f"Status: {resp.get('status')}")
            return ReverseGeocodeResult(success=False, error_message="응답 형식 오류")
        except Exception as e:
            return ReverseGeocodeResult(success=False, error_message=str(e))

    # Search API 2.0 (간소화된 구현)
    def search_address(self, query: str, category: str = "ROAD", size: int = 10, page: int = 1) -> SearchResult:
        try:
            params = {
                "service": "search", "request": "search", "version": "2.0",
                "key": self.api_key, "query": query, "type": "ADDRESS",
                "category": category, "size": size, "page": page, "format": "json"
            }
            r = requests.get(self.search_url, params=params, timeout=self.timeout)
            r.raise_for_status()
            data = r.json().get("response", {})
            if data.get("status") == "OK":
                items_raw = data.get("result", {}).get("items", {}).get("item", [])
                if isinstance(items_raw, dict): items_raw = [items_raw]
                items = [AddressSearchItem(id=i.get("id"), road_address=i.get("address",{}).get("road"),
                                         parcel_address=i.get("address",{}).get("parcel"),
                                         x=float(i.get("point",{}).get("x")), y=float(i.get("point",{}).get("y")))
                        for i in items_raw]
                return SearchResult(success=True, items=items, total=int(data.get("record",{}).get("total",0)))
            return SearchResult(success=False, error_message=data.get("status"))
        except Exception as e:
            return SearchResult(success=False, error_message=str(e))

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
        """
        try:
            if not self.api_key:
                return SearchResult(success=False, error_message="VWORLD_API_KEY가 설정되지 않았습니다")

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
                        x_str = point_info.get("x", "")
                        y_str = point_info.get("y", "")
                        try:
                            x_float = float(x_str) if x_str else None
                            y_float = float(y_str) if y_str else None
                        except (ValueError, TypeError):
                            x_float = y_float = None
                        coordinates = (x_float, y_float) if x_float and y_float else None
                        items.append(PlaceSearchItem(
                            id=item_data.get("id", ""),
                            title=item_data.get("title", ""),
                            category=item_data.get("category", ""),
                            road_address=address_info.get("road", ""),
                            parcel_address=address_info.get("parcel", ""),
                            coordinates=coordinates,
                            x=x_float,
                            y=y_float
                        ))

                    record = response_data.get("record", {})
                    page_info = response_data.get("page", {})
                    return SearchResult(
                        success=True, items=items,
                        total=record.get("total", 0), current=record.get("current", 0),
                        page_total=page_info.get("total", 0), page_current=page_info.get("current", 0),
                        page_size=page_info.get("size", 0)
                    )
                elif status == "NOT_FOUND":
                    return SearchResult(success=True, items=[], total=0, current=0)
                else:
                    error_text = response_data.get("error", {}).get("text", "알 수 없는 오류")
                    return SearchResult(success=False, error_message=f"API 오류: {error_text}")
            return SearchResult(success=False, error_message="응답 형식이 올바르지 않습니다")
        except Exception as e:
            logger.error(f"장소 검색 중 오류: {e}", exc_info=True)
            return SearchResult(success=False, error_message=f"오류: {str(e)}")

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
        """
        try:
            if not self.api_key:
                return SearchResult(success=False, error_message="VWORLD_API_KEY가 설정되지 않았습니다")

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
                        x_str = point_info.get("x", "")
                        y_str = point_info.get("y", "")
                        try:
                            x_float = float(x_str) if x_str else None
                            y_float = float(y_str) if y_str else None
                        except (ValueError, TypeError):
                            x_float = y_float = None
                        coordinates = (x_float, y_float) if x_float and y_float else None
                        items.append(DistrictSearchItem(
                            id=item_data.get("id", ""),
                            title=item_data.get("title", ""),
                            geometry_url=item_data.get("geometry", ""),
                            coordinates=coordinates,
                            x=x_float,
                            y=y_float
                        ))

                    record = response_data.get("record", {})
                    page_info = response_data.get("page", {})
                    return SearchResult(
                        success=True, items=items,
                        total=record.get("total", 0), current=record.get("current", 0),
                        page_total=page_info.get("total", 0), page_current=page_info.get("current", 0),
                        page_size=page_info.get("size", 0)
                    )
                elif status == "NOT_FOUND":
                    return SearchResult(success=True, items=[], total=0, current=0)
                else:
                    error_text = response_data.get("error", {}).get("text", "알 수 없는 오류")
                    return SearchResult(success=False, error_message=f"API 오류: {error_text}")
            return SearchResult(success=False, error_message="응답 형식이 올바르지 않습니다")
        except Exception as e:
            logger.error(f"행정구역 검색 중 오류: {e}", exc_info=True)
            return SearchResult(success=False, error_message=f"오류: {str(e)}")

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
        """
        try:
            if not self.api_key:
                return SearchResult(success=False, error_message="VWORLD_API_KEY가 설정되지 않았습니다")

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

            if "response" in data:
                response_data = data["response"]
                status = response_data.get("status", "")

                if status == "OK":
                    result = response_data.get("result", {})
                    items_data = result.get("items", {})
                    items_list = items_data.get("item", []) if isinstance(items_data, dict) else []
                    if isinstance(items_list, dict):
                        items_list = [items_list]

                    items = [
                        RoadSearchItem(
                            id=item_data.get("id", ""),
                            title=item_data.get("title", ""),
                            district=item_data.get("district", ""),
                            geometry_url=item_data.get("geometry", "")
                        )
                        for item_data in items_list
                    ]

                    record = response_data.get("record", {})
                    page_info = response_data.get("page", {})
                    return SearchResult(
                        success=True, items=items,
                        total=record.get("total", 0), current=record.get("current", 0),
                        page_total=page_info.get("total", 0), page_current=page_info.get("current", 0),
                        page_size=page_info.get("size", 0)
                    )
                elif status == "NOT_FOUND":
                    return SearchResult(success=True, items=[], total=0, current=0)
                else:
                    error_text = response_data.get("error", {}).get("text", "알 수 없는 오류")
                    return SearchResult(success=False, error_message=f"API 오류: {error_text}")
            return SearchResult(success=False, error_message="응답 형식이 올바르지 않습니다")
        except Exception as e:
            logger.error(f"도로명 검색 중 오류: {e}", exc_info=True)
            return SearchResult(success=False, error_message=f"오류: {str(e)}")


# 전역 인스턴스
_vworld_api_client = None


def get_vworld_api_client() -> VWorldAPIClient:
    """VWorld API 클라이언트 인스턴스 반환 (싱글톤)"""
    global _vworld_api_client
    if _vworld_api_client is None:
        _vworld_api_client = VWorldAPIClient()
    return _vworld_api_client

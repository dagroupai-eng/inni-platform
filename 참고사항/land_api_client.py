"""
토지(필지) 정보 API 클라이언트

VWorld Data API를 사용해 실제 공적 데이터 조회:
  - LP_PA_CBND_BUBUN  : 연속지적도 (필지 경계, 지목, 면적, PNU)
  - LT_C_LFCPAM       : 토지이음 용도지역 (용도지역/지구/구역)

지목코드 → 합필 가능 여부 판단, 용도지역 교차 비교, 접도 조건 분석 포함
"""

import os
import logging
import requests
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ─── 지목코드 매핑 ─────────────────────────────────────────────────────────────
LAND_CATEGORY_MAP: Dict[str, str] = {
    "01": "전",       "02": "답",       "03": "과수원",   "04": "목장용지",
    "05": "임야",     "06": "광천지",   "07": "염전",     "08": "대",
    "09": "공장용지", "10": "학교용지", "11": "주차장",   "12": "주유소용지",
    "13": "창고용지", "14": "도로",     "15": "철도용지", "16": "제방",
    "17": "하천",     "18": "구거",     "19": "유지",     "20": "양어장",
    "21": "수도용지", "22": "공원",     "23": "체육용지", "24": "유원지",
    "25": "종교용지", "26": "사적지",   "27": "묘지",     "28": "잡종지",
}

# 건축법상 건축이 가능한 기본 지목 (합필 없이 바로 건축 허가 가능)
BUILDABLE_CATEGORIES = {"08", "09", "10", "11", "22", "23", "24", "25"}

# 용도지역 건폐율/용적률 기준 (국토계획법 시행령 기준)
ZONING_LIMITS: Dict[str, Dict[str, int]] = {
    "제1종전용주거지역": {"bcr": 50, "far": 100},
    "제2종전용주거지역": {"bcr": 50, "far": 150},
    "제1종일반주거지역": {"bcr": 60, "far": 200},
    "제2종일반주거지역": {"bcr": 60, "far": 250},
    "제3종일반주거지역": {"bcr": 50, "far": 300},
    "준주거지역":        {"bcr": 70, "far": 500},
    "중심상업지역":      {"bcr": 90, "far": 1500},
    "일반상업지역":      {"bcr": 80, "far": 1300},
    "근린상업지역":      {"bcr": 70, "far": 900},
    "유통상업지역":      {"bcr": 80, "far": 1100},
    "전용공업지역":      {"bcr": 70, "far": 300},
    "일반공업지역":      {"bcr": 70, "far": 350},
    "준공업지역":        {"bcr": 70, "far": 400},
    "보전녹지지역":      {"bcr": 20, "far": 80},
    "생산녹지지역":      {"bcr": 20, "far": 100},
    "자연녹지지역":      {"bcr": 20, "far": 100},
    "보전관리지역":      {"bcr": 20, "far": 80},
    "생산관리지역":      {"bcr": 20, "far": 80},
    "계획관리지역":      {"bcr": 40, "far": 100},
    "농림지역":          {"bcr": 20, "far": 80},
    "자연환경보전지역":  {"bcr": 20, "far": 80},
}

# 용도지역 제한 강도 순서 (낮을수록 더 제한적)
ZONING_RESTRICTIVENESS: Dict[str, int] = {
    "자연환경보전지역": 1,  "보전녹지지역": 2,   "농림지역": 3,
    "보전관리지역": 4,      "생산관리지역": 5,   "생산녹지지역": 6,
    "자연녹지지역": 7,      "계획관리지역": 8,   "전용공업지역": 9,
    "제1종전용주거지역": 10,"제2종전용주거지역": 11,"제1종일반주거지역": 12,
    "준공업지역": 13,       "일반공업지역": 14,  "제2종일반주거지역": 15,
    "제3종일반주거지역": 16,"보전녹지지역": 17,  "유통상업지역": 18,
    "준주거지역": 19,       "근린상업지역": 20,  "일반상업지역": 21,
    "중심상업지역": 22,
}


@dataclass
class ParcelInfo:
    """단일 필지 정보"""
    address: str                                 # 입력 주소/지번
    pnu: Optional[str] = None                    # 고유번호 (19자리)
    jibun: Optional[str] = None                  # 지번 (예: "123")
    area_m2: Optional[float] = None              # 공부상 면적(㎡)
    land_category_code: Optional[str] = None     # 지목코드 (예: "08")
    land_category_name: Optional[str] = None     # 지목명 (예: "대")
    zoning: Optional[str] = None                 # 용도지역명
    zoning_code: Optional[str] = None            # 용도지역코드
    district: Optional[str] = None              # 용도지구
    zone: Optional[str] = None                   # 용도구역
    coordinates: Optional[Tuple[float, float]] = None  # (경도, 위도) WGS84
    bcr_limit: Optional[int] = None              # 건폐율 한도(%)
    far_limit: Optional[int] = None              # 용적률 한도(%)
    is_buildable: bool = True                    # 현 지목으로 건축 가능 여부
    official_price_per_m2: Optional[int] = None  # 공시지가(원/㎡)
    official_total_price: Optional[int] = None   # 토지 공시가액(원) = 공시지가 × 면적
    price_year: Optional[str] = None             # 공시지가 기준연도
    error: Optional[str] = None
    data_sources: List[str] = field(default_factory=list)


@dataclass
class MultiParcelResult:
    """다중 필지 통합 결과"""
    parcels: List[ParcelInfo]
    total_area_m2: float = 0.0
    parcel_count: int = 0
    all_zonings: List[str] = field(default_factory=list)
    all_land_categories: List[str] = field(default_factory=list)
    dominant_zoning: Optional[str] = None        # 가장 넓은 면적의 용도지역
    worst_case_zoning: Optional[str] = None      # 가장 제한적인 용도지역
    worst_bcr: Optional[int] = None              # 가장 제한적인 건폐율(%)
    worst_far: Optional[int] = None              # 가장 제한적인 용적률(%)
    is_mergeable: bool = True                    # 합필 가능 여부
    merge_issues: List[str] = field(default_factory=list)
    failed_parcels: List[str] = field(default_factory=list)  # API 실패한 주소
    summary_markdown: str = ""                   # 분석 결과 마크다운


class LandAPIClient:
    """
    VWorld Data API 기반 토지 정보 클라이언트

    주요 기능:
    - 주소 → 좌표 → 필지 정보 (지목, 면적, PNU) 조회
    - 주소 → 좌표 → 용도지역/지구/구역 조회
    - 다중 필지 일괄 조회 + 통합 요약
    """

    DATA_API_URL = "https://api.vworld.kr/req/data"
    GEOCODER_URL = "https://api.vworld.kr/req/address"

    def __init__(self, api_key: str = None, domain: str = None):
        # API 키 우선순위: 파라미터 > Streamlit secrets > 환경변수
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

        if domain:
            self.domain = domain
        else:
            try:
                import streamlit as st
                self.domain = st.secrets.get("VWORLD_API_DOMAIN")
            except Exception:
                self.domain = None
            if not self.domain:
                self.domain = os.getenv("VWORLD_API_DOMAIN")

        self.timeout = int(os.getenv("VWORLD_API_TIMEOUT", "15"))

        if not self.api_key:
            logger.warning("⚠️ VWORLD_API_KEY 미설정 — 토지 API 조회 불가")

    # ─── 저수준 API 호출 ─────────────────────────────────────────────────

    def _geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """주소 → (경도, 위도) 좌표 반환 (WGS84)"""
        if not self.api_key:
            return None
        try:
            params = {
                "service": "address",
                "request": "GetCoord",
                "version": "2.0",
                "key": self.api_key,
                "crs": "epsg:4326",
                "address": address,
                "type": "PARCEL",  # 지번주소 우선
                "refine": "true",
                "simple": "false",
                "format": "json",
                "errorFormat": "json",
            }
            resp = requests.get(self.GEOCODER_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            result = data.get("response", {})
            if result.get("status") != "OK":
                # 지번 실패 시 도로명으로 재시도
                params["type"] = "ROAD"
                resp2 = requests.get(self.GEOCODER_URL, params=params, timeout=self.timeout)
                resp2.raise_for_status()
                data = resp2.json()
                result = data.get("response", {})
            if result.get("status") == "OK":
                point = result.get("result", {}).get("point", {})
                x = float(point.get("x", 0))
                y = float(point.get("y", 0))
                if x and y:
                    return (x, y)
        except Exception as e:
            logger.debug("지오코딩 실패 [%s]: %s", address, e)
        return None

    # 검증된 VWorld Data API 레이어명
    LAYER_PARCEL = "LT_C_LANDINFOBASEMAP"  # 토지정보기본도: pnu, jimok, parea, jibun
    LAYER_ZONING = "LT_C_UQ111"            # 용도지역: uname
    LAYER_PRICE  = "LT_C_LHSPINFOBASEMAP"  # 표준지공시지가: pblntf_pclnd, stdr_year

    def _get_feature(self, layer: str, x: float, y: float, size: int = 3) -> List[Dict[str, Any]]:
        """VWorld Data API GetFeature 호출 → features 리스트 반환"""
        if not self.api_key:
            return []
        try:
            params = {
                "service": "data",
                "request": "GetFeature",
                "data": layer,
                "key": self.api_key,
                "format": "json",
                "size": size,
                "page": 1,
                "geometry": "false",
                "attribute": "true",
                "crs": "EPSG:4326",
                "geomFilter": f"POINT({x} {y})",
            }
            if self.domain:
                params["domain"] = self.domain

            resp = requests.get(self.DATA_API_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            response_block = data.get("response", {})
            status = response_block.get("status", "")
            if status != "OK":
                err = response_block.get("error", {})
                logger.debug("VWorld Data API [%s] 실패: %s", layer, err.get("text", status))
                return []

            features = response_block.get("result", {}).get("featureCollection", {}).get("features", [])
            return features

        except Exception as e:
            logger.debug("VWorld Data API [%s] 오류: %s", layer, e)
            return []

    # ─── 필지 정보 조회 ──────────────────────────────────────────────────

    def _parse_parcel_feature(self, feat: Dict) -> Dict[str, Any]:
        """LT_C_LANDINFOBASEMAP 피처 → 필지 속성 딕셔너리

        실제 필드: pnu, jimok, parea, jibun, sido_nm, sgg_nm, emd_nm, ri_nm
        """
        props = feat.get("properties", {})

        # 지목명 (예: "대", "전", "답")
        jm_name = props.get("jimok", "")
        # 지목코드 역매핑
        jm_code = next(
            (code for code, name in LAND_CATEGORY_MAP.items() if name == jm_name),
            ""
        )

        try:
            area = float(props.get("parea", 0) or 0)
        except (ValueError, TypeError):
            area = 0.0

        return {
            "pnu": props.get("pnu", ""),
            "jibun": props.get("jibun", ""),
            "area_m2": area,
            "land_category_code": jm_code,
            "land_category_name": jm_name,
        }

    def _parse_zoning_feature(self, feat: Dict) -> Dict[str, Any]:
        """LT_C_UQ111 피처 → 용도지역 속성 딕셔너리

        실제 필드: uname(용도지역명), dyear, dnum, sido_name, sigg_name
        """
        props = feat.get("properties", {})
        zoning_name = props.get("uname", "")
        # "지역" 접미 표준화 (예: "일반상업" → "일반상업지역")
        if zoning_name and not zoning_name.endswith("지역") and not zoning_name.endswith("구역") and not zoning_name.endswith("지구"):
            zoning_name = zoning_name + "지역"
        return {
            "zoning_code": props.get("dnum", ""),
            "zoning": zoning_name,
            "district": None,   # LT_C_UQ111은 용도지역만 제공
            "zone": None,
        }

    def get_parcel_info_by_address(self, address: str) -> ParcelInfo:
        """
        주소로 단일 필지 정보 조회

        Returns:
            ParcelInfo: 지목, 면적, 용도지역 포함 필지 정보
        """
        info = ParcelInfo(address=address)

        # 1. 지오코딩
        coords = self._geocode(address)
        if not coords:
            info.error = f"좌표 변환 실패: '{address}'"
            logger.warning(info.error)
            return info
        info.coordinates = coords
        x, y = coords

        # 2. 토지정보기본도에서 필지 정보 (지목, 면적, PNU)
        parcel_features = self._get_feature(self.LAYER_PARCEL, x, y)
        if parcel_features:
            parsed = self._parse_parcel_feature(parcel_features[0])
            info.pnu = parsed["pnu"]
            info.jibun = parsed["jibun"]
            info.area_m2 = parsed["area_m2"]
            info.land_category_code = parsed["land_category_code"]
            info.land_category_name = parsed["land_category_name"]
            info.data_sources.append(f"VWorld 토지정보기본도({self.LAYER_PARCEL})")
        else:
            logger.debug("토지정보기본도 결과 없음: %s (%.6f, %.6f)", address, x, y)

        # 3. 용도지역 정보
        zoning_features = self._get_feature(self.LAYER_ZONING, x, y)
        if zoning_features:
            parsed_z = self._parse_zoning_feature(zoning_features[0])
            info.zoning_code = parsed_z["zoning_code"]
            info.zoning = parsed_z["zoning"]
            info.district = parsed_z["district"] or None
            info.zone = parsed_z["zone"] or None
            info.data_sources.append(f"VWorld 용도지역({self.LAYER_ZONING})")
        else:
            logger.debug("용도지역 결과 없음: %s (%.6f, %.6f)", address, x, y)

        # 4. 건폐율/용적률 한도 부여
        if info.zoning and info.zoning in ZONING_LIMITS:
            limits = ZONING_LIMITS[info.zoning]
            info.bcr_limit = limits["bcr"]
            info.far_limit = limits["far"]

        # 5. 지목별 건축 가능 여부
        if info.land_category_code:
            info.is_buildable = (info.land_category_code in BUILDABLE_CATEGORIES)

        # 6. 공시지가 (best-effort)
        price_features = self._get_feature(self.LAYER_PRICE, x, y)
        if price_features:
            props = price_features[0].get("properties", {})
            price_raw = (
                props.get("pblntf_pclnd") or
                props.get("indvdl_pclnd") or
                props.get("pclnd")
            )
            if price_raw:
                try:
                    info.official_price_per_m2 = int(float(str(price_raw).replace(",", "")))
                    if info.area_m2:
                        info.official_total_price = int(info.official_price_per_m2 * info.area_m2)
                    info.price_year = str(props.get("stdr_year") or props.get("year") or "")
                    info.data_sources.append(f"VWorld 공시지가({self.LAYER_PRICE})")
                except (ValueError, TypeError):
                    pass

        return info

    # ─── 다중 필지 통합 분석 ─────────────────────────────────────────────

    def get_multi_parcel_data(self, addresses: List[str]) -> MultiParcelResult:
        """
        다수 필지 주소 → 각 필지 조회 → 통합 결과 반환

        Args:
            addresses: 지번주소 또는 도로명주소 목록

        Returns:
            MultiParcelResult: 전체 면적, 용도지역 교차, 합필 가능성 등
        """
        if not addresses:
            return MultiParcelResult(parcels=[], summary_markdown="입력된 주소가 없습니다.")

        parcels: List[ParcelInfo] = []
        failed: List[str] = []

        for addr in addresses:
            addr = addr.strip()
            if not addr:
                continue
            logger.info("필지 조회: %s", addr)
            info = self.get_parcel_info_by_address(addr)
            parcels.append(info)
            if info.error:
                failed.append(addr)

        result = MultiParcelResult(parcels=parcels, failed_parcels=failed)
        result.parcel_count = len(parcels)

        # 면적 합산
        result.total_area_m2 = sum(p.area_m2 or 0 for p in parcels)

        # 지목 목록 (중복 제거)
        cats = [p.land_category_name for p in parcels if p.land_category_name]
        result.all_land_categories = list(dict.fromkeys(cats))

        # 용도지역 목록 (중복 제거)
        zonings = [p.zoning for p in parcels if p.zoning]
        result.all_zonings = list(dict.fromkeys(zonings))

        # 지배 용도지역 (면적 최대 필지 기준)
        area_parcels = [p for p in parcels if p.zoning and p.area_m2]
        if area_parcels:
            result.dominant_zoning = max(area_parcels, key=lambda p: p.area_m2).zoning

        # 최악 용도지역 (가장 제한적)
        if result.all_zonings:
            result.worst_case_zoning = min(
                result.all_zonings,
                key=lambda z: ZONING_RESTRICTIVENESS.get(z, 50)
            )
            if result.worst_case_zoning in ZONING_LIMITS:
                lim = ZONING_LIMITS[result.worst_case_zoning]
                result.worst_bcr = lim["bcr"]
                result.worst_far = lim["far"]

        # 합필 가능성 판단
        result.is_mergeable, result.merge_issues = self._check_mergeability(parcels)

        # 마크다운 요약 생성
        result.summary_markdown = self._build_summary_markdown(result)

        return result

    def _check_mergeability(self, parcels: List[ParcelInfo]) -> Tuple[bool, List[str]]:
        """합필 가능성 판단 (지목 기준)"""
        issues: List[str] = []
        valid = [p for p in parcels if p.land_category_code]

        # 지목 불일치 확인
        unique_codes = set(p.land_category_code for p in valid)
        if len(unique_codes) > 1:
            names = [LAND_CATEGORY_MAP.get(c, c) for c in unique_codes]
            issues.append(
                f"지목 불일치 ({', '.join(names)}) — 합필 전 지목 변경 또는 분리 대장 처리 필요"
            )

        # 건축 불가 지목 포함 여부
        non_build = [p for p in valid if not p.is_buildable]
        if non_build:
            names = [f"{p.address}({p.land_category_name})" for p in non_build]
            issues.append(
                f"건축 제한 지목 포함: {', '.join(names)} — 지목 변경 허가 필요"
            )

        # 용도지역 혼재 확인
        unique_zonings = set(p.zoning for p in parcels if p.zoning)
        if len(unique_zonings) > 1:
            issues.append(
                f"용도지역 혼재 ({', '.join(unique_zonings)}) — 가장 제한적인 기준 적용 검토 필요"
            )

        # 도로 지목 필지 포함 (사실상 도로)
        road_parcels = [p for p in valid if p.land_category_code == "14"]
        if road_parcels:
            issues.append(
                f"도로 지목 필지 포함 ({len(road_parcels)}필지) — 도로로 사용 중인 경우 합필 불가, "
                "폐도 절차 또는 대지 안의 공지 처리 검토"
            )

        return (len(issues) == 0), issues

    def _build_summary_markdown(self, result: MultiParcelResult) -> str:
        """MultiParcelResult → 분석용 마크다운 문자열 생성"""
        lines: List[str] = []
        lines.append("## 📋 필지 구성 API 조회 결과 (VWorld 공공데이터 기반)")
        lines.append("")

        # 전체 요약
        lines.append("### 대지 통합 현황")
        lines.append(f"| 항목 | 내용 |")
        lines.append(f"|------|------|")
        lines.append(f"| 총 필지 수 | {result.parcel_count}필지 |")
        if result.total_area_m2:
            pyeong = result.total_area_m2 / 3.3058
            lines.append(f"| 합산 면적 | {result.total_area_m2:,.1f}㎡ (약 {pyeong:,.0f}평) |")
        else:
            lines.append(f"| 합산 면적 | 조회 불가 |")
        lines.append(f"| 지목 구성 | {', '.join(result.all_land_categories) or '조회 불가'} |")
        lines.append(f"| 용도지역 | {', '.join(result.all_zonings) or '조회 불가'} |")
        if result.worst_case_zoning:
            lines.append(f"| 적용 기준 (최제한) | {result.worst_case_zoning} |")
        if result.worst_bcr is not None:
            lines.append(f"| 건폐율 한도 | {result.worst_bcr}% (국토계획법 시행령 기준) |")
        if result.worst_far is not None:
            lines.append(f"| 용적률 한도 | {result.worst_far}% (국토계획법 시행령 기준) |")
        lines.append("")

        # 필지별 상세
        lines.append("### 필지별 상세")
        lines.append("| 주소 | 지목 | 면적(㎡) | 용도지역 | 건폐율/용적률 | 공시지가(원/㎡) | 데이터 출처 |")
        lines.append("|------|------|----------|----------|--------------|----------------|------------|")
        for p in result.parcels:
            area_str = f"{p.area_m2:,.1f}" if p.area_m2 else "조회 불가"
            zoning_str = p.zoning or "조회 불가"
            limits_str = f"{p.bcr_limit}%/{p.far_limit}%" if p.bcr_limit else "—"
            cat_str = p.land_category_name or "조회 불가"
            price_str = f"{p.official_price_per_m2:,}" if p.official_price_per_m2 else "—"
            src_str = ", ".join(p.data_sources) if p.data_sources else "API 실패"
            err_note = f" ⚠️ {p.error}" if p.error else ""
            lines.append(
                f"| {p.address}{err_note} | {cat_str} | {area_str} | {zoning_str} | {limits_str} | {price_str} | {src_str} |"
            )
        lines.append("")

        # 합필 가능성
        merge_icon = "✅" if result.is_mergeable else "⚠️"
        merge_text = "합필 가능 (현황 기준)" if result.is_mergeable else "합필 시 검토 필요"
        lines.append(f"### 합필 가능성: {merge_icon} {merge_text}")
        if result.merge_issues:
            for issue in result.merge_issues:
                lines.append(f"- {issue}")
        else:
            lines.append("- 지목 동일, 건축 가능 지목, 용도지역 단일 — 기본 합필 조건 충족")
        lines.append("")

        # API 실패 필지 안내
        if result.failed_parcels:
            lines.append("### ⚠️ API 조회 실패 필지")
            lines.append("아래 주소는 좌표 변환 실패로 AI 추론으로 대체됩니다:")
            for addr in result.failed_parcels:
                lines.append(f"- {addr}")
            lines.append("")

        lines.append(
            "> **데이터 출처**: VWorld 토지정보기본도(LT_C_LANDINFOBASEMAP), 용도지역(LT_C_UQ111) — "
            "국토교통부 공공데이터 (실시간 조회, 확정값)"
        )

        return "\n".join(lines)


# ─── 주소 파싱 유틸 ──────────────────────────────────────────────────────────

def extract_parcel_addresses(text: str) -> List[str]:
    """
    프롬프트/텍스트에서 지번주소(다수 포함) 추출

    패턴: '소재지:', '지번:', '위치:' 뒤 주소 / 쉼표·줄바꿈으로 구분된 주소 목록

    예) "소재지: 서울시 강남구 역삼동 123, 124, 역삼동 125"
        → ["서울시 강남구 역삼동 123", "서울시 강남구 역삼동 124", "서울시 강남구 역삼동 125"]
    """
    import re
    addresses: List[str] = []

    # 1. "소재지: 서울시 강남구 역삼동 123, 124, 역삼동 125" 형태
    block_pattern = re.compile(
        r"(?:소재지|지번|부지|위치|대지)\s*[:：]\s*([^\n]+)",
        re.IGNORECASE
    )
    for match in block_pattern.finditer(text):
        raw = match.group(1).strip()
        parts = re.split(r"[,，、및]", raw)
        base_prefix = ""  # 첫 완전한 주소에서 추출한 시/구/동 접두사

        for part in parts:
            part = part.strip()
            if not part:
                continue

            is_full_addr = _is_full_address(part)  # 구/군 이상 행정구역 포함 여부

            if is_full_addr:
                # 완전한 주소: 그대로 사용하고 접두사 갱신
                addresses.append(part)
                base_prefix = _extract_address_prefix(part)
            elif re.search(r"^\d+(-\d+)?(번지)?$", part):
                # 숫자만 있는 경우 (지번만) → 접두사(동까지)에 붙이기
                if base_prefix:
                    jibun = part.replace("번지", "").strip()
                    addresses.append(f"{base_prefix} {jibun}")
            elif _looks_like_address(part):
                if base_prefix:
                    # "역삼동 124" 같이 동+번지만 있는 경우 → 시/구 접두사 붙이기
                    parent_prefix = _extract_city_district_prefix(base_prefix)
                    addresses.append(f"{parent_prefix} {part}" if parent_prefix else part)
                else:
                    addresses.append(part)
                # 이 주소도 base_prefix 갱신 (다음 짧은 주소를 위해)
                new_prefix = _extract_address_prefix(part)
                if new_prefix != part:  # 동/리를 포함한 경우만 업데이트
                    # 단, base_prefix가 있으면 시/구 부분 보존
                    if base_prefix:
                        city_dist = _extract_city_district_prefix(base_prefix)
                        base_prefix = f"{city_dist} {new_prefix}".strip() if city_dist else new_prefix
                    else:
                        base_prefix = new_prefix

    # 2. 줄마다 단독 주소 형태 (줄 전체가 주소처럼 생긴 경우)
    if not addresses:
        for line in text.splitlines():
            line = line.strip()
            if _looks_like_address(line) and len(line) < 60:
                addresses.append(line)

    # 중복 제거 후 반환
    seen: set = set()
    unique: List[str] = []
    for a in addresses:
        if a not in seen:
            seen.add(a)
            unique.append(a)
    return unique


def _extract_address_prefix(address: str) -> str:
    """주소에서 '동/읍/면/리'까지의 접두사 추출 (예: '서울시 강남구 역삼동')"""
    import re
    # 마지막 동/읍/면/리 까지 포함한 부분 추출
    m = re.search(r"^(.+[동읍면리])\s+\d", address)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"^(.+[동읍면리])", address)
    return m2.group(1).strip() if m2 else address.strip()


def _extract_city_district_prefix(dong_prefix: str) -> str:
    """
    동 접두사에서 마지막 동/읍/면/리 단위를 제거해 시/구 수준 접두사 반환

    예) "서울시 강남구 역삼동" → "서울시 강남구"
        "경기도 성남시 분당구 정자동" → "경기도 성남시 분당구"
    """
    import re
    # 마지막 [동읍면리] 토큰을 제거
    # 공백+한글+동/읍/면/리 가 끝에 있는 경우
    result = re.sub(r"\s+[가-힣]+[동읍면리]\s*$", "", dong_prefix).strip()
    return result if result else dong_prefix


def _looks_like_address(text: str) -> bool:
    """텍스트가 한국 주소처럼 생겼는지 간단히 확인"""
    import re
    text = text.strip()
    if len(text) < 4 or len(text) > 80:
        return False
    has_number = bool(re.search(r"\d+", text))
    has_admin = bool(re.search(r"[시도구군읍면동리]", text))
    return has_number and has_admin


def _is_full_address(text: str) -> bool:
    """시/도 레벨 행정구역이 포함된 완전한 주소인지 확인"""
    import re
    return bool(re.search(r"[가-힣]+(특별시|광역시|특별자치시|특별자치도|시|도)\s*[가-힣]", text))


# ─── site_fields 통합 enrichment ─────────────────────────────────────────────

def enrich_site_fields_with_land_api(
    site_fields: Dict[str, Any],
    extra_text: str = "",
) -> Dict[str, Any]:
    """
    기존 site_fields(PDF 추론값)를 VWorld 실제 공공데이터로 덮어쓰기

    - site_address 또는 extra_text에서 지번주소 추출
    - LandAPIClient로 필지별 지목·면적·용도지역 조회
    - site_fields의 핵심 필드(zoning, site_area, restrictions 등)를 확정값으로 교체
    - 이미 enrichment된 경우(land_api_enriched=True)는 스킵

    Returns:
        enriched site_fields dict (실패 시 원본 그대로 반환)
    """
    if not site_fields:
        site_fields = {}

    # 이미 enrichment된 경우 스킵 (캐시 재로드 시 중복 방지)
    if site_fields.get("land_api_enriched"):
        return site_fields

    try:
        client = get_land_api_client()
        if not client.api_key:
            return site_fields

        # ── 주소 추출 ──────────────────────────────────────────────────────
        # 1순위: site_fields["site_address"]
        # 2순위: extra_text(pdf_summary 등)에서 파싱
        addresses: List[str] = []
        site_addr = site_fields.get("site_address", "")
        if site_addr and site_addr not in ("대지 주소 정보 없음", ""):
            # "소재지: ..." 형태가 아니어도 파싱 시도
            parsed = extract_parcel_addresses(f"소재지: {site_addr}")
            if not parsed:
                # 단일 주소 그대로 사용
                from utils.integrations.land_api_client import _looks_like_address
                if _looks_like_address(site_addr):
                    parsed = [site_addr.strip()]
            addresses.extend(parsed)

        if not addresses and extra_text:
            addresses = extract_parcel_addresses(extra_text)

        if not addresses:
            logger.debug("land API enrichment: 추출된 주소 없음, 스킵")
            return site_fields

        logger.info("land API enrichment 시작: %d개 주소", len(addresses))

        # ── API 조회 ───────────────────────────────────────────────────────
        result = client.get_multi_parcel_data(addresses)

        # ── site_fields 업데이트 ───────────────────────────────────────────
        enriched = dict(site_fields)  # 복사

        # 용도지역 (확정값으로 교체)
        if result.worst_case_zoning:
            old_zoning = enriched.get("zoning", "")
            enriched["zoning"] = result.worst_case_zoning
            if result.dominant_zoning and result.dominant_zoning != result.worst_case_zoning:
                enriched["zoning"] += f" (주지역: {result.dominant_zoning})"
            enriched["zoning"] += " [VWorld API 확인]"
            logger.info("용도지역 교체: '%s' → '%s'", old_zoning, enriched["zoning"])

        # 대지면적 (API 확인값으로 교체)
        if result.total_area_m2 and result.total_area_m2 > 0:
            pyeong = result.total_area_m2 / 3.3058
            enriched["site_area"] = (
                f"{result.total_area_m2:,.1f}㎡ (약 {pyeong:,.0f}평, {result.parcel_count}필지 합산) [VWorld API 확인]"
            )

        # 건축 제한 (건폐율/용적률)
        if result.worst_bcr is not None:
            enriched["restrictions"] = (
                f"건폐율 {result.worst_bcr}% 이하 / 용적률 {result.worst_far}% 이하 "
                f"({result.worst_case_zoning} 기준, 국토계획법 시행령) [VWorld API 확인]"
            )

        # 지목
        if result.all_land_categories:
            enriched["land_category"] = ", ".join(result.all_land_categories) + " [VWorld API 확인]"

        # 필지 수
        if result.parcel_count > 0:
            enriched["parcel_count"] = str(result.parcel_count)

        # 합필 이슈
        if result.merge_issues:
            enriched["merge_issues"] = "; ".join(result.merge_issues)

        # 전체 필지 분석 마크다운 (모든 분석 블록에서 참조 가능)
        if result.summary_markdown:
            enriched["land_api_summary"] = result.summary_markdown

        # enrichment 완료 플래그
        enriched["land_api_enriched"] = True

        logger.info(
            "land API enrichment 완료: 면적=%s㎡, 용도지역=%s, 필지=%d개",
            f"{result.total_area_m2:,.1f}" if result.total_area_m2 else "N/A",
            result.worst_case_zoning or "N/A",
            result.parcel_count,
        )
        return enriched

    except Exception as e:
        logger.warning("land API enrichment 실패 (원본 site_fields 사용): %s", e)
        return site_fields


# ─── 싱글톤 ──────────────────────────────────────────────────────────────────

_land_api_client: Optional[LandAPIClient] = None


def get_land_api_client() -> LandAPIClient:
    """LandAPIClient 싱글톤 반환"""
    global _land_api_client
    if _land_api_client is None:
        _land_api_client = LandAPIClient()
    return _land_api_client

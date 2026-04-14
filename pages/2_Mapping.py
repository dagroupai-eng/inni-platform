"""
필지 선택 지도 페이지

VWorld WFS(연속지적도 polygon) + Data API(속성) 연동:
- 지도 클릭 → 즉시 필지 경계 polygon 하이라이트
- 여러 필지 클릭 → 색상 구분된 polygon 다중 표시
- 선택 목록 → "분석에 활용" → session_state 주입
"""

import logging
import os
import streamlit as st
from typing import Optional, Tuple, Union

logger = logging.getLogger(__name__)

# .env 로드 (pages/* 직접 실행 시에도 환경변수 확보)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# 세션 초기화 및 인증 확인
try:
    from auth.session_init import init_page_session
    from auth.authentication import check_page_access
    init_page_session()
    check_page_access()
except Exception:
    pass

# ─── VWorld 레이어 ────────────────────────────────────────────────────────────
LAYER_PARCEL   = "LT_C_LANDINFOBASEMAP"  # 토지정보기본도
LAYER_ZONING   = "LT_C_UQ111"           # 용도지역
LAYER_DISTRICT = "LT_C_UQ121"           # 용도지구
LAYER_ZONE     = "LT_C_UQ131"           # 용도구역
LAYER_JIGUDAN  = "LT_C_NSDI_JIGUDAN"   # 지구단위계획구역
WFS_TYPENAME   = "lp_pa_cbnd_bubun"     # 연속지적도 (polygon) — VWorld WFS 소문자

# 건축HUB 클라이언트 (선택적 — KHUG_API_KEY 없으면 VWorld fallback 사용)
try:
    from utils.integrations.building_registry_client import get_jiguinfo, get_building_info
    _BLDG_HUB_AVAILABLE = True
except ImportError:
    _BLDG_HUB_AVAILABLE = False

DEFAULT_CENTER = [37.5665, 126.9780]
DEFAULT_ZOOM   = 17

# 선택 필지 polygon 색상 팔레트 (파란 계열)
PARCEL_COLORS = [
    "#1a73e8", "#0d47a1", "#1565c0", "#1976d2",
    "#1e88e5", "#2196f3", "#42a5f5", "#64b5f6",
]
PREVIEW_COLOR = "#ff6d00"   # 미리보기 (클릭 직후) → 주황


# ─── 주소 파싱/포맷 ────────────────────────────────────────────────────────────

# 배치 검색: (전체 주소 문자열, 사용자가 적은 지목 힌트 또는 None)
ParcelAddrEntry = Tuple[str, Optional[str]]


def _strip_category_with_hint(raw: str) -> Tuple[str, Optional[str]]:
    """
    지번 끝 지목 한글 접미 추출 후 제거.
    "산12-1임" → ("산12-1", "임"), "127-1잡" → ("127-1", "잡")
    """
    import re
    raw = raw.strip().replace('번지', '').strip()
    m = re.search(r'(?<=[0-9])([가-힣]+)$', raw)
    if m:
        hint = m.group(1)
        lot = raw[: m.start(1)].strip()
        return lot, hint
    return raw, None


def _normalize_pending_addr(item: Union[str, ParcelAddrEntry]) -> ParcelAddrEntry:
    """세션 등 문자열/튜플 혼입 시 (주소, 지목힌트)로 통일."""
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return str(item[0]).strip(), (str(item[1]).strip() if item[1] else None)
    if isinstance(item, (list, tuple)) and len(item) == 1:
        return str(item[0]).strip(), None
    return str(item).strip(), None


def _normalize_san_spacing(s: str) -> str:
    """'산 110-2' → '산110-2' (VWorld·WFS와 동일하게 맞춤)"""
    import re
    return re.sub(r'^산\s+', '산', (s or '').strip())


def _parse_batch_parcel_input(text: str) -> list[ParcelAddrEntry]:
    """
    쉼표 구분 다중 지번 입력을 (전체 주소, 지목 힌트) 리스트로 변환.

    입력 예:
      "강원특별자치도 삼척시 도계읍 산12-1임, 산12-3임, 127-1잡, 130-2철, 131-3대, 129-3대"
    출력:
      [("강원특별자치도 삼척시 도계읍 산12-1", "임"),
       ("강원특별자치도 삼척시 도계읍 산12-3", "임"),
       ("강원특별자치도 삼척시 도계읍 127-1", "잡"),
       ...]

    - 지번 끝 지목 코드(임·대·전·답·잡·철 등 한글 접미)는 주소에서는 제거하되 힌트로 보관
    - 읍/면/동/리/가 모두 베이스 주소 기준점으로 지원
    - **면 아래 리**가 있으면 베이스에 `OO리`까지 포함(이어지는 지번에 리가 빠지지 않게 함)
    - 쉼표 없는 단일 주소는 [(text, None)] 반환
    """
    import re
    text = text.strip()
    if not text:
        return []

    parts = [p.strip() for p in text.split(',') if p.strip()]
    if len(parts) <= 1:
        return [(text, None)]

    # 첫 번째 파트: …면/읍/동 + (선택) OO리 + 첫 지번
    first = parts[0]
    m = re.match(
        r'^(?P<base_prefix>.*?(\S+(?:읍|면|동|리|가)))'
        r'(?P<after_li>\s+\S+리)?'
        r'\s+(?P<first_lot>(?:산\s*)?[\d\-].*)$',
        first.strip(),
    )
    if not m:
        # 행정단위 인식 불가 → 기존 파서로 위임
        return [(s, None) for s in _parse_multi_parcel_address(text)]

    base = (m.group("base_prefix").strip() + (m.group("after_li") or "")).strip()
    first_lot_raw = _normalize_san_spacing(m.group("first_lot").strip())

    results: list[ParcelAddrEntry] = []
    for lot_raw in [first_lot_raw] + parts[1:]:
        lot_raw = _normalize_san_spacing(lot_raw)
        lot_clean, hint = _strip_category_with_hint(lot_raw)
        if lot_clean:
            results.append((f"{base} {lot_clean}", hint))

    return results if results else [(text, None)]


def _parse_multi_parcel_address(text: str) -> list:
    """
    "서울특별시 강남구 논현동 16, 16-7, 16-16번지" → 개별 주소 리스트
    단일 주소는 [주소] 로 반환.
    "외 N필지" 접미사는 앞 주소만 추출.
    """
    import re
    text = text.strip()
    if not text:
        return []
    # "외 N필지" → 이미 로드된 포맷, 첫 주소만
    if re.search(r'외\s*\d+필지', text):
        return [re.sub(r'\s*외\s*\d+필지.*$', '', text).strip()]
    # 동/리/가 + 콤마 구분 지번들 패턴
    m = re.match(r'^(.*?[동리가])\s+([\d\-,\s]+번지.*)$', text)
    if m:
        base = m.group(1).strip()
        lots_str = m.group(2).replace('번지', '').strip()
        lots = [l.strip() for l in lots_str.split(',') if re.match(r'[\d\-]+$', l.strip())]
        if len(lots) > 1:
            return [f"{base} {lot}번지" for lot in lots]
    return [text]


def _format_parcel_addresses(addresses: list) -> str:
    """
    ["서울특별시 강남구 논현동 16 대", "...16-7 대", ...] →
    "서울특별시 강남구 논현동 16, 16-7번지"
    같은 동끼리 묶고, 다른 동은 " / "로 구분.
    """
    import re
    from collections import OrderedDict
    if not addresses:
        return ""
    if len(addresses) == 1:
        # 단일: 지목 제거하고 "번지" 붙이기
        m = re.match(r'^(.*?[동리가])\s+([\d\-]+)', addresses[0].strip())
        if m:
            return f"{m.group(1).strip()} {m.group(2)}번지"
        return addresses[0]

    groups: dict = OrderedDict()
    unmatched = []
    for addr in addresses:
        m = re.match(r'^(.*?[동리가])\s+([\d\-]+)', addr.strip())
        if m:
            base, lot = m.group(1).strip(), m.group(2)
            groups.setdefault(base, []).append(lot)
        else:
            unmatched.append(addr.strip())

    sep = ", "
    parts = [f"{base} {sep.join(lots)}번지" for base, lots in groups.items()]
    parts.extend(unmatched)
    return " / ".join(parts)


# ─── API 함수 ─────────────────────────────────────────────────────────────────

def _api_key() -> str:
    return os.getenv("VWORLD_API_KEY", "")

def _domain() -> Optional[str]:
    return os.getenv("VWORLD_DOMAIN") or os.getenv("VWORLD_API_DOMAIN") or None

def _vworld_get(url: str, params: dict, timeout: int = 10):
    """VWorld API GET 요청 — 서울 리전 서버에서 직접 호출"""
    import requests
    return requests.get(url, params=params, timeout=timeout)


def _geocode(address: str) -> Optional[tuple]:
    """주소 → (lon, lat)"""
    import requests
    key = _api_key()
    for addr_type in ("PARCEL", "ROAD"):
        try:
            r = _vworld_get(
                "https://api.vworld.kr/req/address",
                {
                    "service": "address", "request": "GetCoord", "version": "2.0",
                    "key": key, "crs": "epsg:4326", "address": address,
                    "type": addr_type, "refine": "true", "simple": "false",
                    "format": "json", "errorFormat": "json",
                },
                timeout=10,
            )
            r.raise_for_status()
            resp = r.json().get("response", {})
            if resp.get("status") == "OK":
                pt = resp["result"]["point"]
                return float(pt["x"]), float(pt["y"])
        except Exception:
            pass
    return None


def _parcel_geocode_variants(address: str, expected_jimok: Optional[str]) -> list[str]:
    """
    지번지 주소(지목 제거된 문자열)에 대해 VWorld PARCEL 지오코딩에 넘길 변형 목록.
    - '번지' 접미: 지번지 API에 흔한 표기(예: 근덕면 산110-2번지)라 베이스마다 함께 시도한다.
    - 지목: '산110-2 임' / '산110-2임' 형태를 번지 유무 각각에 대해 먼저 시도한다.
    """
    a = (address or "").strip()
    if not a:
        return []
    jm = (expected_jimok or "").strip()

    def _bases(addr: str) -> list[str]:
        b = [addr]
        tail = addr.rstrip()
        if not tail.endswith("번지"):
            b.append(f"{addr}번지")
            b.append(f"{addr} 번지")
        return b

    def _append_jimok_variants(out_list: list[str], base: str) -> None:
        if jm and not base.endswith(jm):
            out_list.append(f"{base} {jm}")
            out_list.append(f"{base}{jm}")
        out_list.append(base)

    out: list[str] = []
    for base in _bases(a):
        _append_jimok_variants(out, base)

    seen: set[str] = set()
    uniq: list[str] = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def _geocode_parcel_first_hit(address: str, expected_jimok: Optional[str]) -> Optional[tuple]:
    """지번+지목 변형을 순서대로 시도해 첫 성공 좌표만 반환."""
    for cand in _parcel_geocode_variants(address, expected_jimok):
        c = _geocode(cand)
        if c:
            return c
    return None


def _get_land_characteristics(pnu: str) -> dict:
    """
    VWorld NED 토지특성속성조회 (getLandCharacteristics)
    PNU → 지형높이, 지형형상, 도로접면, 토지이용상황, 용도지역(보완용)
    """
    import requests
    key = _api_key()
    if not key or not pnu:
        return {}
    params = {
        "pnu": pnu, "key": key,
        "format": "json", "numOfRows": "1", "pageNo": "1",
    }
    dom = _domain()
    if dom:
        params["domain"] = dom
    try:
        r = _vworld_get(
            "https://api.vworld.kr/ned/data/getLandCharacteristics",
            params, timeout=10,
        )
        r.raise_for_status()
        raw = r.content.decode("utf-8")
        import json as _json
        data = _json.loads(raw)

        # 응답 형식 1: {"getLandCharacteristics": {"row": [...], ...}}
        root = data.get("getLandCharacteristics", {})
        rows = root.get("row") or root.get("rows") or []
        if not rows and root.get("totalCnt", "0") == "0":
            logger.debug("getLandCharacteristics: 데이터 없음 (pnu=%s)", pnu)
            return {}

        # 응답 형식 2: {"response": {"result": {"featureCollection": {...}}}}
        if not rows:
            feats = (data.get("response", {}).get("result", {})
                     .get("featureCollection", {}).get("features", []))
            if feats:
                rows = [feats[0].get("properties", {})]

        if not rows:
            return {}

        row = rows[0] if isinstance(rows, list) else rows
        result = {}
        skip = {"지정되지않음", "해당없음", "0", "", "null", "None"}
        for src, dst in [
            ("tpgrphHgCodeNm",  "terrain_height"),  # 지형높이
            ("tpgrphFrmCodeNm", "terrain_shape"),   # 지형형상
            ("roadSideCodeNm",  "road_side"),        # 도로접면
            ("ladUseSittnNm",   "land_use_status"),  # 토지이용상황
            ("prposArea1Nm",    "zoning_ned"),       # 용도지역명1 (보완용)
        ]:
            v = str(row.get(src) or "").strip()
            if v and v not in skip:
                result[dst] = v
        return result
    except Exception as e:
        logger.debug("getLandCharacteristics 오류 (pnu=%s): %s", pnu, e)
        return {}


def _get_indvd_land_price(pnu: str) -> list:
    """
    VWorld NED 개별공시지가 조회 (getIndvdLandPrice, AL_D150)
    PNU → 최근 5개년 공시지가 이력
    Returns list of {"year": "2024", "price": 5420000}
    """
    import requests, json as _json
    key = _api_key()
    if not key or not pnu:
        return []
    params = {
        "pnu": pnu, "key": key,
        "format": "json", "numOfRows": "5", "pageNo": "1",
    }
    dom = _domain()
    if dom:
        params["domain"] = dom
    try:
        r = _vworld_get(
            "https://api.vworld.kr/ned/data/getIndvdLandPrice",
            params, timeout=10,
        )
        r.raise_for_status()
        data = _json.loads(r.content.decode("utf-8"))
        root = data.get("getIndvdLandPrice", {})
        rows = root.get("row") or root.get("rows") or []
        if not rows:
            return []
        result = []
        for row in (rows if isinstance(rows, list) else [rows]):
            year = str(row.get("stdrYear") or row.get("stdr_year") or "").strip()
            price_raw = row.get("pblntfPclnd") or row.get("pblntf_pclnd") or ""
            try:
                price = int(float(str(price_raw).replace(",", "")))
            except (ValueError, TypeError):
                price = None
            if year and price:
                result.append({"year": year, "price": price})
        result.sort(key=lambda x: x["year"], reverse=True)
        return result[:5]
    except Exception as e:
        logger.debug("getIndvdLandPrice 오류 (pnu=%s): %s", pnu, e)
        return []


def _get_price_change_rate(sigungu_code: str) -> Optional[dict]:
    """
    VWorld NED 지역별 지가변동률 조회 (getChangeRateByRegion, AL_D203)
    sigungu_code (5자리) → 최근 지가변동률(%)
    Returns {"rate": 2.5, "year": "2024", "period": "3/4"} or None
    """
    import requests, json as _json
    key = _api_key()
    if not key or not sigungu_code or len(sigungu_code) < 5:
        return None
    params = {
        "sigunguCd": sigungu_code[:5], "key": key,
        "format": "json", "numOfRows": "1", "pageNo": "1",
    }
    dom = _domain()
    if dom:
        params["domain"] = dom
    try:
        r = _vworld_get(
            "https://api.vworld.kr/ned/data/getChangeRateByRegion",
            params, timeout=10,
        )
        r.raise_for_status()
        data = _json.loads(r.content.decode("utf-8"))
        root = data.get("getChangeRateByRegion", {})
        rows = root.get("row") or root.get("rows") or []
        if not rows:
            return None
        row = rows[0] if isinstance(rows, list) else rows
        rate_raw = (row.get("chgRt") or row.get("chg_rt")
                    or row.get("changeRate") or row.get("change_rate") or "")
        try:
            rate = float(str(rate_raw).replace(",", ""))
        except (ValueError, TypeError):
            return None
        year   = str(row.get("stdrYear") or row.get("stdr_year") or "").strip()
        period = str(row.get("stdrMt") or row.get("stdr_mt") or "").strip()
        return {"rate": rate, "year": year, "period": period}
    except Exception as e:
        logger.debug("getChangeRateByRegion 오류 (sigungu=%s): %s", sigungu_code, e)
        return None


def _get_parcel_building_wfs(lon: float, lat: float, pnu: str) -> dict:
    """
    VWorld NED getBuildingUseWFS — 선택 필지 건물 상세 (주차 포함, AL_D162/164)
    소반경(50m)으로 조회 후 PNU 매칭
    Returns dict: total_park_co, total_park_ar, wfs_* fields or {}
    """
    import requests, json as _json
    key = _api_key()
    if not key:
        return {}
    d = 50 / 111_000
    bbox = f"{lat-d},{lon-d},{lat+d},{lon+d},EPSG:4326"
    params = {
        "key": key, "bbox": bbox,
        "maxFeatures": "20", "resultType": "results",
        "srsName": "EPSG:4326", "output": "application/json",
    }
    dom = _domain()
    if dom:
        params["domain"] = dom
    try:
        r = _vworld_get(
            "https://api.vworld.kr/ned/wfs/getBuildingUseWFS",
            params, timeout=10,
        )
        r.raise_for_status()
        feats = _json.loads(r.content.decode("utf-8")).get("features", [])
        match = next((f for f in feats if f.get("properties", {}).get("pnu") == pnu), None)
        if not match and feats:
            match = feats[0]
        if not match:
            return {}
        props = match.get("properties", {})
        result = {}
        # 주차 정보 (필드명 후보 다양하게 시도)
        park_co = (props.get("total_park_co") or props.get("totParkCo")
                   or props.get("tprkCo") or props.get("parkingCo"))
        park_ar = (props.get("total_park_ar") or props.get("totParkAr")
                   or props.get("tprkAr") or props.get("parkingAr"))
        if park_co:
            try:
                v = int(float(str(park_co)))
                if v > 0:
                    result["total_park_co"] = v
            except (ValueError, TypeError):
                pass
        if park_ar:
            try:
                v = float(str(park_ar))
                if v > 0:
                    result["total_park_ar"] = v
            except (ValueError, TypeError):
                pass
        # 건물 기본 필드 (건축HUB 데이터 보완용)
        skip = {"0", "null", "None", ""}
        for src, dst in [
            ("buld_nm",            "wfs_buld_nm"),
            ("main_prpos_code_nm", "wfs_main_prpos"),
            ("buld_totar",         "wfs_total_area"),
            ("ground_floor_co",    "wfs_floors_above"),
            ("undgrnd_floor_co",   "wfs_floors_below"),
            ("use_confm_de",       "wfs_approve_date"),
            ("strct_code_nm",      "wfs_structure"),
        ]:
            v = str(props.get(src) or "").strip()
            if v and v not in skip:
                result[dst] = v
        return result
    except Exception as e:
        logger.debug("getBuildingUseWFS (parcel detail) 오류: %s", e)
        return {}


def _get_land_ownership(pnu: str) -> dict:
    """
    VWorld NED 토지소유정보 (AL_D160)
    PNU → 소유구분, 공유인수, 소유권변동원인/일자, 거주지구분, 연령대
    Returns dict or {}
    """
    import requests, json as _json
    key = _api_key()
    if not key or not pnu:
        return {}
    params = {"pnu": pnu, "key": key, "format": "json", "numOfRows": "1", "pageNo": "1"}
    dom = _domain()
    if dom:
        params["domain"] = dom
    try:
        r = _vworld_get(
            "https://api.vworld.kr/ned/data/getLandOwnership",
            params, timeout=10,
        )
        r.raise_for_status()
        data = _json.loads(r.content.decode("utf-8"))
        root = data.get("getLandOwnership", {})
        rows = root.get("row") or root.get("rows") or []
        if not rows:
            return {}
        row = rows[0] if isinstance(rows, list) else rows
        result = {}
        skip = {"", "null", "None", "해당없음", "지정되지않음"}
        for src, dst in [
            ("ownshipGbNm",    "ownership_type"),   # 소유구분명
            ("sharedCo",       "shared_count"),     # 공유인수
            ("ownshipChgCauseNm", "change_cause"),  # 소유권변동원인
            ("ownshipChgDe",   "change_date"),      # 소유권변동일자
            ("resdncGbNm",     "residence_type"),   # 거주지구분
            ("agGbNm",         "age_group"),        # 연령대구분
            ("ntnlInsttGbNm",  "gov_agency"),       # 국가기관구분
        ]:
            v = str(row.get(src) or "").strip()
            if v and v not in skip:
                result[dst] = v
        # 공유인수 숫자 변환
        if result.get("shared_count"):
            try:
                result["shared_count"] = int(float(result["shared_count"]))
            except (ValueError, TypeError):
                result.pop("shared_count", None)
        return result
    except Exception as e:
        logger.debug("getLandOwnership 오류 (pnu=%s): %s", pnu, e)
        return {}


def _get_gis_building(lon: float, lat: float, pnu: str) -> dict:
    """
    VWorld NED GIS건물통합정보 (AL_D010)
    좌표 기준 조회 → PNU 매칭 → 건물 높이, 위반건축물여부, 대지면적 등
    Returns dict or {}
    """
    import requests, json as _json
    key = _api_key()
    if not key:
        return {}
    d = 50 / 111_000
    bbox = f"{lat-d},{lon-d},{lat+d},{lon+d},EPSG:4326"
    params = {
        "key": key, "bbox": bbox,
        "maxFeatures": "20", "resultType": "results",
        "srsName": "EPSG:4326", "output": "application/json",
    }
    dom = _domain()
    if dom:
        params["domain"] = dom
    try:
        r = _vworld_get(
            "https://api.vworld.kr/ned/wfs/getGISBuildingWFS",
            params, timeout=10,
        )
        r.raise_for_status()
        feats = _json.loads(r.content.decode("utf-8")).get("features", [])
        match = next((f for f in feats if f.get("properties", {}).get("pnu") == pnu
                      or f.get("properties", {}).get("A2") == pnu), None)
        if not match and feats:
            match = feats[0]
        if not match:
            return {}
        props = match.get("properties", {})
        result = {}
        skip = {"0", "0.0", "null", "None", ""}
        # 높이
        hgt = props.get("buld_hg") or props.get("A16") or props.get("height")
        if hgt:
            try:
                v = float(str(hgt))
                if v > 0:
                    result["building_height"] = v
            except (ValueError, TypeError):
                pass
        # 위반건축물여부
        vio = str(props.get("vltBldgYn") or props.get("A20") or props.get("illegal_yn") or "").strip()
        if vio and vio not in skip:
            result["illegal_building"] = vio
        # 대지면적
        site_ar = props.get("platArea") or props.get("A15") or props.get("site_area")
        if site_ar:
            try:
                v = float(str(site_ar))
                if v > 0:
                    result["gis_site_area"] = v
            except (ValueError, TypeError):
                pass
        # 건물명 (보완용)
        for k in ("buldNm", "A24", "buld_nm", "building_nm"):
            v = str(props.get(k) or "").strip()
            if v and v not in skip:
                result["gis_bld_name"] = v
                break
        # 지상/지하층수 (보완용)
        for k in ("grndFlrCnt", "A26", "ground_floor_co"):
            v = str(props.get(k) or "").strip()
            if v and v not in skip and v != "0":
                result["gis_floors_above"] = v
                break
        for k in ("ugrndFlrCnt", "A27", "undgrnd_floor_co"):
            v = str(props.get(k) or "").strip()
            if v and v not in skip and v != "0":
                result["gis_floors_below"] = v
                break
        return result
    except Exception as e:
        logger.debug("getGISBuildingWFS 오류: %s", e)
        return {}


def _get_std_land_price(pnu: str) -> dict:
    """
    VWorld NED 표준지공시지가정보 (AL_D152)
    PNU → 기준연도, 공시지가, 과년도 1~4년 이력
    Returns {"year": "2024", "price": 5800000, "history": [...]} or {}
    """
    import requests, json as _json
    key = _api_key()
    if not key or not pnu:
        return {}
    params = {"pnu": pnu, "key": key, "format": "json", "numOfRows": "1", "pageNo": "1"}
    dom = _domain()
    if dom:
        params["domain"] = dom
    try:
        r = _vworld_get(
            "https://api.vworld.kr/ned/data/getStanddLandPrice",
            params, timeout=10,
        )
        r.raise_for_status()
        data = _json.loads(r.content.decode("utf-8"))
        root = data.get("getStanddLandPrice", {})
        rows = root.get("row") or root.get("rows") or []
        if not rows:
            return {}
        row = rows[0] if isinstance(rows, list) else rows
        result = {}
        # 기준연도/월
        year = str(row.get("stdrYear") or row.get("A7") or "").strip()
        if year:
            result["year"] = year
        # 당해 공시지가
        price_raw = row.get("pblntfPclnd") or row.get("A9") or ""
        try:
            price = int(float(str(price_raw).replace(",", "")))
            if price > 0:
                result["price"] = price
        except (ValueError, TypeError):
            pass
        # 과년도 1~4년
        history = []
        try:
            yr_int = int(year) if year else 0
        except (ValueError, TypeError):
            yr_int = 0
        for i, field in enumerate(["A25", "A26", "A27", "A28"], 1):
            raw = row.get(field) or row.get(f"pastYrPclnd{i}") or ""
            try:
                p = int(float(str(raw).replace(",", "")))
                if p > 0:
                    hist_yr = str(yr_int - i) if yr_int else f"과년도{i}"
                    history.append({"year": hist_yr, "price": p})
            except (ValueError, TypeError):
                pass
        if history:
            result["history"] = history
        return result
    except Exception as e:
        logger.debug("getStanddLandPrice 오류 (pnu=%s): %s", pnu, e)
        return {}


def _get_land_use_plan(pnu: str) -> dict:
    """
    VWorld NED 토지이용계획정보 (AL_D155)
    PNU → 용도지역지구명목록, 저촉여부목록
    Returns {"entries": [{"name": "제2종일반주거지역", "conflict": "저촉"},...]} or {}
    """
    import requests, json as _json
    key = _api_key()
    if not key or not pnu:
        return {}
    params = {"pnu": pnu, "key": key, "format": "json", "numOfRows": "1", "pageNo": "1"}
    dom = _domain()
    if dom:
        params["domain"] = dom
    try:
        r = _vworld_get(
            "https://api.vworld.kr/ned/data/getLandUsePlan",
            params, timeout=10,
        )
        r.raise_for_status()
        data = _json.loads(r.content.decode("utf-8"))
        root = data.get("getLandUsePlan", {})
        rows = root.get("row") or root.get("rows") or []
        if not rows:
            return {}
        row = rows[0] if isinstance(rows, list) else rows
        # 용도지역지구명목록 (A8), 저촉여부목록 (A10) — 쉼표 구분
        names_raw   = str(row.get("prposAreaNmList") or row.get("A8") or "").strip()
        conflict_raw = str(row.get("tchgYnList") or row.get("A10") or "").strip()
        if not names_raw:
            return {}
        names     = [n.strip() for n in names_raw.split(",") if n.strip()]
        conflicts = [c.strip() for c in conflict_raw.split(",") if c.strip()]
        entries = []
        for i, nm in enumerate(names):
            conf = conflicts[i] if i < len(conflicts) else ""
            entries.append({"name": nm, "conflict": conf})
        return {"entries": entries, "source": "AL_D155"}
    except Exception as e:
        logger.debug("getLandUsePlan 오류 (pnu=%s): %s", pnu, e)
        return {}


def _fetch_nearby_buildings(lon: float, lat: float, radius_m: int = 500) -> list:
    """
    VWorld NED 용도별건물WFS조회 (getBuildingUseWFS)
    중심 좌표 기준 radius_m 반경 내 건물 목록 반환

    Returns list of dicts: pnu, buld_nm, main_prpos_code_nm, buld_totar, measrmt_rt,
                           btl_rt, ground_floor_co, use_confm_de, total_park_co, total_park_ar
    """
    import requests, json as _json
    key = _api_key()
    if not key:
        return []

    # radius_m → 위경도 delta (1도 ≈ 111km)
    d = radius_m / 111_000
    # EPSG:4326 → ymin,xmin,ymax,xmax
    bbox = f"{lat-d},{lon-d},{lat+d},{lon+d},EPSG:4326"

    # 반경에 비례해 maxFeatures 조정 (최대 1000, 최소 200)
    max_features = min(1000, max(200, radius_m // 2))
    params = {
        "key": key, "bbox": bbox,
        "maxFeatures": str(max_features), "resultType": "results",
        "srsName": "EPSG:4326", "output": "application/json",
    }
    dom = _domain()
    if dom:
        params["domain"] = dom
    try:
        r = _vworld_get(
            "https://api.vworld.kr/ned/wfs/getBuildingUseWFS",
            params, timeout=15,
        )
        r.raise_for_status()
        feats = _json.loads(r.content.decode("utf-8")).get("features", [])
        buildings = []
        for f in feats:
            p = f.get("properties", {})
            bld = {k: p.get(k, "") for k in [
                "pnu", "buld_nm", "main_prpos_code_nm", "detail_prpos_code_nm",
                "buld_totar", "buld_bildng_ar", "measrmt_rt", "btl_rt",
                "ground_floor_co", "undgrnd_floor_co", "strct_code_nm",
                "use_confm_de", "buld_hg",
                "total_park_co", "total_park_ar",
            ]}
            # 중심 좌표 (geometry centroid 근사)
            geom = f.get("geometry", {})
            bld["geometry"] = geom
            buildings.append(bld)
        return buildings
    except Exception as e:
        logger.debug("getBuildingUseWFS 오류: %s", e)
        return []


def _get_feature(layer: str, lon: float, lat: float) -> list:
    """VWorld Data API GetFeature → features 리스트"""
    import requests
    params = {
        "service": "data", "request": "GetFeature", "data": layer,
        "key": _api_key(), "format": "json", "size": 5, "page": 1,
        "geometry": "false", "attribute": "true", "crs": "EPSG:4326",
        "geomFilter": f"POINT({lon} {lat})",
    }
    dom = _domain()
    if dom:
        params["domain"] = dom
    try:
        r = _vworld_get("https://api.vworld.kr/req/data", params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("response", {}).get("status") != "OK":
            return []
        return data["response"]["result"]["featureCollection"]["features"]
    except Exception as e:
        print(f"[VWorld Data API] {layer} 오류: {type(e).__name__}: {e}")
        return []


def _point_in_ring(lon: float, lat: float, ring: list) -> bool:
    """Ray casting: (lon,lat) ∈ ring (list of [lon,lat] pairs)"""
    inside = False
    j = len(ring) - 1
    for i, (xi, yi) in enumerate(ring):
        xj, yj = ring[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geom(lon: float, lat: float, geom: dict) -> bool:
    """Check if (lon,lat) is inside a GeoJSON Polygon or MultiPolygon"""
    gtype = geom.get("type", "")
    coords = geom.get("coordinates", [])
    if gtype == "Polygon":
        return bool(coords) and _point_in_ring(lon, lat, coords[0])
    if gtype == "MultiPolygon":
        return any(_point_in_ring(lon, lat, poly[0]) for poly in coords if poly)
    return False


def _polygon_centroid(geom: dict) -> tuple:
    """GeoJSON Polygon/MultiPolygon → (lon, lat) bbox 중심점"""
    gtype = geom.get("type", "")
    coords = geom.get("coordinates", [])
    ring = []
    if gtype == "Polygon" and coords:
        ring = coords[0]
    elif gtype == "MultiPolygon" and coords:
        ring = coords[0][0]
    if not ring:
        return None, None
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    return (min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2


def _parse_jibun_address(address: str) -> Optional[tuple]:
    """
    WFS CQL·지번 매칭용: (sig_nm, emd_nm, 지번번호부만, ri_nm 또는 None)

    - "… 삼척시 근덕면 부남리 산109-1" → ("삼척시", "근덕면", "산109-1", "부남리")
    - "… 근덕면 산108-2" → ("삼척시", "근덕면", "산108-2", None)
    면 단위 다음에 `OO리`가 오면 WFS ri_nm 조회에 쓴다.
    """
    import re
    address = address.strip()
    sig_nm: Optional[str] = None
    m = re.match(r'^.*?(\S+(?:시|군|구))\s+(\S+(?:읍|면|동|리|가))\s+(.+)$', address)
    if m:
        sig_nm = m.group(1).strip()
        emd_nm = m.group(2).strip()
        remainder = m.group(3).strip()
    else:
        m2 = re.match(r'^.*?(\S+(?:읍|면|동|리|가))\s+(.+)$', address)
        if not m2:
            return None
        emd_nm = m2.group(1).strip()
        remainder = m2.group(2).strip()

    remainder = re.sub(r'^산\s+', '산', remainder)

    ri_nm: Optional[str] = None
    if emd_nm.endswith('면'):
        mri = re.match(r'^(\S+리)\s+(.+)$', remainder)
        if mri:
            ri_nm = mri.group(1).strip()
            remainder = re.sub(r'^산\s+', '산', mri.group(2).strip())

    jibun_num = remainder.strip()
    if not jibun_num:
        return None
    return (sig_nm, emd_nm, jibun_num, ri_nm)


def _wfs_jibun_num_jimok(props: dict) -> Tuple[str, str]:
    """WFS properties → (지번번호부, 지목부) 예: '산108-2 임' → ('산108-2', '임')"""
    jr = (props.get("jibun") or "").strip()
    parts = jr.split()
    num = parts[0] if parts else ""
    jim = parts[1] if len(parts) > 1 else ""
    return num, jim


def _pick_wfs_candidates(
    feats: list,
    jibun_num: str,
    expected_jimok: Optional[str],
    expected_ri_nm: Optional[str] = None,
) -> list:
    """
    지번 번호부 정확 일치 후보를 모은 뒤, 지목 힌트로 좁히고 PNU로 정렬.
    지목 필터로 0건이면 지목 없이 재시도.
    일반지번(산 없음) 검색 시 WFS '산…' 번지는 제외해 오매칭을 줄인다.
    expected_ri_nm: 면 하위 리가 있으면 WFS ri_nm과 일치하는 후보만 남긴다.
    """
    want_jm = (expected_jimok or "").strip()
    want_ri = (expected_ri_nm or "").strip()
    req_san = jibun_num.startswith("산")

    def _san_ok(wfs_jn: str) -> bool:
        wfs_san = wfs_jn.startswith("산")
        if req_san:
            return wfs_san
        # 요청에 산이 없으면 산지번 후보는 배제 (67-1 vs 산67-1)
        return not wfs_san

    cands = [
        f for f in feats
        if _wfs_jibun_num_jimok(f.get("properties", {}))[0] == jibun_num
        and _san_ok(_wfs_jibun_num_jimok(f.get("properties", {}))[0])
    ]
    if want_jm:
        filtered = [f for f in cands if _wfs_jibun_num_jimok(f.get("properties", {}))[1] == want_jm]
        if filtered:
            cands = filtered
    if want_ri:
        by_ri = [
            f for f in cands
            if str((f.get("properties") or {}).get("ri_nm") or "").strip() == want_ri
        ]
        if by_ri:
            cands = by_ri
    cands.sort(key=lambda f: (f.get("properties") or {}).get("pnu") or "")
    return cands


def _fetch_parcel_by_jibun(
    address: str,
    nearby_radius: int = 500,
    expected_jimok: Optional[str] = None,
) -> Optional[dict]:
    """
    지번 주소 → 정확한 필지 조회.

    geocode 후 넓은 BBOX로 WFS 후보를 받아, 지번 번호부·지목 힌트로 후보를 좁힌 뒤
    PNU 정렬로 결정적으로 1건을 고른다. BBOX에 없으면 CQL 필터로 재시도.
    """
    import json as _json

    parsed = _parse_jibun_address(address)
    if not parsed:
        return None
    sig_nm, emd_nm, jibun_num, ri_nm = parsed
    if not jibun_num:
        return None

    key = _api_key()
    dom = _domain()
    if not key:
        return None

    def _run_bbox(lon0: float, lat0: float) -> list:
        d = 0.008
        wfs_params = {
            "SERVICE": "WFS", "VERSION": "1.1.0", "REQUEST": "GetFeature",
            "TYPENAME": WFS_TYPENAME, "KEY": key,
            "SRSNAME": "EPSG:4326", "outputFormat": "application/json",
            "MAXFEATURES": "80",
            "BBOX": f"{lat0-d},{lon0-d},{lat0+d},{lon0+d},EPSG:4326",
        }
        if dom:
            wfs_params["domain"] = dom
        r = _vworld_get("https://api.vworld.kr/req/wfs", wfs_params, timeout=12)
        r.raise_for_status()
        return _json.loads(r.content.decode("utf-8")).get("features", [])

    def _run_cql(with_ri: bool) -> list:
        if not emd_nm:
            return []
        jn = jibun_num.replace("'", "''")
        emd_esc = emd_nm.replace("'", "''")
        jm_raw = (expected_jimok or "").strip()
        if jm_raw:
            jm = jm_raw.replace("'", "''")
            # 공부 형식: '산110-2 임' 우선, 없으면 기존 넓은 패턴
            jibun_cql = (
                f"(jibun = '{jn} {jm}' OR jibun LIKE '{jn} {jm} %' OR jibun LIKE '{jn} {jm}%')"
                f" OR (jibun LIKE '{jn} %' OR jibun = '{jn}')"
            )
        else:
            jibun_cql = f"(jibun LIKE '{jn} %' OR jibun = '{jn}')"
        parts = [f"emd_nm = '{emd_esc}'"]
        if with_ri and ri_nm:
            ri_esc = ri_nm.replace("'", "''")
            parts.append(f"ri_nm = '{ri_esc}'")
        parts.append(f"({jibun_cql})")
        cql = " AND ".join(parts)
        if sig_nm:
            sig_esc = sig_nm.replace("'", "''")
            cql = f"sig_nm = '{sig_esc}' AND {cql}"
        wfs_params = {
            "SERVICE": "WFS", "VERSION": "1.1.0", "REQUEST": "GetFeature",
            "TYPENAME": WFS_TYPENAME, "KEY": key,
            "SRSNAME": "EPSG:4326", "outputFormat": "application/json",
            "MAXFEATURES": "20",
            "CQL_FILTER": cql,
        }
        if dom:
            wfs_params["domain"] = dom
        r = _vworld_get("https://api.vworld.kr/req/wfs", wfs_params, timeout=12)
        r.raise_for_status()
        return _json.loads(r.content.decode("utf-8")).get("features", [])

    try:
        # 지목(임·전 등)을 주소에 붙인 변형부터 지오코딩 — PARCEL 검색이 산+지목 조합에 맞춰지는 경우가 많음
        feats: list = []
        variants = _parcel_geocode_variants(address, expected_jimok)
        cands: list = []
        for cand_addr in variants:
            coords = _geocode(cand_addr)
            if not coords:
                continue
            lon0, lat0 = coords
            feats_try = _run_bbox(lon0, lat0)
            c_try = _pick_wfs_candidates(feats_try, jibun_num, expected_jimok, ri_nm)
            if c_try:
                feats = feats_try
                cands = c_try
                break
            if not feats and feats_try:
                feats = feats_try
            elif feats_try and len(feats_try) > len(feats):
                feats = feats_try

        if not cands:
            cands = _pick_wfs_candidates(feats, jibun_num, expected_jimok, ri_nm)
        if not cands:
            for with_ri in ([True, False] if ri_nm else [False]):
                feats_cql = _run_cql(with_ri)
                cands = _pick_wfs_candidates(feats_cql, jibun_num, expected_jimok, ri_nm)
                if cands:
                    break

        if not cands:
            print(f"[지번 매칭] '{jibun_num}' 없음 — bbox+CQL 후보 부족 (fallback)")
            return None

        matched = cands[0]
        lon, lat = _polygon_centroid(matched.get("geometry", {}))
        if lon is None:
            return None

        return _fetch_parcel_info(
            lon, lat,
            nearby_radius=nearby_radius,
            expected_jibun_num=jibun_num,
            expected_jimok=expected_jimok,
            seed_wfs_feature=matched,
        )

    except Exception as e:
        print(f"[지번 매칭] 실패 ({address!r}): {type(e).__name__}: {e}")
        return None


def _wfs_feature_to_parcel_info_fields(feat: dict) -> dict:
    """WFS GeoJSON feature → _fetch_parcel_info용 기본 필드."""
    props = feat.get("properties", {}) or {}
    geom = feat.get("geometry", {}) or {}
    jibun_raw = props.get("jibun", "")
    jibun_parts = jibun_raw.rsplit(" ", 1)
    jibun_num = jibun_parts[0] if jibun_parts else jibun_raw
    land_cat = jibun_parts[1] if len(jibun_parts) == 2 else ""
    jiga_raw = props.get("jiga")
    price_per_m2 = None
    if jiga_raw:
        try:
            price_per_m2 = int(float(str(jiga_raw).replace(",", "")))
        except (ValueError, TypeError):
            pass
    addr_parts = [
        props.get("ctp_nm", ""), props.get("sig_nm", ""),
        props.get("emd_nm", ""), jibun_raw,
    ]
    address = " ".join(x for x in addr_parts if x)
    return {
        "pnu": props.get("pnu", ""),
        "jibun": jibun_num,
        "land_category_name": land_cat,
        "sido_nm": props.get("ctp_nm", ""),
        "sgg_nm": props.get("sig_nm", ""),
        "emd_nm": props.get("emd_nm", ""),
        "address": address,
        "official_price_per_m2": price_per_m2,
        "price_year": str(props.get("gosi_year", "") or ""),
        "geometry": geom,
    }


def _fetch_parcel_info(
    lon: float,
    lat: float,
    nearby_radius: int = 500,
    expected_jibun_num: Optional[str] = None,
    expected_jimok: Optional[str] = None,
    seed_wfs_feature: Optional[dict] = None,
) -> dict:
    """
    좌표 → 필지 전체 정보 딕셔너리.

    Step 1. WFS lp_pa_cbnd_bubun  → polygon + PNU + 지번 + 공시지가(jiga)
    Step 2. Data API LANDINFOBASEMAP → 면적 보완
    Step 3~N. 보강 API 병렬 실행 (토지특성/공시지가/소유정보/건물/주변건물 등)

    expected_jibun_num / expected_jimok: 검색·지오코딩 직후 좁은 BBOX에서 이웃 필지로
    잘못 잡히는 경우, 좌표가 들어 있는 폴리곤 중 지번이 일치하는 것을 우선한다.

    seed_wfs_feature: 지번 검색에서 이미 고른 WFS 피처가 있으면 BBOX 재조회 없이 사용한다.
    (좁은 BBOX가 이웃 필지로 바뀌는 오류 방지)
    """
    import requests, json as _json

    info: dict = {"lon": lon, "lat": lat}
    key = _api_key()
    dom = _domain()
    if not key:
        return {**info, "error": "VWORLD_API_KEY 미설정"}

    # ── 1. WFS → polygon + 기본 필지 속성 ────────────────────────────
    if seed_wfs_feature and (seed_wfs_feature.get("properties") or seed_wfs_feature.get("geometry")):
        g = seed_wfs_feature.get("geometry") or {}
        c_lon, c_lat = _polygon_centroid(g)
        if c_lon is not None and c_lat is not None:
            lon, lat = c_lon, c_lat
        info["lon"], info["lat"] = lon, lat
        info.update(_wfs_feature_to_parcel_info_fields(seed_wfs_feature))
    else:
        # d=0.0002 ≈ 22m 반경 BBOX, MAXFEATURES=30 → point-in-polygon으로 정확 선택
        d = 0.0002
        wfs_params = {
            "SERVICE": "WFS", "VERSION": "1.1.0", "REQUEST": "GetFeature",
            "TYPENAME": WFS_TYPENAME, "KEY": key,
            "SRSNAME": "EPSG:4326", "outputFormat": "application/json",
            "MAXFEATURES": "30",
            "BBOX": f"{lat-d},{lon-d},{lat+d},{lon+d},EPSG:4326",
        }
        if dom:
            wfs_params["domain"] = dom

        try:
            r = _vworld_get("https://api.vworld.kr/req/wfs", wfs_params, timeout=12)
            r.raise_for_status()
            raw_text = r.content.decode("utf-8")
            wfs_json = _json.loads(raw_text)
            feats = wfs_json.get("features", [])
            if not feats:
                print(f"[VWorld WFS] features 없음. 응답 앞 300자: {raw_text[:300]}")
            if feats:
                def _feat_jn(f):
                    jr = (f.get("properties") or {}).get("jibun", "")
                    return jr.split()[0] if jr else ""

                inside = [f for f in feats if _point_in_geom(lon, lat, f.get("geometry", {}))]
                exp_jn = (expected_jibun_num or "").strip()
                exp_jm = (expected_jimok or "").strip()

                matched = None
                if exp_jn:
                    pool = inside if inside else feats
                    if exp_jm:
                        matched = next(
                            (f for f in pool
                             if _feat_jn(f) == exp_jn
                             and _wfs_jibun_num_jimok(f.get("properties", {}))[1] == exp_jm),
                            None,
                        )
                    if matched is None:
                        matched = next((f for f in pool if _feat_jn(f) == exp_jn), None)
                    if matched is None and inside:
                        matched = next(
                            (f for f in feats if _feat_jn(f) == exp_jn),
                            None,
                        )
                if matched is None:
                    matched = next(
                        (f for f in inside),
                        feats[0],
                    )
                info.update(_wfs_feature_to_parcel_info_fields(matched))
        except _json.JSONDecodeError as e:
            # VWorld가 JSON이 아닌 XML/HTML 오류를 반환할 때 (key 오류, domain 불일치 등)
            try:
                raw_preview = r.content.decode("utf-8")[:500]
            except Exception:
                raw_preview = "(응답 읽기 실패)"
            print(f"[VWorld WFS] JSON 파싱 실패 — 응답: {raw_preview}")
        except Exception as e:
            print(f"[VWorld WFS] 조회 실패: {type(e).__name__}: {e}")

    # ── 2. Data API → 면적·지목 보완 (LT_C_LANDINFOBASEMAP) ──────────
    da_feats = _get_feature(LAYER_PARCEL, lon, lat)
    if da_feats:
        p = da_feats[0].get("properties", {})
        try:
            area = float(p.get("parea", 0) or 0)
        except (ValueError, TypeError):
            area = 0.0
        if area:
            info["area_m2"] = area
        if not info.get("land_category_name"):
            info["land_category_name"] = p.get("jimok", "")
        if not info.get("pnu"):
            info["pnu"] = p.get("pnu", "")

    # 공시가액 계산
    if info.get("official_price_per_m2") and info.get("area_m2"):
        info["official_total_price"] = int(info["official_price_per_m2"] * info["area_m2"])

    pnu = info.get("pnu", "")
    khug_key = os.getenv("KHUG_API_KEY", "")
    sigungu_code = pnu[:5] if pnu and len(pnu) >= 5 else ""

    # ── PNU 캐시 조회 (캐시 히트 시 NED API 12개 생략) ───────────────────
    # seed_wfs_feature 경로는 방금 확정한 필지와 캐시 불일치 방지를 위해 캐시 생략
    if pnu and seed_wfs_feature is None:
        try:
            from database.supabase_client import get_supabase_client as _gsc
            _sc = _gsc()
            _hit = _sc.table("parcel_cache").select("parcel_data").eq("pnu", pnu).limit(1).execute()
            if _hit.data:
                _cached = _hit.data[0].get("parcel_data") or {}
                # 클릭 좌표(lon/lat)는 현재 값 유지, 나머지는 캐시에서 덮어씀
                _cached["lon"] = lon
                _cached["lat"] = lat
                # nearby_radius가 다르면 nearby_buildings만 새로 조회
                if nearby_radius and _cached.get("nearby_radius") != nearby_radius:
                    try:
                        _fresh_nearby = _fetch_nearby_buildings(lon, lat, radius_m=nearby_radius)
                        _cached["nearby_buildings"] = _fresh_nearby or []
                        _cached["nearby_radius"] = nearby_radius
                    except Exception as _ne:
                        print(f"[PNU캐시] nearby_buildings 재조회 오류: {_ne}")
                return _cached
        except Exception as _ce:
            print(f"[PNU캐시] 조회 오류: {_ce}")

    # ── 2-b ~ 4. 모든 보강 API 병렬 실행 (timeout 7s) ─────────────────
    # 순차 실행 시 10개+ × 10s = 100s+, 병렬로 ~7s로 단축
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _task_land_char():
        return "land_char", _get_land_characteristics(pnu) if pnu else {}

    def _task_indvd_price():
        return "indvd_price", _get_indvd_land_price(pnu) if pnu else []

    def _task_price_change():
        return "price_change", _get_price_change_rate(sigungu_code) if sigungu_code else None

    def _task_bwfs():
        return "bwfs", _get_parcel_building_wfs(lon, lat, pnu) if pnu else {}

    def _task_ownership():
        return "ownership", _get_land_ownership(pnu) if pnu else {}

    def _task_gis_bld():
        return "gis_bld", _get_gis_building(lon, lat, pnu) if pnu else {}

    def _task_std_price():
        return "std_price", _get_std_land_price(pnu) if pnu else {}

    def _task_land_use_plan():
        return "land_use_plan", _get_land_use_plan(pnu) if pnu else {}

    def _task_jiguinfo():
        if _BLDG_HUB_AVAILABLE and pnu and khug_key:
            try:
                return "jiguinfo", get_jiguinfo(pnu)
            except Exception as e:
                logger.debug("건축HUB 지구정보 오류: %s", e)
        return "jiguinfo", {}

    def _task_building():
        if _BLDG_HUB_AVAILABLE and pnu and khug_key:
            return "building", get_building_info(pnu)
        return "building", {}

    def _task_nearby():
        if not nearby_radius:
            return "nearby", []
        return "nearby", _fetch_nearby_buildings(lon, lat, radius_m=nearby_radius)

    def _task_vworld_reg():
        """VWorld 4-layer 규제 조회 — _task_jiguinfo / _task_land_use_plan 실패 시 사용"""
        results = {}
        for _layer, _field, _suffix in [
            (LAYER_ZONING,   "zoning",   "지역"),
            (LAYER_DISTRICT, "district", "지구"),
            (LAYER_ZONE,     "zone",     "구역"),
            (LAYER_JIGUDAN,  "jigudan",  ""),
        ]:
            _feats = _get_feature(_layer, lon, lat)
            if _feats:
                _p = _feats[0].get("properties", {})
                _v = (_p.get("uname") or _p.get("jnamt") or "").strip()
                if _v and _suffix and not _v.endswith(("지역", "구역", "지구")):
                    _v += _suffix
                if _v:
                    results[_field] = _v
        return "vworld_reg", results

    tasks = [
        _task_land_char, _task_indvd_price, _task_price_change,
        _task_bwfs, _task_ownership, _task_gis_bld,
        _task_std_price, _task_land_use_plan,
        _task_jiguinfo, _task_building, _task_vworld_reg,
        _task_nearby,
    ]
    enriched = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(t): t.__name__ for t in tasks}
        try:
            for future in as_completed(futures, timeout=35):
                try:
                    key_r, val = future.result()
                    enriched[key_r] = val
                except Exception as e:
                    logger.debug("병렬 API 오류 (%s): %s", futures[future], e)
        except TimeoutError:
            logger.debug("병렬 API 일부 미완료 (timeout) — 수집된 결과로 진행")

    # ── 결과 병합 ─────────────────────────────────────────────────────

    # 토지특성
    lc = enriched.get("land_char") or {}
    if lc:
        info.update(lc)
        if not info.get("zoning") and lc.get("zoning_ned"):
            info["zoning"] = lc.pop("zoning_ned")
        else:
            lc.pop("zoning_ned", None)

    # 개별공시지가 이력
    price_history = enriched.get("indvd_price") or []
    if price_history:
        info["price_history"] = price_history

    # 지가변동률
    chg = enriched.get("price_change")
    if chg:
        info["price_change_rate"] = chg

    # 건물WFS (주차)
    bwfs = enriched.get("bwfs") or {}
    if bwfs:
        info["building_wfs"] = bwfs

    # 소유정보
    own = enriched.get("ownership") or {}
    if own:
        info["ownership"] = own

    # GIS건물
    gis_bld = enriched.get("gis_bld") or {}
    if gis_bld:
        info["gis_building"] = gis_bld

    # 표준지공시지가 (개별공시지가 없을 때 보완)
    std = enriched.get("std_price") or {}
    if std and not info.get("price_history"):
        info["std_land_price"] = std
        hist = []
        if std.get("price") and std.get("year"):
            hist.append({"year": std["year"], "price": std["price"]})
        hist += std.get("history", [])
        if hist:
            info["price_history"] = hist

    # 토지이용계획
    lup = enriched.get("land_use_plan") or {}
    if lup and lup.get("entries"):
        info["land_use_plan"] = lup

    # 건축물 정보
    binfo = enriched.get("building") or {}
    if binfo:
        info["building"] = binfo

    # 주변 건물
    nearby = enriched.get("nearby") or []
    if nearby:
        info["nearby_buildings"] = nearby
        info["nearby_radius"] = nearby_radius

    # 지역·지구·구역 (우선순위: 건축HUB > AL_D155 > VWorld 4-layer)
    jinfo = enriched.get("jiguinfo") or {}
    if jinfo and jinfo.get("all_entries"):
        if jinfo.get("zoning"):
            info["zoning"] = jinfo["zoning"]
        if jinfo.get("districts"):
            info["districts"] = jinfo["districts"]
        info["jiguinfo_entries"] = jinfo["all_entries"]
    elif lup and lup.get("entries"):
        lup_entries = lup["entries"]
        info["jiguinfo_entries"] = [
            {"type": "용도지역지구", "name": e["name"],
             **({"conflict": e["conflict"]} if e.get("conflict") else {})}
            for e in lup_entries
        ]
        if not info.get("zoning") and lup_entries:
            info["zoning"] = lup_entries[0]["name"]
    else:
        vworld_regs = enriched.get("vworld_reg") or {}
        if vworld_regs:
            type_labels = {"zoning": "지역", "district": "지구", "zone": "구역", "jigudan": "지구단위계획구역"}
            for field, val in vworld_regs.items():
                info[field] = val
            info["jiguinfo_entries"] = [
                {"type": type_labels.get(f, f), "name": v}
                for f, v in vworld_regs.items()
            ]

    # ── PNU 캐시 저장 ────────────────────────────────────────────────────
    if pnu:
        try:
            from database.supabase_client import get_supabase_client as _gsc
            _sc = _gsc()
            _sc.table("parcel_cache").upsert(
                {"pnu": pnu, "parcel_data": info},
                on_conflict="pnu"
            ).execute()
        except Exception as _ce:
            print(f"[PNU캐시] 저장 오류: {_ce}")

    return info


# ─── 지도 빌드 ────────────────────────────────────────────────────────────────

def _build_map(center: list, zoom: int, parcels: list, preview: Optional[dict]) -> "folium.Map":
    import folium

    key = _api_key()
    # tiles=None → 빈 지도로 시작, 아래 TileLayer 첫 번째가 기본 표시됨
    m = folium.Map(location=center, zoom_start=zoom, tiles=None, max_zoom=19)

    # VWorld 기본지도 (show=True → 기본 선택)
    folium.TileLayer(
        tiles=f"https://api.vworld.kr/req/wmts/1.0.0/{key}/Base/{{z}}/{{y}}/{{x}}.png",
        name="VWorld 기본지도",
        attr="© VWorld (국토지리정보원)",
        max_zoom=19,
        overlay=False,
        show=True,
    ).add_to(m)

    # ── 추가 베이스 타일 ──────────────────────────────────────────────────
    # VWorld 위성영상
    folium.TileLayer(
        tiles=f"https://api.vworld.kr/req/wmts/1.0.0/{key}/Satellite/{{z}}/{{y}}/{{x}}.jpeg",
        name="VWorld 위성영상",
        attr="© VWorld (국토지리정보원)",
        max_zoom=19,
        overlay=False,
    ).add_to(m)

    # VWorld 하이브리드 (위성 + 지명)
    folium.TileLayer(
        tiles=f"https://api.vworld.kr/req/wmts/1.0.0/{key}/Hybrid/{{z}}/{{y}}/{{x}}.png",
        name="VWorld 하이브리드",
        attr="© VWorld (국토지리정보원)",
        max_zoom=19,
        overlay=False,
    ).add_to(m)

    # VWorld 지적도 (필지 경계 오버레이) — 기본 ON, 항상 표시
    folium.TileLayer(
        tiles=f"https://api.vworld.kr/req/wmts/1.0.0/{key}/Cadastral/{{z}}/{{y}}/{{x}}.png",
        name="지적도 경계",
        attr="© VWorld (국토지리정보원)",
        max_zoom=19,
        overlay=True,
        opacity=1.0,
        show=True,
        z_index_offset=100,
    ).add_to(m)

    # ── 선택된 필지 polygon ────────────────────────────────────────────────
    for i, p in enumerate(parcels):
        geom = p.get("geometry")
        if not geom:
            continue
        color = PARCEL_COLORS[i % len(PARCEL_COLORS)]
        address = p.get("address", f"필지 {i+1}")
        area_s = f"{p['area_m2']:,.1f}㎡" if p.get("area_m2") else ""
        popup_html = (
            f"<b style='color:{color}'>● 선택 {i+1}</b><br>"
            f"<b>{address}</b><br>"
            f"지목: {p.get('land_category_name','-')}<br>"
            f"면적: {area_s}<br>"
            f"용도지역: {p.get('zoning','-')}"
        )
        folium.GeoJson(
            data={"type": "Feature", "geometry": geom},
            style_function=lambda _, c=color: {
                "fillColor": c,
                "color": c,
                "weight": 3,
                "fillOpacity": 0.35,
                "opacity": 1.0,
            },
            highlight_function=lambda _, c=color: {
                "fillColor": c,
                "fillOpacity": 0.6,
                "weight": 4,
                "opacity": 1.0,
            },
            tooltip=address,
            popup=folium.Popup(popup_html, max_width=240),
        ).add_to(m)

    # ── 미리보기 polygon (클릭 직후, 아직 추가 전) ─────────────────────────
    if preview and not preview.get("error"):
        geom = preview.get("geometry")
        lon_p, lat_p = preview.get("lon"), preview.get("lat")
        address = preview.get("address", "선택 중")

        if geom:
            folium.GeoJson(
                data={"type": "Feature", "geometry": geom},
                style_function=lambda _: {
                    "fillColor": PREVIEW_COLOR,
                    "color": PREVIEW_COLOR,
                    "weight": 4,
                    "fillOpacity": 0.45,
                    "opacity": 1.0,
                    "dashArray": "8 4",
                },
                tooltip=f"📍 {address}",
            ).add_to(m)
        elif lon_p and lat_p:
            # polygon 없을 때 마커로 대체
            folium.Marker(
                location=[lat_p, lon_p],
                icon=folium.Icon(color="orange", icon="home"),
                tooltip=address,
            ).add_to(m)

    # ── 선택 필지 중심 마커 (번호 표시) ───────────────────────────────────
    for i, p in enumerate(parcels):
        lon_p, lat_p = p.get("lon"), p.get("lat")
        if lon_p and lat_p:
            color = PARCEL_COLORS[i % len(PARCEL_COLORS)]
            folium.Marker(
                location=[lat_p, lon_p],
                icon=folium.DivIcon(
                    html=f'<div style="background:{color};color:#fff;border-radius:50%;'
                         f'width:24px;height:24px;display:flex;align-items:center;'
                         f'justify-content:center;font-weight:700;font-size:12px;'
                         f'border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.4);">{i+1}</div>',
                    icon_size=(24, 24),
                    icon_anchor=(12, 12),
                ),
                tooltip=p.get("address", f"필지 {i+1}"),
            ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


# ─── 정보 카드 ────────────────────────────────────────────────────────────────

def _section(title: str):
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:#444;'
        f'margin:10px 0 4px 0;padding-bottom:2px;border-bottom:1px solid #e0e0e0">'
        f'{title}</div>',
        unsafe_allow_html=True,
    )

def _row(label: str, value: str):
    if not value or value == "—":
        return
    st.markdown(
        f'<div style="display:flex;gap:8px;font-size:13px;margin:2px 0">'
        f'<span style="color:#888;min-width:110px;flex-shrink:0">{label}</span>'
        f'<span style="color:#111;font-weight:500">{value}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_parcel_card(info: dict, color: str = PREVIEW_COLOR, badge: str = "선택 중"):
    address = info.get("address", "—")
    pnu     = info.get("pnu", "")

    # ── 헤더 ──────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="border-left:4px solid {color};padding:6px 10px;margin-bottom:8px;'
        f'background:rgba(0,0,0,0.02);border-radius:0 4px 4px 0">'
        f'<span style="background:{color};color:#fff;border-radius:4px;'
        f'padding:1px 8px;font-size:11px;font-weight:600">{badge}</span> '
        f'<b style="font-size:14px">{address}</b>'
        + (f'<br><span style="font-size:11px;color:#888">PNU: {pnu}</span>' if pnu else "")
        + f'</div>',
        unsafe_allow_html=True,
    )

    # ── 📐 기본정보 ────────────────────────────────────────────────────
    _section("📐 기본정보")
    _row("지목", info.get("land_category_name", "—"))
    area = info.get("area_m2")
    _row("면적", f"{area:,.0f} ㎡" if area else "—")
    jibun = info.get("jibun", "")
    _row("지번", jibun or "—")

    price = info.get("official_price_per_m2")
    if price:
        year_s = f" ({info['price_year']}년 기준)" if info.get("price_year") else ""
        _row("공시지가", f"{price:,} 원/㎡{year_s}")
        total = info.get("official_total_price")
        if total:
            _row("토지 공시지가 총액", f"{total:,} 원")

    # 개별공시지가 이력 (AL_D150)
    price_history = info.get("price_history", [])
    if price_history:
        hist_str = "  /  ".join(
            f"{h['year']}년 {h['price']:,}원" for h in price_history[:4]
        )
        _row("개별공시지가 이력", hist_str)

    # 지가변동률 (AL_D203)
    chg = info.get("price_change_rate")
    if chg and chg.get("rate") is not None:
        rate_s = f"{chg['rate']:+.2f}%"
        period_s = ""
        if chg.get("year"):
            period_s = f" ({chg['year']}년"
            if chg.get("period"):
                period_s += f" {chg['period']}분기"
            period_s += ")"
        _row("지가변동률", rate_s + period_s)

    # 토지특성 (getLandCharacteristics)
    _row("토지이용상황", info.get("land_use_status", ""))
    _row("도로접면",    info.get("road_side", ""))
    _row("지형높이",    info.get("terrain_height", ""))
    _row("지형형상",    info.get("terrain_shape", ""))

    # ── 🏠 소유정보 (AL_D160) ──────────────────────────────────────────
    own = info.get("ownership", {})
    if own:
        _section("🏠 소유정보")
        _row("소유구분",       own.get("ownership_type", ""))
        shared = own.get("shared_count")
        if shared and shared > 1:
            _row("공유인수",   f"{shared}명")
        _row("소유권변동원인", own.get("change_cause", ""))
        _row("소유권변동일자", own.get("change_date", ""))
        _row("거주지구분",     own.get("residence_type", ""))
        _row("연령대",         own.get("age_group", ""))

    # ── 🏗 용도 및 규제 ────────────────────────────────────────────────
    entries   = info.get("jiguinfo_entries") or []
    zoning    = info.get("zoning", "")

    has_reg = entries or zoning or info.get("district") or info.get("zone") or info.get("jigudan")
    if has_reg:
        _section("🏗 용도 및 규제")

        if entries:
            # AL_D155 또는 건축HUB 데이터
            lup = info.get("land_use_plan", {})
            if lup and lup.get("entries"):
                # AL_D155: 저촉여부 포함 전체 목록
                for e in lup["entries"]:
                    conf_s = f" ({'저촉' if e.get('conflict') else '비저촉'})" if e.get("conflict") else ""
                    _row("용도지역지구", e["name"] + conf_s)
            else:
                # 건축HUB 데이터 — 지역/지구/구역 전체 분류
                zoning_list  = [e["name"] for e in entries if e.get("type") == "지역"]
                jigudan_list = [e["name"] for e in entries if "지구단위" in e.get("name", "")]
                all_names    = [e["name"] for e in entries]
                _row("용도지역",    ", ".join(zoning_list) if zoning_list else "—")
                if jigudan_list:
                    _row("지구단위계획", ", ".join(jigudan_list))
                if all_names:
                    _row("기타규제사항", ", ".join(all_names))
        else:
            # VWorld fallback
            _row("용도지역",       zoning or "—")
            _row("용도지구",       info.get("district", ""))
            _row("용도구역",       info.get("zone", ""))
            _row("지구단위계획구역", info.get("jigudan", ""))

    # ── 🏢 건축물 정보 ─────────────────────────────────────────────────
    bld  = info.get("building")
    bwfs = info.get("building_wfs", {})
    if bld or bwfs:
        _section("🏢 건축물 정보")
        # 건물명 (건축HUB 우선, WFS 보완)
        bld_nm = (bld or {}).get("bld_name") or bwfs.get("wfs_buld_nm", "")
        _row("건물명",    bld_nm)
        _row("주용도",    (bld or {}).get("main_purpose") or bwfs.get("wfs_main_prpos", ""))
        _row("주구조",    (bld or {}).get("structure") or bwfs.get("wfs_structure", ""))
        if bld and bld.get("arch_area"):
            _row("건축면적", f"{bld['arch_area']:,.1f} ㎡")
        if bld and bld.get("total_area"):
            _row("연면적",   f"{bld['total_area']:,.1f} ㎡")
        elif bwfs.get("wfs_total_area"):
            try:
                _row("연면적", f"{float(bwfs['wfs_total_area']):,.1f} ㎡")
            except (ValueError, TypeError):
                pass
        if bld and bld.get("bcr"):
            _row("건폐율",   f"{bld['bcr']:.1f} %")
        if bld and bld.get("vlr"):
            _row("용적률",   f"{bld['vlr']:.1f} %")
        if bld and bld.get("vlr_area"):
            _row("용적률산정연면적", f"{bld['vlr_area']:,.1f} ㎡")
        flr_parts = []
        if bld and bld.get("floors_above"):
            flr_parts.append(f"지상 {bld['floors_above']}층")
        elif bwfs.get("wfs_floors_above"):
            flr_parts.append(f"지상 {bwfs['wfs_floors_above']}층")
        if bld and bld.get("floors_below"):
            flr_parts.append(f"지하 {bld['floors_below']}층")
        elif bwfs.get("wfs_floors_below"):
            flr_parts.append(f"지하 {bwfs['wfs_floors_below']}층")
        if flr_parts:
            _row("층수", " / ".join(flr_parts))
        if bld and bld.get("building_height"):
            _row("건물 높이", f"{bld['building_height']:.1f} m")
        _row("사용승인일", (bld or {}).get("approve_date") or bwfs.get("wfs_approve_date", ""))
        # 승강기
        elev_parts = []
        if bld and bld.get("elev_ride"):
            elev_parts.append(f"승용 {bld['elev_ride']}대")
        if bld and bld.get("elev_emergency"):
            elev_parts.append(f"비상 {bld['elev_emergency']}대")
        if elev_parts:
            _row("승강기", " / ".join(elev_parts))
        # 세대/가구
        if bld and bld.get("household_cnt"):
            _row("세대수", f"{bld['household_cnt']:,} 세대")
        if bld and bld.get("family_cnt"):
            _row("가구수", f"{bld['family_cnt']:,} 가구")
        # 지붕구조
        _row("지붕구조", (bld or {}).get("roof_structure", ""))
        # 주차 (건축HUB 표제부 우선, WFS 보완)
        pk_total = (bld or {}).get("parking_total") or bwfs.get("total_park_co")
        pk_ar    = bwfs.get("total_park_ar")
        if pk_total:
            _row("총 주차대수", f"{pk_total:,} 대")
        if pk_ar:
            _row("주차장 면적", f"{float(pk_ar):,.1f} ㎡")
        for _pk_label, _pk_key in [
            ("옥내자주식", "parking_indoor_auto"), ("옥외자주식", "parking_outdoor_auto"),
            ("옥내기계식", "parking_indoor_mech"), ("옥외기계식", "parking_outdoor_mech"),
        ]:
            if (bld or {}).get(_pk_key):
                _row(_pk_label, f"{bld[_pk_key]:,} 대")
        # GIS건물통합정보
        gis = info.get("gis_building", {})
        if gis.get("building_height"):
            _row("건물 높이",   f"{gis['building_height']:.1f} m")
        if gis.get("illegal_building"):
            flag = gis["illegal_building"]
            color = "#e53935" if flag in ("Y", "위반", "1") else "#555"
            st.markdown(
                f'<div style="display:flex;gap:8px;font-size:13px;margin:2px 0">'
                f'<span style="color:#888;min-width:110px;flex-shrink:0">위반건축물</span>'
                f'<span style="color:{color};font-weight:600">{flag}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if gis.get("gis_site_area"):
            _row("대지면적(GIS)", f"{gis['gis_site_area']:,.1f} ㎡")
        if bld and bld.get("plat_area"):
            _row("대지면적(표제부)", f"{bld['plat_area']:,.1f} ㎡")

    # ── 📋 층별 개요 ───────────────────────────────────────────────────
    bld = info.get("building") or {}
    floors = bld.get("floor_list", [])
    if floors:
        _section(f"📋 층별 개요 ({len(floors)}개 층)")
        # 지상/지하 구분 소계
        from collections import defaultdict
        _flr_agg: dict = defaultdict(float)
        for fl in floors:
            _flr_agg[fl.get("floor_gb", "기타")] += fl.get("area_m2", 0)
        for gb, area_sum in _flr_agg.items():
            if area_sum:
                _row(f"{gb} 합계", f"{area_sum:,.1f} ㎡")
        # 층별 상세 (expander) — 지하↓ → 지상↑ 정렬
        def _flr_sort_key(fl):
            gb = fl.get("floor_gb", "지상")
            try:
                no = int(fl.get("floor_no", 0))
            except (ValueError, TypeError):
                no = 0
            return (0, -no) if "지하" in gb else (1, no)

        with st.expander("층별 상세 보기", expanded=False):
            _rows_html = []
            for fl in sorted(floors, key=_flr_sort_key):
                gb   = fl.get("floor_gb", "")
                no   = fl.get("floor_no", "")
                purp = fl.get("purpose", "")
                ar   = fl.get("area_m2", 0)
                _rows_html.append(
                    f'<tr><td style="color:#888;padding:2px 8px">{gb}{no}층</td>'
                    f'<td style="padding:2px 8px">{purp}</td>'
                    f'<td style="padding:2px 8px;text-align:right">{ar:,.1f}㎡</td></tr>'
                )
            st.markdown(
                '<table style="font-size:12px;width:100%;border-collapse:collapse">'
                + "".join(_rows_html) + "</table>",
                unsafe_allow_html=True,
            )

    # ── 🏠 전유/공용면적 ─────────────────────────────────────────────
    excl_areas = bld.get("exclusive_areas", [])
    if excl_areas:
        from collections import defaultdict as _dd
        _ea_agg: dict = _dd(float)
        for ea in excl_areas:
            key = ea.get("division", "")
            _ea_agg[key] += ea.get("area_m2", 0)
        _section("🏠 전유/공용 면적")
        for div, area_sum in _ea_agg.items():
            if area_sum:
                _row(div, f"{area_sum:,.1f} ㎡")

    # ── 💰 주택가격 ───────────────────────────────────────────────────
    hsprc = bld.get("housing_prices", [])
    if hsprc:
        _section("💰 주택가격")
        for hp in hsprc[:5]:
            yr  = hp.get("year", "")
            mt  = hp.get("month", "")
            pr  = hp.get("price", 0)
            dnm = hp.get("dong_nm", "")
            hnm = hp.get("ho_nm", "")
            label = f"{yr}년 {mt}월" if mt else f"{yr}년"
            if dnm or hnm:
                label += f" ({dnm}{hnm})"
            if pr:
                _row(label, f"{pr:,} 원")

    # ── 🏘 주변 건물 현황 ──────────────────────────────────────────────
    nearby = info.get("nearby_buildings", [])
    if nearby:
        from collections import Counter
        radius = info.get("nearby_radius", 500)
        _section(f"🏘 주변 건물 현황 (반경 {radius}m, {len(nearby)}동)")
        uses = Counter(b.get("main_prpos_code_nm", "") for b in nearby if b.get("main_prpos_code_nm"))
        for use_nm, cnt in uses.most_common(8):
            pct = cnt / len(nearby) * 100
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;font-size:12px;margin:3px 0">'
                f'<span style="color:#888;min-width:110px;flex-shrink:0">{use_nm}</span>'
                f'<div style="flex:1;background:#f0f0f0;border-radius:3px;height:10px;overflow:hidden">'
                f'<div style="width:{pct:.0f}%;background:#1a73e8;height:100%"></div></div>'
                f'<span style="color:#333;font-weight:600;min-width:40px;text-align:right">{cnt}동</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _render_summary(parcels: list):
    total_area = sum(p.get("area_m2") or 0 for p in parcels)
    pyeong = total_area / 3.3058 if total_area else 0
    st.markdown("---")
    st.markdown("**📊 합계**")
    c1, c2, c3 = st.columns(3)
    c1.metric("필지 수", f"{len(parcels)}")
    c2.metric("합산 면적", f"{total_area:,.0f} ㎡" if total_area else "—")
    c3.metric("평수", f"{pyeong:,.0f} 평" if pyeong else "—")

    zonings = list(dict.fromkeys(p.get("zoning","") for p in parcels if p.get("zoning")))
    if zonings:
        st.caption(f"용도지역: {', '.join(zonings)}")

    # 공시가액 합계
    total_price = sum(p.get("official_total_price") or 0 for p in parcels)
    if total_price:
        st.caption(f"공시가액 합계: **{total_price:,} 원**")


# ─── 필지 세트 저장/불러오기 ───────────────────────────────────────────────────

_MAP_SET_KEY = "saved_map_sets"
_MAX_MAP_SETS = 20  # 사용자당 최대 저장 개수


def _parcel_snapshot(p: dict) -> dict:
    """저장할 필지 필드 선택 — 대용량 필드(nearby_buildings 등) 제외"""
    KEEP = {
        "pnu", "address", "lat", "lon", "area_m2",
        "land_category_name", "jibun", "sido_nm", "sgg_nm", "emd_nm",
        "zoning", "district", "zone", "jigudan", "jiguinfo_entries",
        "official_price_per_m2", "official_total_price", "price_year",
        "geometry",
    }
    return {k: v for k, v in p.items() if k in KEEP and v is not None}


def _get_user_settings_raw(uid: int) -> dict:
    """user_settings.settings_data 전체를 dict로 반환"""
    try:
        from database.supabase_client import get_supabase_client
        import json as _json
        client = get_supabase_client()
        r = client.table("user_settings").select("settings_data").eq("user_id", uid).limit(1).execute()
        rows = r.data or []
        if not rows:
            return {}
        raw = rows[0].get("settings_data") or {}
        return _json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        print(f"[MapSet] settings 읽기 오류: {e}")
        return {}


def _put_user_settings_raw(uid: int, settings: dict):
    """user_settings.settings_data UPSERT (기존 키 보존, saved_map_sets만 덮어씀)"""
    try:
        from database.supabase_client import get_supabase_client
        from datetime import datetime as _dt
        client = get_supabase_client()
        client.table("user_settings").upsert(
            {"user_id": uid, "settings_data": settings,
             "updated_at": _dt.now().isoformat()},
            on_conflict="user_id",
        ).execute()
    except Exception as e:
        print(f"[MapSet] settings 저장 오류: {e}")


def _load_saved_map_sets(uid: int) -> list:
    return _get_user_settings_raw(uid).get(_MAP_SET_KEY, [])


def _save_map_set(uid: int, parcels: list) -> dict:
    """현재 선택 필지를 user_settings에 자동 저장, 생성된 세트 반환"""
    import uuid
    from datetime import datetime as _dt

    # 이름 자동 생성: "삼척시 근덕면 8필지 · 04-14"
    rep_addr = next((p.get("address", "") for p in parcels if p.get("address")), "")
    addr_parts = rep_addr.split()
    short = " ".join(
        pt for pt in addr_parts
        if any(pt.endswith(x) for x in ("시", "군", "구", "읍", "면", "동", "리"))
    )
    short = (short[:18] if short else "필지 세트")
    auto_name = f"{short} {len(parcels)}필지 · {_dt.now().strftime('%m-%d')}"

    new_set = {
        "id":         str(uuid.uuid4())[:8],
        "name":       auto_name,
        "created_at": _dt.now().isoformat(),
        "parcels":    [_parcel_snapshot(p) for p in parcels],
    }

    settings = _get_user_settings_raw(uid)
    sets = settings.get(_MAP_SET_KEY, [])
    sets.insert(0, new_set)
    settings[_MAP_SET_KEY] = sets[:_MAX_MAP_SETS]
    _put_user_settings_raw(uid, settings)
    return new_set


def _delete_map_set(uid: int, set_id: str):
    settings = _get_user_settings_raw(uid)
    settings[_MAP_SET_KEY] = [
        s for s in settings.get(_MAP_SET_KEY, []) if s.get("id") != set_id
    ]
    _put_user_settings_raw(uid, settings)


# ─── 분석 연동 ────────────────────────────────────────────────────────────────

def _apply_to_analysis(parcels: list, nearby_radius: int = 500):
    if not parcels:
        return

    total_area = sum(p.get("area_m2") or 0 for p in parcels)
    pyeong     = total_area / 3.3058 if total_area else 0
    zonings    = list(dict.fromkeys(p.get("zoning","") for p in parcels if p.get("zoning")))
    addresses  = [p.get("address","") for p in parcels if p.get("address")]

    site_location = _format_parcel_addresses(addresses)

    site_area = (
        f"{total_area:,.1f}㎡ (약 {pyeong:,.0f}평, {len(parcels)}필지 합산) [VWorld API 확인]"
        if total_area else ""
    )
    zoning_str = ", ".join(zonings) + " [VWorld API 확인]" if zonings else ""

    if "user_inputs" not in st.session_state:
        st.session_state.user_inputs = {}
    st.session_state.user_inputs.update({
        "site_location": site_location,
        "site_area": site_area,
        "zoning": zoning_str,
    })

    # 메인 페이지 위젯 직접 연동
    # pending_project_info_updates 메커니즘으로 위젯 렌더링 전 안전하게 값 주입
    st.session_state["pending_project_info_updates"] = {
        "site_location": site_location,
        "site_area":     site_area,
    }
    # 직접 설정도 병행 (이미 main page에 있을 때 즉시 반영)
    st.session_state["site_location"] = site_location
    st.session_state["site_area"]     = site_area
    st.session_state["zoning"]        = zoning_str
    # 문서 분석 location 필드 자동 주입 (bridge key 사용 → form 렌더 직전에 복사)
    # "location"은 Document Analysis의 form 위젯 key이므로 Mapping에서 직접 설정하면
    # 페이지 전환 시 Streamlit이 위젯 키를 정리할 때 값이 사라질 수 있음.
    # _map_location은 위젯 key가 아니므로 안전하게 유지됨.
    if site_location:
        st.session_state["_map_location"] = site_location
    # 대표 필지 좌표 자동 설정 (Google Maps 블록용)
    rep = next((p for p in parcels if p.get("lat") and p.get("lon")), None)
    if rep:
        st.session_state["latitude"]  = str(rep["lat"])
        st.session_state["longitude"] = str(rep["lon"])
    # 지도 필지 선택 플래그 (메인 페이지 배너용)
    st.session_state["_map_parcel_loaded"] = True

    # 공시지가 가중평균
    weighted = [
        (p.get("official_price_per_m2") or 0) * (p.get("area_m2") or 0)
        for p in parcels
    ]
    avg_price = sum(weighted) / total_area if total_area and any(weighted) else 0

    # 용도계획 제한 목록 (건축HUB jiguinfo_entries 우선, 없으면 VWorld)
    all_restrictions = []
    for p in parcels:
        entries = p.get("jiguinfo_entries")
        if entries:
            for e in entries:
                nm = e.get("name","")
                if nm and nm not in all_restrictions:
                    all_restrictions.append(nm)
        else:
            for k in ("zoning","district","zone","jigudan"):
                v = p.get(k)
                if v and v not in all_restrictions:
                    all_restrictions.append(v)

    # 개별공시지가 이력 (대표 필지)
    rep_hist = next((p.get("price_history",[]) for p in parcels if p.get("price_history")), [])
    hist_str = ""
    if rep_hist:
        hist_str = " / ".join(f"{h['year']}년 {h['price']:,}원/㎡" for h in rep_hist[:3])

    # 지가변동률 (대표 필지)
    chg = next((p.get("price_change_rate") for p in parcels if p.get("price_change_rate")), None)
    chg_str = ""
    if chg and chg.get("rate") is not None:
        chg_str = f"{chg['rate']:+.2f}%"
        if chg.get("year"):
            chg_str += f" ({chg['year']}년"
            if chg.get("period"):
                chg_str += f" {chg['period']}분기"
            chg_str += ")"

    if "site_fields" not in st.session_state:
        st.session_state.site_fields = {}
    st.session_state.site_fields.update({
        "site_address":          site_location,
        "site_area":             site_area,
        "zoning":                zoning_str,
        "land_category":         ", ".join(dict.fromkeys(
            p.get("land_category_name","") for p in parcels if p.get("land_category_name")
        )) + " [VWorld API 확인]",
        "parcel_count":          str(len(parcels)),
        "official_price_per_m2": f"{avg_price:,.0f} 원/㎡ (가중평균)" if avg_price else "",
        "land_restrictions":     ", ".join(all_restrictions),
        "land_api_enriched":     True,
        "land_api_summary":      _build_md(parcels),
        **({"indvd_land_price_history": hist_str} if hist_str else {}),
        **({"land_price_change_rate": chg_str} if chg_str else {}),
    })

    # 소유정보 (AL_D160, 대표 필지)
    own = next((p.get("ownership") for p in parcels if p.get("ownership")), None)
    if own:
        own_summary = own.get("ownership_type", "")
        if own.get("shared_count") and own["shared_count"] > 1:
            own_summary += f" (공유 {own['shared_count']}명)"
        if own_summary:
            st.session_state.site_fields["land_ownership"] = own_summary

    # GIS건물 높이/위반건축물 (AL_D010, 대표 필지)
    gis_bld = next((p.get("gis_building") for p in parcels if p.get("gis_building")), None)
    if gis_bld:
        if gis_bld.get("building_height"):
            st.session_state.site_fields["building_height"] = f"{gis_bld['building_height']:.1f}m"
        if gis_bld.get("illegal_building"):
            st.session_state.site_fields["illegal_building"] = gis_bld["illegal_building"]

    # 건축물 정보 (건축HUB — 대표 건물 기준)
    bld_list = [p.get("building") for p in parcels if p.get("building")]
    if bld_list:
        bld = bld_list[0]
        bld_fields = {}
        if bld.get("main_purpose"):  bld_fields["existing_building_purpose"] = bld["main_purpose"]
        if bld.get("total_area"):    bld_fields["existing_building_area"] = f"{bld['total_area']:,.1f}㎡"
        if bld.get("bcr"):           bld_fields["existing_bcr"] = f"{bld['bcr']:.1f}%"
        if bld.get("vlr"):           bld_fields["existing_vlr"] = f"{bld['vlr']:.1f}%"
        flr = ""
        if bld.get("floors_above"): flr = f"지상 {bld['floors_above']}층"
        if bld.get("floors_below"): flr += f" / 지하 {bld['floors_below']}층"
        if flr: bld_fields["existing_floors"] = flr
        if bld.get("approve_date"): bld_fields["existing_approve_date"] = bld["approve_date"]
        if bld_fields:
            st.session_state.site_fields.update(bld_fields)
    st.session_state["selected_parcels_raw"] = parcels

    # ── 주변 건물 정보 (getBuildingUseWFS, 반경은 nearby_radius 인수 기준) ──────────────────────
    # 대표 필지 좌표 기준으로 조회
    rep = next((p for p in parcels if p.get("lon") and p.get("lat")), None)
    if rep:
        with st.spinner(f"주변 건물 정보 조회 중 (반경 {nearby_radius}m)..."):
            nearby = _fetch_nearby_buildings(rep["lon"], rep["lat"], radius_m=nearby_radius)
        if nearby:
            st.session_state["nearby_buildings"] = nearby
            st.session_state.site_fields["nearby_buildings_count"] = str(len(nearby))
            # 주요 용도 통계
            from collections import Counter
            uses = Counter(b.get("main_prpos_code_nm","") for b in nearby if b.get("main_prpos_code_nm"))
            if uses:
                top = ", ".join(f"{nm}({cnt}동)" for nm, cnt in uses.most_common(5))
                st.session_state.site_fields["nearby_building_uses"] = top
            st.session_state.site_fields["nearby_buildings_summary"] = _build_nearby_md(nearby, radius_m=nearby_radius)

    # 필지 polygon → GeoJSON → downloaded_geo_data (3_Document_Analysis의 공간 데이터 연동용)
    parcel_features = []
    for p in parcels:
        geom = p.get("geometry")
        if geom:
            parcel_features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "address":               p.get("address", ""),
                    "pnu":                   p.get("pnu", ""),
                    "area_m2":               p.get("area_m2"),
                    "zoning":                p.get("zoning", ""),
                    "land_category":         p.get("land_category_name", ""),
                    "official_price_per_m2": p.get("official_price_per_m2"),
                    "land_restrictions":     ", ".join(
                        e.get("name", "") for e in (p.get("jiguinfo_entries") or []) if e.get("name")
                    ),
                },
            })
    if parcel_features:
        existing = st.session_state.get("downloaded_geo_data") or {}
        existing["선택 필지 (연속지적도)"] = {
            "geojson": {"type": "FeatureCollection", "features": parcel_features},
            "feature_count": len(parcel_features),
        }
        st.session_state["downloaded_geo_data"] = existing

    st.success(f"✅ {len(parcels)}개 필지 정보를 분석에 적용했습니다. '문서 분석' 페이지에서 분석을 시작하세요.")

    # projects.location 자동 업데이트
    try:
        from auth.authentication import is_authenticated, get_current_user
        from auth.project_manager import get_or_create_current_project, update_project
        if is_authenticated():
            _u = get_current_user()
            if _u:
                _uid = _u.get("id")
                _pid = get_or_create_current_project(_uid)
                if _pid and site_location:
                    update_project(_uid, _pid, location=site_location)
    except Exception as _upd_err:
        print(f"[Mapping] projects.location 업데이트 오류: {_upd_err}")

    # 지도 데이터 즉시 자동 저장
    try:
        from auth.session_init import auto_save_debounced
        auto_save_debounced(throttle_seconds=0)  # 즉시 저장
    except Exception as _as_err:
        print(f"[Mapping] 자동 저장 오류: {_as_err}")

    # 필지 세트 사이드바 자동 저장
    try:
        from auth.authentication import is_authenticated, get_current_user
        if is_authenticated():
            _mu = get_current_user()
            if _mu:
                _save_map_set(_mu.get("id"), parcels)
                # 사이드바 갱신을 위해 캐시 무효화
                st.session_state.pop("_map_sets_cache", None)
    except Exception as _ms_err:
        print(f"[MapSet] 자동 저장 오류: {_ms_err}")


def _build_nearby_md(buildings: list, radius_m: int = 500) -> str:
    """주변 건물 목록 → 분석용 마크다운"""
    if not buildings:
        return ""
    from collections import Counter
    lines = [f"### 주변 건물 현황 (반경 {radius_m}m, {len(buildings)}동)", ""]
    uses = Counter(b.get("main_prpos_code_nm","기타") for b in buildings)
    lines += ["**용도별 분포**"]
    for nm, cnt in uses.most_common():
        lines.append(f"- {nm}: {cnt}동")
    lines += ["", "**건물 목록 (상위 20동)**",
              "| 건물명 | 주용도 | 연면적(㎡) | 건폐율(%) | 용적률(%) | 지상층수 | 사용승인 |",
              "|--------|--------|-----------|----------|----------|---------|---------|"]
    for b in buildings[:20]:
        nm   = b.get("buld_nm","—") or "—"
        use  = b.get("main_prpos_code_nm","—") or "—"
        tar  = f"{float(b['buld_totar']):,.0f}" if b.get("buld_totar") else "—"
        btl  = b.get("btl_rt","—") or "—"
        fsr  = b.get("measrmt_rt","—") or "—"
        flr  = b.get("ground_floor_co","—") or "—"
        aday = b.get("use_confm_de","—") or "—"
        lines.append(f"| {nm} | {use} | {tar} | {btl} | {fsr} | {flr} | {aday} |")
    lines += ["", "> **출처**: VWorld 용도별건물WFS (getBuildingUseWFS) — 국토교통부 공공데이터"]
    return "\n".join(lines)


def _build_md(parcels: list) -> str:
    lines = ["## 📋 필지 구성 (지도 직접 선택, VWorld + 건축HUB 공공데이터 기반)", ""]
    total = sum(p.get("area_m2") or 0 for p in parcels)
    pyeong = total / 3.3058 if total else 0
    zonings = list(dict.fromkeys(p.get("zoning","") for p in parcels if p.get("zoning")))
    # 지가변동률 (대표 필지)
    chg = next((p.get("price_change_rate") for p in parcels if p.get("price_change_rate")), None)
    chg_str = ""
    if chg and chg.get("rate") is not None:
        chg_str = f"{chg['rate']:+.2f}%"
        if chg.get("year"):
            chg_str += f" ({chg['year']}년"
            if chg.get("period"):
                chg_str += f" {chg['period']}분기"
            chg_str += ")"

    lines += [
        "### 대지 통합 현황",
        "| 항목 | 내용 |", "|------|------|",
        f"| 총 필지 수 | {len(parcels)}필지 |",
        f"| 합산 면적 | {total:,.1f}㎡ (약 {pyeong:,.0f}평) |",
        f"| 용도지역 | {', '.join(zonings) or '—'} |",
    ]
    if chg_str:
        lines.append(f"| 지가변동률 | {chg_str} |")
    lines += ["",
        "### 필지별 상세",
        "| 주소 | 지목 | 면적(㎡) | 용도지역 | 공시지가(원/㎡) |",
        "|------|------|----------|----------|----------------|",
    ]
    for p in parcels:
        a = f"{p['area_m2']:,.1f}" if p.get("area_m2") else "—"
        pr = f"{p['official_price_per_m2']:,}" if p.get("official_price_per_m2") else "—"
        lines.append(
            f"| {p.get('address','—')} | {p.get('land_category_name','—')} | "
            f"{a} | {p.get('zoning','—')} | {pr} |"
        )

    # 지역·지구·구역 (건축HUB 데이터)
    for p in parcels:
        entries = p.get("jiguinfo_entries")
        if entries:
            addr = p.get("address", "필지")
            zoning_list  = [e["name"] for e in entries if e.get("type") == "지역"]
            jigudan_list = [e["name"] for e in entries if "지구단위" in e.get("name","")]
            all_names    = [e["name"] for e in entries]
            lines += ["", f"#### 용도 및 규제 — {addr}",
                      "| 항목 | 내용 |", "|------|------|"]
            lines.append(f"| 용도지역 | {', '.join(zoning_list) or '—'} |")
            if jigudan_list:
                lines.append(f"| 지구단위계획 | {', '.join(jigudan_list)} |")
            lines.append(f"| 기타규제사항 | {', '.join(all_names)} |")

    # 개별공시지가 이력 (AL_D150) — 대표 필지
    for p in parcels:
        hist = p.get("price_history", [])
        if hist:
            addr = p.get("address", "필지")
            lines += ["", f"#### 개별공시지가 이력 — {addr}",
                      "| 기준연도 | 공시지가 (원/㎡) |", "|---------|----------------|"]
            for h in hist[:5]:
                lines.append(f"| {h['year']}년 | {h['price']:,} |")

    # 건축물 정보 (건축HUB + WFS 주차정보)
    bld_sections = [
        (p.get("address","필지"), p.get("building"), p.get("building_wfs",{}))
        for p in parcels if p.get("building") or p.get("building_wfs")
    ]
    if bld_sections:
        lines += ["", "### 건축물 현황"]
        for addr, bld, bwfs in bld_sections:
            bld = bld or {}
            nm = bld.get("bld_name") or bwfs.get("wfs_buld_nm", "")
            lines.append(f"**{addr}** {f'({nm})' if nm else ''}")
            mp = bld.get("main_purpose") or bwfs.get("wfs_main_prpos","")
            if mp:           lines.append(f"- 주용도: {mp}")
            if bld.get("arch_area"):     lines.append(f"- 건축면적: {bld['arch_area']:,.1f}㎡")
            if bld.get("total_area"):    lines.append(f"- 연면적: {bld['total_area']:,.1f}㎡")
            if bld.get("bcr"):           lines.append(f"- 건폐율: {bld['bcr']:.1f}%")
            if bld.get("vlr"):           lines.append(f"- 용적률: {bld['vlr']:.1f}%")
            flr = ""
            if bld.get("floors_above"): flr += f"지상 {bld['floors_above']}층"
            if bld.get("floors_below"): flr += f" / 지하 {bld['floors_below']}층"
            if flr: lines.append(f"- 층수: {flr}")
            if bld.get("approve_date"): lines.append(f"- 사용승인일: {bld['approve_date']}")
            # 주차 정보
            if bwfs.get("total_park_co"):
                lines.append(f"- 총 주차대수: {bwfs['total_park_co']:,}대")
            if bwfs.get("total_park_ar"):
                lines.append(f"- 주차장 면적: {bwfs['total_park_ar']:,.1f}㎡")

    # 소유정보 (AL_D160)
    own_sections = [(p.get("address","필지"), p.get("ownership")) for p in parcels if p.get("ownership")]
    if own_sections:
        lines += ["", "### 소유 현황"]
        for addr, own in own_sections:
            lines.append(f"**{addr}**")
            if own.get("ownership_type"): lines.append(f"- 소유구분: {own['ownership_type']}")
            if own.get("shared_count"):   lines.append(f"- 공유인수: {own['shared_count']}명")
            if own.get("change_cause"):   lines.append(f"- 변동원인: {own['change_cause']}")
            if own.get("change_date"):    lines.append(f"- 변동일자: {own['change_date']}")

    lines += ["", "> **데이터 출처**: VWorld LP_PA_CBND_BUBUN(WFS), LT_C_LANDINFOBASEMAP — 국토교통부 공공데이터  \n"
              "> 지역·지구·구역: 건축물대장 허브(getBrJijiguInfo) → AL_D155 토지이용계획 → VWorld 규제레이어 (순차 fallback)  \n"
              "> 건축물 정보: 건축물대장 허브(getBrRecapTitleInfo) + AL_D010 GIS건물통합 + AL_D162/164 건물WFS  \n"
              "> 공시지가: AL_D150 개별공시지가 / AL_D152 표준지공시지가  \n"
              "> 지가변동률: AL_D203 지역별지가변동률  \n"
              "> 소유정보: AL_D160 토지소유정보"]
    return "\n".join(lines)


# ─── 메인 렌더 ────────────────────────────────────────────────────────────────

def render_land_map_page():
    st.title("🗺 필지 선택")

    key = _api_key()
    if not key:
        st.error("VWORLD_API_KEY가 설정되지 않았습니다. (.env 로드/환경변수 설정을 확인하세요)")
        return

    try:
        import folium
        from streamlit_folium import st_folium
    except ImportError:
        st.warning("지도 기능을 사용하려면 `pip install folium streamlit-folium`을 실행하세요.")
        return

    # ── 세션 초기화 ──────────────────────────────────────────────────────
    if "lm_center"     not in st.session_state: st.session_state.lm_center     = DEFAULT_CENTER
    if "lm_zoom"       not in st.session_state: st.session_state.lm_zoom       = DEFAULT_ZOOM
    if "lm_parcels" not in st.session_state:
        st.session_state.lm_parcels = list(st.session_state.get("selected_parcels_raw") or [])
    if "lm_preview"       not in st.session_state: st.session_state.lm_preview       = None
    if "lm_last_click"    not in st.session_state: st.session_state.lm_last_click    = ""
    if "lm_nearby_radius" not in st.session_state: st.session_state.lm_nearby_radius = 500

    # ── 사이드바: 저장된 필지 세트 ────────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("**저장된 필지 세트**")

        _sb_uid = None
        _sb_sets = []
        try:
            from auth.authentication import is_authenticated, get_current_user
            if is_authenticated():
                _sb_u = get_current_user()
                if _sb_u:
                    _sb_uid = _sb_u.get("id")
                    # 캐시 활용 (동일 rerun 내 중복 DB 조회 방지)
                    if "_map_sets_cache" not in st.session_state:
                        st.session_state["_map_sets_cache"] = _load_saved_map_sets(_sb_uid)
                    _sb_sets = st.session_state["_map_sets_cache"]
        except Exception:
            pass

        if not _sb_uid:
            st.caption("로그인 후 이용 가능합니다.")
        elif not _sb_sets:
            st.caption("저장된 세트가 없습니다.\n\n분석에 활용하면 자동 저장됩니다.")
        else:
            for _s in _sb_sets:
                _sid      = _s.get("id", "")
                _sname    = _s.get("name", "이름 없음")
                _sparcels = _s.get("parcels", [])
                _sdate    = (_s.get("created_at") or "")[:10]

                with st.expander(_sname, expanded=False):
                    # 지번 목록
                    for _sp in _sparcels:
                        _addr = _sp.get("address", "—")
                        _area = _sp.get("area_m2")
                        _area_s = f"  {_area:,.0f}㎡" if _area else ""
                        st.caption(f"• {_addr}{_area_s}")

                    if _sdate:
                        st.caption(f"저장일: {_sdate}")
                    st.write("")

                    _bc1, _bc2 = st.columns(2)
                    with _bc1:
                        if st.button("불러오기", key=f"lm_load_{_sid}",
                                     use_container_width=True, type="primary"):
                            st.session_state.lm_parcels = list(_sparcels)
                            st.session_state.lm_preview = None
                            if _sparcels:
                                _rep = _sparcels[0]
                                if _rep.get("lat") and _rep.get("lon"):
                                    st.session_state.lm_center = [_rep["lat"], _rep["lon"]]
                                    st.session_state.lm_zoom   = 15
                            st.rerun()
                    with _bc2:
                        if st.button("삭제", key=f"lm_del_{_sid}",
                                     use_container_width=True):
                            if _sb_uid:
                                _delete_map_set(_sb_uid, _sid)
                                st.session_state.pop("_map_sets_cache", None)
                            st.rerun()

    # ── 메인 페이지에서 주소 입력 → 자동 필지 로드 ───────────────────────────
    pending_addrs = st.session_state.get("_pending_map_addresses")
    if pending_addrs:
        del st.session_state["_pending_map_addresses"]
        _failed = []
        with st.spinner(f"{len(pending_addrs)}개 주소 필지 로드 중..."):
            existing_pnus = {p.get("pnu") for p in st.session_state.lm_parcels}
            _loaded_count = 0
            for raw_entry in pending_addrs:
                addr, jimok_hint = _normalize_pending_addr(raw_entry)
                # 1차: geocode+BBOX 지번 매칭, 실패 시 CQL + 지목 힌트
                info = _fetch_parcel_by_jibun(
                    addr,
                    nearby_radius=st.session_state.lm_nearby_radius,
                    expected_jimok=jimok_hint,
                )
                if not info:
                    # 2차: geocode만으로 좁은 BBOX (기대 지번으로 폴리곤 재선택)
                    coords = _geocode_parcel_first_hit(addr, jimok_hint)
                    if not coords:
                        _failed.append(addr)
                        continue
                    lon_a, lat_a = coords
                    parsed_fb = _parse_jibun_address(addr)
                    exp_jn = parsed_fb[2] if parsed_fb else None
                    info = _fetch_parcel_info(
                        lon_a, lat_a,
                        nearby_radius=st.session_state.lm_nearby_radius,
                        expected_jibun_num=exp_jn,
                        expected_jimok=jimok_hint,
                    )
                if info and not info.get("error") and info.get("pnu") not in existing_pnus:
                    st.session_state.lm_parcels.append(info)
                    existing_pnus.add(info.get("pnu"))
                    _loaded_count += 1
                    if _loaded_count == 1:
                        st.session_state.lm_center = [info["lat"], info["lon"]]
                        st.session_state.lm_zoom = 17
        if _failed:
            st.warning(f"주소를 찾을 수 없음: {', '.join(_failed)}")
        if st.session_state.lm_parcels:
            st.rerun()

    parcels = st.session_state.lm_parcels
    preview = st.session_state.lm_preview

    # ════════════════════════════════════════════════════════════════════
    # 상단: 검색 + 합계 + 필지 목록 (전체 폭)
    # ════════════════════════════════════════════════════════════════════

    # ── 검색 바 ──────────────────────────────────────────────────────────
    sc1, sc2, sc3 = st.columns([5, 1, 1])
    with sc1:
        addr_q = st.text_input(
            "주소", placeholder="주소 검색 — 단일: 강원도 삼척시 도계읍 산12-1  또는  다중: 강원도 삼척시 도계읍 산12-1임, 산12-3임, 127-1잡",
            label_visibility="collapsed", key="lm_addr_q",
        )
    with sc2:
        do_search = st.button("검색", type="primary", use_container_width=True)
    with sc3:
        if st.button("초기화", use_container_width=True):
            st.session_state.lm_parcels    = []
            st.session_state.lm_preview    = None
            st.session_state.lm_center     = DEFAULT_CENTER
            st.session_state.lm_zoom       = DEFAULT_ZOOM
            st.session_state.lm_last_click = ""
            st.rerun()

    # ── 주변 건물 반경 (항상 표시) ───────────────────────────────────────
    rc1, rc2 = st.columns([4, 2])
    with rc1:
        new_radius = st.slider(
            "🔍 주변 건물 조회 반경",
            min_value=100, max_value=2000, step=100,
            value=st.session_state.lm_nearby_radius,
            format="%dm", key="lm_radius_slider",
        )
    with rc2:
        st.write("")
        st.caption(f"선택 필지 기준 **{new_radius}m** 반경 내 건물 용도 표시")
    if new_radius != st.session_state.lm_nearby_radius:
        st.session_state.lm_nearby_radius = new_radius
        # 반경 변경 시 preview 재조회
        if st.session_state.lm_preview and not st.session_state.lm_preview.get("error"):
            p = st.session_state.lm_preview
            with st.spinner("주변 건물 재조회 중..."):
                nb = _fetch_nearby_buildings(p["lon"], p["lat"], radius_m=new_radius)
            st.session_state.lm_preview["nearby_buildings"] = nb
            st.session_state.lm_preview["nearby_radius"] = new_radius
            st.rerun()

    if do_search and addr_q.strip():
        addresses = _parse_batch_parcel_input(addr_q.strip())
        if len(addresses) > 1:
            # 다중 필지: 기존 목록을 비우고 이번 검색 결과만 쌓음(이전 검색과 섞이지 않게)
            st.session_state.lm_parcels = []
            st.session_state.lm_preview = None
            st.session_state["_pending_map_addresses"] = addresses
            st.rerun()
        else:
            # 단일 필지: BBOX/CQL 지번 매칭 → geocode fallback
            single, jimok_hint = _normalize_pending_addr(
                addresses[0] if addresses else (addr_q.strip(), None)
            )
            with st.spinner("필지 검색 중..."):
                info = _fetch_parcel_by_jibun(
                    single,
                    nearby_radius=st.session_state.lm_nearby_radius,
                    expected_jimok=jimok_hint,
                )
            if info:
                st.session_state.lm_center  = [info["lat"], info["lon"]]
                st.session_state.lm_zoom    = 18
                st.session_state.lm_preview = info
                st.rerun()
            else:
                with st.spinner("좌표 변환 중..."):
                    coords = _geocode_parcel_first_hit(single, jimok_hint)
                if coords:
                    lon_g, lat_g = coords
                    st.session_state.lm_center = [lat_g, lon_g]
                    st.session_state.lm_zoom   = 18
                    parsed_fb = _parse_jibun_address(single)
                    exp_jn = parsed_fb[2] if parsed_fb else None
                    with st.spinner("필지 정보 조회 중..."):
                        info = _fetch_parcel_info(
                            lon_g, lat_g,
                            nearby_radius=st.session_state.lm_nearby_radius,
                            expected_jibun_num=exp_jn,
                            expected_jimok=jimok_hint,
                        )
                    st.session_state.lm_preview = info
                    st.rerun()
                else:
                    st.warning("주소를 찾을 수 없습니다.")

    # ── 합계 (필지 있을 때만) ─────────────────────────────────────────────
    if parcels:
        total_area  = sum(p.get("area_m2") or 0 for p in parcels)
        pyeong      = total_area / 3.3058 if total_area else 0
        total_price = sum(p.get("official_total_price") or 0 for p in parcels)
        zonings     = list(dict.fromkeys(p.get("zoning","") for p in parcels if p.get("zoning")))

        st.markdown("---")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("필지 수",  f"{len(parcels)}필지")
        m2.metric("합산 면적", f"{total_area:,.0f} ㎡" if total_area else "—")
        m3.metric("평수",     f"{pyeong:,.0f} 평" if pyeong else "—")
        m4.metric("공시가액 합계", f"{total_price/1e8:,.1f} 억원" if total_price else "—")
        with m5:
            if st.button("🚀 분석에 활용", type="primary", use_container_width=True, key="lm_apply_btn"):
                _apply_to_analysis(parcels, st.session_state.lm_nearby_radius)

        if zonings:
            st.caption(f"용도지역: {', '.join(zonings)}")

    # ── 미리보기 (클릭/검색 직후) ─────────────────────────────────────────
    if preview and not preview.get("error"):
        st.markdown("---")
        pc1, pc2 = st.columns([5, 1])
        with pc1:
            _render_parcel_card(preview, color=PREVIEW_COLOR, badge="📍 클릭 위치")
        with pc2:
            existing_pnus = {p.get("pnu") for p in parcels if p.get("pnu")}
            prev_pnu = preview.get("pnu", "")
            already  = prev_pnu and prev_pnu in existing_pnus
            st.write("")  # spacing
            if already:
                st.info("이미 추가됨")
            else:
                if st.button("➕ 추가", type="primary", use_container_width=True, key="lm_add_btn"):
                    st.session_state.lm_parcels.append(preview)
                    st.session_state.lm_preview = None
                    st.session_state.lm_last_click = ""  # 동일 좌표 재클릭 허용
                    st.rerun()
    elif preview and preview.get("error"):
        st.error(preview["error"])

    # ── 선택된 필지 목록 (expander) ──────────────────────────────────────
    if parcels:
        st.markdown(f"**선택된 필지 ({len(parcels)}개)**")
        for i, p in enumerate(parcels):
            color  = PARCEL_COLORS[i % len(PARCEL_COLORS)]
            addr_s = p.get("address", f"필지 {i+1}")
            area_s = f"{p['area_m2']:,.0f}㎡" if p.get("area_m2") else ""
            zone_s = p.get("zoning", "")
            label  = (
                f'<span style="color:{color};font-weight:700;font-size:14px">●</span> '
                f'<b>{i+1}.</b> {addr_s}'
                + (f'  <span style="color:#888;font-size:12px">{area_s}</span>' if area_s else "")
                + (f'  <span style="color:#666;font-size:12px">| {zone_s}</span>' if zone_s else "")
            )
            with st.expander(f"{i+1}. {addr_s}  {area_s}", expanded=False):
                ecol1, ecol2 = st.columns([10, 1])
                with ecol1:
                    _render_parcel_card(p, color=color, badge=f"필지 {i+1}")
                with ecol2:
                    st.write("")
                    if st.button("✕", key=f"lm_del_{i}", help="목록에서 제거"):
                        st.session_state.lm_parcels.pop(i)
                        st.rerun()
                    # 건물정보 갱신 (캐시된 데이터에 floor_list 등 신규 필드 없을 때)
                    bld_cache = p.get("building") or {}
                    if p.get("pnu") and "floor_list" not in bld_cache:
                        if st.button("🔄", key=f"lm_refresh_{i}", help="건물정보 재조회"):
                            with st.spinner("건물정보 재조회 중..."):
                                lon_p = p.get("lon") or p.get("x")
                                lat_p = p.get("lat") or p.get("y")
                                if lon_p and lat_p:
                                    refreshed = _fetch_parcel_info(float(lon_p), float(lat_p),
                                                                   nearby_radius=st.session_state.get("lm_nearby_radius", 0))
                                    if refreshed and not refreshed.get("error"):
                                        st.session_state.lm_parcels[i] = refreshed
                                        st.rerun()

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════
    # 하단: 전체 폭 지도
    # ════════════════════════════════════════════════════════════════════
    m = _build_map(
        center  = st.session_state.lm_center,
        zoom    = st.session_state.lm_zoom,
        parcels = parcels,
        preview = preview,
    )

    map_data = st_folium(
        m,
        use_container_width=True,
        height=700,
        returned_objects=["last_clicked", "last_object_clicked", "zoom", "center"],
        key="lm_map",
    )

    st.caption("💡 지도 클릭 → 필지 경계 표시 + 정보 조회  |  지적도 레이어가 기본으로 켜져 있습니다")

    # ── 클릭 이벤트 처리 ──────────────────────────────────────────────
    # last_clicked: 빈 지도 클릭, last_object_clicked: GeoJson 필지 위 클릭
    _raw_click = (map_data or {}).get("last_clicked") or (map_data or {}).get("last_object_clicked")
    c_lat = (_raw_click or {}).get("lat")
    c_lon = (_raw_click or {}).get("lng")
    if c_lat and c_lon:
        click_key = f"{c_lat:.6f},{c_lon:.6f}"
        if click_key != st.session_state.lm_last_click:
            st.session_state.lm_last_click = click_key
            if (map_data or {}).get("zoom"):
                st.session_state.lm_zoom = map_data["zoom"]
            if (map_data or {}).get("center"):
                c = map_data["center"]
                if isinstance(c, dict):
                    st.session_state.lm_center = [c.get("lat", c_lat), c.get("lng", c_lon)]
            with st.spinner("필지 정보 조회 중..."):
                new_info = _fetch_parcel_info(c_lon, c_lat, nearby_radius=st.session_state.lm_nearby_radius)
            st.session_state.lm_preview = new_info
            st.rerun()


# Streamlit pages 진입 시 자동 렌더
try:
    render_land_map_page()
except Exception as _render_err:
    st.error(f"지도 페이지 렌더링 오류: {_render_err}")

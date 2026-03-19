"""
건축물대장 허브 API 클라이언트 (data.go.kr 건축HUB)
End Point: https://apis.data.go.kr/1613000/BldRgstHubService

구현 엔드포인트:
  getBrJijiguInfo        지역·지구·구역
  getBrBasisOulnInfo     기본개요 (대장종류/구분, 주소)
  getBrRecapTitleInfo    총괄표제부 (건폐율, 용적률, 면적, 층수, 주차)
  getBrTitleInfo         표제부 (건물명, 주용도, 구조, 주차방식별 대수)
  getBrFlrOulnInfo       층별개요 (층별 구조·용도·면적)
  getBrExposPubuseAreaInfo  전유공용면적 (전유/공용 구분별 면적)
  getBrHsprcInfo         주택가격
  getBrExposInfo         전유부 (동호명칭)
  getBrAtchJibunInfo     부속지번

환경변수: KHUG_API_KEY
"""

import logging
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

_BASE_URL = "https://apis.data.go.kr/1613000/BldRgstHubService"


def _api_key() -> str:
    return os.getenv("KHUG_API_KEY", "")


def _pnu_to_params(pnu: str) -> Optional[dict]:
    """
    PNU 19자리 → 건축HUB 공통 요청 파라미터

    PNU: AAAAABBBBBCDDDDEEEE
      A[0:5]  sigunguCd  시군구코드
      B[5:10] bjdongCd   법정동코드
      C[10]   platGbCd   대지구분 (0=대지, 1=산, 2=블록)
      D[11:15] bun       본번
      E[15:19] ji        부번
    """
    if not pnu or len(pnu) < 19:
        return None
    return {
        "sigunguCd": pnu[0:5],
        "bjdongCd":  pnu[5:10],
        "platGbCd":  pnu[10],
        "bun":       pnu[11:15],   # 4자리 제로패딩 그대로 (0017 등)
        "ji":        pnu[15:19],   # 4자리 제로패딩 그대로 (0000 등)
    }


def _request(endpoint: str, pnu_params: dict, extra: dict = None,
             num_rows: int = 100) -> list:
    """건축HUB API 호출 → items 리스트 (오류 시 [])"""
    key = _api_key()
    if not key:
        logger.debug("KHUG_API_KEY 미설정")
        return []

    params = {
        "serviceKey": key,
        "numOfRows":  str(num_rows),
        "pageNo":     "1",
        "_type":      "json",
        **pnu_params,
    }
    if extra:
        params.update(extra)

    try:
        r = requests.get(f"{_BASE_URL}/{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        data   = r.json()
        header = data.get("response", {}).get("header", {})
        body   = data.get("response", {}).get("body", {})
        rc     = str(header.get("resultCode", ""))
        if rc and rc not in ("00", "0000"):
            logger.warning("건축HUB [%s] 결과코드: %s %s", endpoint, rc,
                           header.get("resultMsg", ""))
        total_count = body.get("totalCount", 0)
        items_raw = body.get("items") or {}
        if not items_raw:
            logger.debug("건축HUB [%s] 결과 없음 (totalCount=%s, %s/%s/gb%s/%s-%s)",
                         endpoint, total_count,
                         pnu_params.get("sigunguCd"), pnu_params.get("bjdongCd"),
                         pnu_params.get("platGbCd"), pnu_params.get("bun"), pnu_params.get("ji"))
            return []
        item = items_raw.get("item", [])
        if isinstance(item, dict):
            result_items = [item]
        else:
            result_items = item if isinstance(item, list) else []
        logger.debug("건축HUB [%s] %d건 수신 (gb%s/%s-%s)",
                     endpoint, len(result_items),
                     pnu_params.get("platGbCd"), pnu_params.get("bun"), pnu_params.get("ji"))
        return result_items
    except Exception as e:
        logger.warning("건축HUB [%s] 오류: %s", endpoint, e)
        return []


def _request_with_gb_fallback(endpoint: str, pnu_params: dict, extra: dict = None,
                               num_rows: int = 100) -> list:
    """platGbCd 0→1→2 순서로 시도 후 첫 번째 결과 반환 (PNU gb코드 불일치 대비)"""
    # 먼저 원래 gb코드 시도
    items = _request(endpoint, pnu_params, extra, num_rows)
    if items:
        return items
    # 결과 없으면 다른 gb코드 시도
    orig_gb = pnu_params.get("platGbCd", "0")
    for gb in ("0", "1", "2"):
        if gb == orig_gb:
            continue
        alt_params = {**pnu_params, "platGbCd": gb}
        items = _request(endpoint, alt_params, extra, num_rows)
        if items:
            logger.debug("건축HUB [%s] platGbCd=%s fallback으로 %d건 수신", endpoint, gb, len(items))
            return items
    return []


# ──────────────────────────────────────────────────────────────────────────────
# 개별 조회 함수
# ──────────────────────────────────────────────────────────────────────────────

def get_jiguinfo(pnu: str) -> dict:
    """지역·지구·구역 (getBrJijiguInfo)"""
    pp = _pnu_to_params(pnu)
    if not pp:
        return {}

    items = _request("getBrJijiguInfo", pp)
    if not items:
        return {}

    zoning, districts, all_entries = "", [], []
    for item in items:
        gb_cd = str(item.get("jiyukGbCd", ""))
        gb_nm = item.get("jiyukGbCdNm", "").strip()
        name  = item.get("jiyukCdNm", "").strip()
        if not name:
            continue
        all_entries.append({"type": gb_nm or gb_cd, "name": name})
        if gb_cd == "1":
            if not zoning:
                zoning = name
        else:
            districts.append(name)

    return {"zoning": zoning, "districts": districts,
            "all_entries": all_entries, "source": "건축HUB getBrJijiguInfo"}


def get_basic_outline(pnu: str) -> dict:
    """기본개요 (getBrBasisOulnInfo) — 대장종류/구분, 건물명, 주소"""
    pp = _pnu_to_params(pnu)
    if not pp:
        return {}
    items = _request("getBrBasisOulnInfo", pp)
    if not items:
        return {}
    r = items[0]
    return {
        "register_kind":  str(r.get("ladrRegstCdNm") or "").strip(),   # 대장종류
        "register_type":  str(r.get("regstrKindCdNm") or "").strip(),  # 대장구분
        "bld_name":       str(r.get("bldNm") or "").strip(),
        "new_address":    str(r.get("newPlatPlc") or "").strip(),       # 새주소
        "old_address":    str(r.get("platPlc") or "").strip(),          # 지번주소
        "source":         "건축HUB getBrBasisOulnInfo",
    }


def get_floor_info(pnu: str) -> list:
    """
    층별개요 (getBrFlrOulnInfo)

    Returns list of dicts:
      floor_gb   지상/지하
      floor_no   층번호
      structure  층구조
      purpose    층용도
      area_m2    층면적(㎡)
    """
    pp = _pnu_to_params(pnu)
    if not pp:
        return []
    items = _request_with_gb_fallback("getBrFlrOulnInfo", pp, num_rows=200)
    floors = []
    for item in items:
        try:
            area = float(item.get("area") or 0)
        except (ValueError, TypeError):
            area = 0.0
        gb_cd = str(item.get("flrGbCd", "")).strip()
        gb_nm = str(item.get("flrGbCdNm", "") or ("지상" if gb_cd == "1" else "지하")).strip()
        floors.append({
            "floor_gb":  gb_nm,
            "floor_no":  str(item.get("flrNo") or "").strip(),
            "structure": str(item.get("strctCdNm") or "").strip(),
            "purpose":   str(item.get("mainPurpsCdNm") or "").strip(),
            "area_m2":   area,
        })
    return floors


def get_exclusive_area(pnu: str) -> list:
    """
    전유공용면적 (getBrExposPubuseAreaInfo)

    Returns list of dicts:
      floor_gb      지상/지하
      floor_no      층번호
      division      전유/공용 구분
      structure     구조
      purpose       용도
      area_m2       면적(㎡)
    """
    pp = _pnu_to_params(pnu)
    if not pp:
        return []
    items = _request_with_gb_fallback("getBrExposPubuseAreaInfo", pp, num_rows=200)
    result = []
    for item in items:
        try:
            area = float(item.get("area") or 0)
        except (ValueError, TypeError):
            area = 0.0
        div_cd = str(item.get("exposPubuseGbCd", "")).strip()
        div_nm = str(item.get("exposPubuseGbCdNm", "") or
                     ("전유" if div_cd == "1" else "공용")).strip()
        gb_nm  = str(item.get("flrGbCdNm", "")).strip()
        result.append({
            "floor_gb":  gb_nm,
            "floor_no":  str(item.get("flrNo") or "").strip(),
            "division":  div_nm,
            "structure": str(item.get("strctCdNm") or "").strip(),
            "purpose":   str(item.get("mainPurpsCdNm") or "").strip(),
            "area_m2":   area,
        })
    return result


def get_housing_price(pnu: str) -> list:
    """
    주택가격 (getBrHsprcInfo)

    Returns list of dicts:
      year      기준년도
      month     기준월
      price     주택가격(원)
      dong_nm   동명칭
      ho_nm     호명칭
    """
    pp = _pnu_to_params(pnu)
    if not pp:
        return []
    items = _request_with_gb_fallback("getBrHsprcInfo", pp, num_rows=50)
    result = []
    for item in items:
        try:
            price = int(float(item.get("hsprc") or 0))
        except (ValueError, TypeError):
            price = 0
        result.append({
            "year":    str(item.get("stdrYear") or "").strip(),
            "month":   str(item.get("stdrMt") or "").strip(),
            "price":   price,
            "dong_nm": str(item.get("dongNm") or "").strip(),
            "ho_nm":   str(item.get("hoNm") or "").strip(),
        })
    return result


def get_exclusive_info(pnu: str) -> list:
    """전유부 (getBrExposInfo) — 동호명칭"""
    pp = _pnu_to_params(pnu)
    if not pp:
        return []
    items = _request("getBrExposInfo", pp, num_rows=100)
    result = []
    for item in items:
        result.append({
            "dong_nm":   str(item.get("dongNm") or "").strip(),
            "ho_nm":     str(item.get("hoNm") or "").strip(),
            "new_addr":  str(item.get("newPlatPlc") or "").strip(),
        })
    return result


def get_attached_lots(pnu: str) -> list:
    """부속지번 (getBrAtchJibunInfo)"""
    pp = _pnu_to_params(pnu)
    if not pp:
        return []
    items = _request("getBrAtchJibunInfo", pp)
    result = []
    for item in items:
        result.append({
            "address":    str(item.get("atchPlatPlc") or item.get("platPlc") or "").strip(),
            "new_addr":   str(item.get("newPlatPlc") or "").strip(),
            "atch_type":  str(item.get("atchRegstCdNm") or "").strip(),
        })
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 통합 조회 함수
# ──────────────────────────────────────────────────────────────────────────────

def get_building_info(pnu: str) -> dict:
    """
    PNU → 건축물 전체 정보 (모든 엔드포인트 병렬 조회)

    Returns dict:
      bld_name, main_purpose, structure
      arch_area, total_area, bcr, vlr
      floors_above, floors_below, approve_date
      parking_total, parking_indoor_auto, parking_outdoor_auto
        parking_indoor_mech, parking_outdoor_mech
      roof_structure
      floor_list       → get_floor_info() 결과
      exclusive_areas  → get_exclusive_area() 결과 (있을 때)
      housing_prices   → get_housing_price() 결과 (있을 때)
      attached_lots    → get_attached_lots() 결과 (있을 때)
      source
    """
    pp = _pnu_to_params(pnu)
    if not pp:
        return {}

    result: dict = {}

    def _task_recap():
        return "recap", _request_with_gb_fallback("getBrRecapTitleInfo", pp)

    def _task_title():
        return "title", _request_with_gb_fallback("getBrTitleInfo", pp)

    def _task_floors():
        return "floors", get_floor_info(pnu)

    def _task_excl_area():
        return "excl_area", get_exclusive_area(pnu)

    def _task_hsprc():
        return "hsprc", get_housing_price(pnu)

    def _task_atch():
        return "atch", get_attached_lots(pnu)

    tasks = [_task_recap, _task_title, _task_floors,
             _task_excl_area, _task_hsprc, _task_atch]
    enriched = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(t): t.__name__ for t in tasks}
        try:
            for future in as_completed(futures, timeout=25):
                try:
                    k, v = future.result()
                    enriched[k] = v
                except Exception as e:
                    logger.debug("건축HUB 병렬 오류 (%s): %s", futures[future], e)
        except TimeoutError:
            logger.debug("건축HUB 내부 병렬 일부 미완료 (timeout)")

    # ── 총괄표제부 ─────────────────────────────────────────────────────────
    recap_items = enriched.get("recap") or []
    if recap_items:
        r = recap_items[0]
        def _f(v):
            try: return float(v) if v not in (None, "", "0") else None
            except: return None
        def _i(v):
            try: return int(v) if v not in (None, "", "0") else None
            except: return None

        for _dst, _src in [
            ("arch_area",      _f(r.get("archArea"))),
            ("total_area",     _f(r.get("totArea"))),
            ("vlr_area",       _f(r.get("vlRatEstmTotArea"))),  # 용적률산정연면적
            ("plat_area",      _f(r.get("platArea"))),
            ("bcr",            _f(r.get("bcRat"))),
            ("vlr",            _f(r.get("vlRat"))),
            ("building_height",_f(r.get("heit"))),              # 높이(m)
            ("floors_above",   _i(r.get("grndFlrCnt"))),
            ("floors_below",   _i(r.get("ugrndFlrCnt"))),
            ("elev_ride",      _i(r.get("rideUseElvtCnt"))),    # 승용승강기
            ("elev_emergency", _i(r.get("emgenUseElvtCnt"))),   # 비상용승강기
            ("household_cnt",  _i(r.get("hhldCnt"))),           # 세대수
            ("family_cnt",     _i(r.get("fmlyCnt"))),           # 가구수
            ("parking_total",  _i(r.get("totPkngCnt"))),
            ("parking_indoor_auto",  _i(r.get("indrAutoUtcnt"))),
            ("parking_outdoor_auto", _i(r.get("oudrAutoUtcnt"))),
            ("parking_indoor_mech",  _i(r.get("indrMechUtcnt"))),
            ("parking_outdoor_mech", _i(r.get("oudrMechUtcnt"))),
        ]:
            if _src is not None: result[_dst] = _src

        approve_raw = str(r.get("useAprDay") or "").strip()
        if len(approve_raw) == 8 and approve_raw.isdigit():
            result["approve_date"] = f"{approve_raw[:4]}-{approve_raw[4:6]}-{approve_raw[6:]}"

        for _dst, _src_key in [
            ("bld_name",     "bldNm"),
            ("main_purpose", "mainPurpsCdNm"),
            ("structure",    "strctCdNm"),
        ]:
            v = str(r.get(_src_key) or "").strip()
            if v: result[_dst] = v

    # ── 표제부 (누락 보완 + 주차 상세) ────────────────────────────────────
    title_items = enriched.get("title") or []
    if title_items:
        t = title_items[0]
        if not result.get("bld_name"):
            nm = str(t.get("bldNm") or "").strip()
            if nm: result["bld_name"] = nm
        if not result.get("main_purpose"):
            mp = str(t.get("mainPurpsCdNm") or "").strip()
            if mp: result["main_purpose"] = mp
        if not result.get("structure"):
            st_ = str(t.get("strctCdNm") or "").strip()
            if st_: result["structure"] = st_
        roof = str(t.get("roofCdNm") or "").strip()
        if roof: result["roof_structure"] = roof

        # 표제부 보완 (총괄표제부에 없는 필드들)
        def _park(v):
            try: return int(v) if v not in (None, "", "0") else None
            except: return None

        for _dst, _src_key in [
            ("parking_indoor_auto",  "indrAutoUtcnt"),
            ("parking_outdoor_auto", "oudrAutoUtcnt"),
            ("parking_indoor_mech",  "indrMechUtcnt"),
            ("parking_outdoor_mech", "oudrMechUtcnt"),
            ("parking_total",        "pklotCnt"),     # 주차장면수합계 (총괄표제부에 없을 때)
        ]:
            if not result.get(_dst):
                v = _park(t.get(_src_key))
                if v: result[_dst] = v

        if not result.get("parking_total"):
            total_pk = sum(result.get(k) or 0 for k in [
                "parking_indoor_auto","parking_outdoor_auto",
                "parking_indoor_mech","parking_outdoor_mech",
            ])
            if total_pk: result["parking_total"] = total_pk

        for _dst, _src_key in [
            ("roof_structure",  "roofCdNm"),
            ("plat_area",       "platArea"),
            ("vlr_area",        "vlRatEstmTotArea"),
            ("building_height", "heit"),
            ("elev_ride",       "rideUseElvtCnt"),
            ("elev_emergency",  "emgenUseElvtCnt"),
            ("household_cnt",   "hhldCnt"),
            ("family_cnt",      "fmlyCnt"),
        ]:
            if not result.get(_dst):
                raw = t.get(_src_key)
                if raw not in (None, "", "0"):
                    try:
                        result[_dst] = float(raw) if "." in str(raw) else (
                            int(raw) if str(raw).isdigit() else str(raw).strip()
                        )
                    except: pass

    # ── 층별개요 ───────────────────────────────────────────────────────────
    floors = enriched.get("floors") or []
    if floors:
        result["floor_list"] = floors

    # ── 전유공용면적 ────────────────────────────────────────────────────────
    excl_areas = enriched.get("excl_area") or []
    if excl_areas:
        result["exclusive_areas"] = excl_areas

    # ── 주택가격 ────────────────────────────────────────────────────────────
    hsprc = enriched.get("hsprc") or []
    if hsprc:
        result["housing_prices"] = hsprc

    # ── 부속지번 ────────────────────────────────────────────────────────────
    atch = enriched.get("atch") or []
    if atch:
        result["attached_lots"] = atch

    if result:
        result["source"] = "건축HUB"
    return result

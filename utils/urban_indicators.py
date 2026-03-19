"""도시 지표 자동 추출 및 정합성 검증 모듈"""

import re
from typing import Dict, List, Optional


class UrbanIndicatorExtractor:
    """
    문서에서 도시 단위 수치 지표를 추출하고 교차 검증한다.
    - 인구수 / 가구수 → 가구당 인구 논리 검증
    - 면적 / 인구 → 인구밀도 계산 후 기재값과 비교
    - 용도지역 비율 합계 → 100% 여부 검증
    """

    _POPULATION_PATTERN = re.compile(r'인구\s*[:\s]*([0-9,]+)\s*(?:명|인)(?!\s*/)')
    _HOUSEHOLD_PATTERN = re.compile(r'(?:가구|세대)\s*[:\s]*([0-9,]+)\s*(?:가구|세대|호)')
    _AREA_PATTERN = re.compile(
        r'(?:총?면적|사업면적|행정구역\s*면적)\s*[:\s]*([0-9,]+\.?[0-9]*)\s*(㎢|km²|ha|㎡)'
    )
    _DENSITY_PATTERN = re.compile(
        r'인구밀도\s*[:\s]*([0-9,]+\.?[0-9]*)\s*(?:명/㎢|인/㎢|명/ha|인/ha)'
    )
    _ZONING_PATTERN = re.compile(
        r'([가-힣]+(?:지역|지구))\s*[:\s]*([0-9]+\.?[0-9]*)\s*%'
    )

    def extract(self, text: str) -> Dict:
        """텍스트에서 도시 지표를 추출한다."""
        indicators: Dict = {}

        pop_match = self._POPULATION_PATTERN.search(text)
        if pop_match:
            indicators['population'] = int(pop_match.group(1).replace(',', ''))

        hh_match = self._HOUSEHOLD_PATTERN.search(text)
        if hh_match:
            indicators['households'] = int(hh_match.group(1).replace(',', ''))

        area_match = self._AREA_PATTERN.search(text)
        if area_match:
            indicators['area'] = float(area_match.group(1).replace(',', ''))
            indicators['area_unit'] = area_match.group(2)

        density_match = self._DENSITY_PATTERN.search(text)
        if density_match:
            indicators['density_stated'] = float(density_match.group(1).replace(',', ''))

        zoning_items = self._ZONING_PATTERN.findall(text)
        if zoning_items:
            indicators['zoning'] = {name: float(pct) for name, pct in zoning_items}

        return indicators

    def validate(self, indicators: Dict) -> List[Dict]:
        """
        지표 간 정합성을 검증한다.

        반환: [{'item', 'stated', 'calculated', 'unit', 'ok', 'note'}]
        """
        results: List[Dict] = []

        # 1. 가구당 인구 검증 (정상 범위: 1.5~5.0명/가구)
        pop = indicators.get('population')
        hh = indicators.get('households')
        if pop and hh and hh > 0:
            ratio = pop / hh
            ok = 1.5 <= ratio <= 5.0
            results.append({
                'item': '가구당 인구',
                'stated': None,
                'calculated': round(ratio, 2),
                'unit': '명/가구',
                'ok': ok,
                'note': '정상 범위' if ok else f'비정상 ({ratio:.2f}명/가구)',
            })

        # 2. 인구밀도 검증
        area = indicators.get('area')
        density_stated = indicators.get('density_stated')
        if pop and area and area > 0 and density_stated:
            area_unit = indicators.get('area_unit', '')
            if 'ha' in area_unit:
                area_km2 = area / 100.0
            elif '㎡' in area_unit and '㎢' not in area_unit:
                area_km2 = area / 1_000_000.0
            else:
                area_km2 = area
            calc_density = pop / area_km2 if area_km2 > 0 else 0.0
            error_rate = abs(calc_density - density_stated) / density_stated if density_stated > 0 else 0.0
            results.append({
                'item': '인구밀도',
                'stated': density_stated,
                'calculated': round(calc_density, 1),
                'unit': '명/㎢',
                'ok': error_rate <= 0.1,
                'note': '정합' if error_rate <= 0.1 else f'오차 {error_rate * 100:.1f}%',
            })

        # 3. 용도지역 비율 합계 검증 (±5% 허용)
        zoning = indicators.get('zoning', {})
        if zoning:
            total = sum(zoning.values())
            ok = abs(total - 100.0) <= 5.0
            results.append({
                'item': '용도지역 비율 합계',
                'stated': None,
                'calculated': round(total, 1),
                'unit': '%',
                'ok': ok,
                'note': '합계 100%' if ok else f'합계 {total:.1f}% (불일치)',
            })

        return results

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    gpd = None

import pandas as pd
import streamlit as st
from typing import Dict, Any, Optional, List
import os
import zipfile
import io

try:
    import pyproj
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False
    pyproj = None


class GeoDataLoader:
    """도시공간데이터 Shapefile을 로드하고 처리하는 클래스"""
    
    def __init__(self):
        if not GEOPANDAS_AVAILABLE:
            raise ImportError(
                "geopandas가 설치되지 않았습니다. "
                "conda를 사용하여 설치하세요: conda install -c conda-forge geopandas "
                "또는 pip를 사용하세요: pip install geopandas"
            )
        # 한국 좌표계 정의 (CRS)
        self.korean_crs = {
            'GRS80': 'EPSG:5186',  # GRS80(EPSG:5186) - 가장 일반적
            'WGS84': 'EPSG:4326',  # WGS84 - 위경도
            'Bessel': 'EPSG:5174',  # Bessel 1841
            'EPSG5179': 'EPSG:5179',  # KATEC
        }
    
    def load_shapefile_from_zip(self, zip_file_data: bytes, encoding: str = 'cp949') -> Dict[str, Any]:
        """
        ZIP 파일에서 Shapefile을 로드합니다.
        
        Args:
            zip_file_data: ZIP 파일의 바이트 데이터
            encoding: 문자 인코딩 (기본값: cp949 - WINDOWS-949)
        
        Returns:
            Dict with success status and GeoDataFrame or error message
        """
        try:
            # 메모리에서 ZIP 파일 읽기
            with zipfile.ZipFile(io.BytesIO(zip_file_data), 'r') as zip_ref:
                # .shp 파일 찾기
                shp_files = [f for f in zip_ref.namelist() if f.endswith('.shp')]
                
                if not shp_files:
                    return {
                        'success': False,
                        'error': 'ZIP 파일에 .shp 파일이 없습니다.'
                    }
                
                # 첫 번째 shp 파일 사용
                shp_file = shp_files[0]
                
                # 임시 폴더 생성
                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir:
                    # ZIP 파일 압축 해제
                    zip_ref.extractall(temp_dir)
                    
                    # Shapefile 경로
                    shp_path = os.path.join(temp_dir, shp_file)
                    
                    # GeoDataFrame 로드
                    gdf = gpd.read_file(shp_path, encoding=encoding)
                    
                    # CRS 정보 확인 및 변환
                    gdf_transformed = self._transform_crs(gdf)
                    
                    return {
                        'success': True,
                        'gdf': gdf_transformed,
                        'crs': gdf_transformed.crs.to_string() if gdf_transformed.crs else None,
                        'feature_count': len(gdf_transformed),
                        'columns': gdf_transformed.columns.tolist(),
                        'bounds': gdf_transformed.total_bounds.tolist(),
                        'geometry_type': gdf_transformed.geometry.geom_type.value_counts().to_dict()
                    }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Shapefile 로드 중 오류 발생: {str(e)}'
            }
    
    def load_shapefile_from_files(self, file_dict: Dict[str, bytes], encoding: str = 'cp949') -> Dict[str, Any]:
        """
        개별 파일들로부터 Shapefile을 로드합니다.
        
        Args:
            file_dict: {'shp': bytes, 'shx': bytes, 'dbf': bytes, ...} 형식의 딕셔너리
            encoding: 문자 인코딩
        
        Returns:
            Dict with success status and GeoDataFrame or error message
        """
        try:
            import tempfile
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # 각 파일을 임시 디렉토리에 저장
                for file_type, file_data in file_dict.items():
                    if file_type in ['shp', 'shx', 'dbf', 'prj', 'cpg']:
                        file_path = os.path.join(temp_dir, f'temp.{file_type}')
                        with open(file_path, 'wb') as f:
                            f.write(file_data)
                
                # Shapefile 로드
                shp_path = os.path.join(temp_dir, 'temp.shp')
                gdf = gpd.read_file(shp_path, encoding=encoding)
                
                # CRS 정보 확인 및 변환
                gdf_transformed = self._transform_crs(gdf)
                
                return {
                    'success': True,
                    'gdf': gdf_transformed,
                    'crs': gdf_transformed.crs.to_string() if gdf_transformed.crs else None,
                    'feature_count': len(gdf_transformed),
                    'columns': gdf_transformed.columns.tolist(),
                    'bounds': gdf_transformed.total_bounds.tolist(),
                    'geometry_type': gdf_transformed.geometry.geom_type.value_counts().to_dict()
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Shapefile 로드 중 오류 발생: {str(e)}'
            }
    
    def _transform_crs(self, gdf: gpd.GeoDataFrame, target_crs: str = 'EPSG:4326') -> gpd.GeoDataFrame:
        """
        GeoDataFrame의 좌표계를 변환합니다.
        
        Args:
            gdf: 원본 GeoDataFrame
            target_crs: 목표 좌표계 (기본값: EPSG:4326 - WGS84, Streamlit 지도와 호환)
        
        Returns:
            변환된 GeoDataFrame
        """
        try:
            # CRS가 없으면 한국 일반 좌표계로 가정
            if gdf.crs is None:
                gdf.crs = 'EPSG:5186'  # GRS80
            
            # Streamlit 지도는 WGS84(EPSG:4326)를 사용하므로 변환
            if gdf.crs.to_string() != target_crs:
                gdf = gdf.to_crs(target_crs)
            
            return gdf
        
        except Exception as e:
            print(f"좌표계 변환 중 오류 (원본 유지): {str(e)}")
            return gdf
    
    def gdf_to_dataframe_for_map(self, gdf: gpd.GeoDataFrame) -> pd.DataFrame:
        """
        GeoDataFrame을 Streamlit st.map()에서 사용할 수 있는 DataFrame으로 변환합니다.
        
        Args:
            gdf: GeoDataFrame
        
        Returns:
            DataFrame with lat, lon columns
        """
        try:
            # 중심점(centroid) 계산
            gdf_centroid = gdf.copy()
            gdf_centroid['geometry'] = gdf_centroid.geometry.centroid
            
            # 위경도 추출
            gdf_centroid['lon'] = gdf_centroid.geometry.x
            gdf_centroid['lat'] = gdf_centroid.geometry.y
            
            # DataFrame으로 변환 (geometry 컬럼 제외)
            df = pd.DataFrame(gdf_centroid.drop(columns=['geometry']))
            
            return df
        
        except Exception as e:
            print(f"DataFrame 변환 중 오류: {str(e)}")
            # 변환 실패 시 빈 DataFrame 반환
            return pd.DataFrame()
    
    def create_folium_map_multilayer(self, geo_layers_dict: Dict[str, gpd.GeoDataFrame]) -> Optional[Any]:
        """
        여러 GeoDataFrame을 하나의 Folium 지도로 합칩니다.
        
        Args:
            geo_layers_dict: {'레이어명': GeoDataFrame} 형식의 딕셔너리
        
        Returns:
            Folium Map 객체 또는 None
        """
        try:
            import folium
        except ImportError:
            return None
        
        try:
            if not geo_layers_dict:
                return None
            
            # 모든 레이어의 경계 계산
            all_bounds = []
            for gdf in geo_layers_dict.values():
                bounds = gdf.total_bounds
                all_bounds.append(bounds)
            
            # 전체 경계 계산
            min_x = min(b[0] for b in all_bounds)
            min_y = min(b[1] for b in all_bounds)
            max_x = max(b[2] for b in all_bounds)
            max_y = max(b[3] for b in all_bounds)
            
            center_lat = (min_y + max_y) / 2
            center_lon = (min_x + max_x) / 2
            
            # Folium 지도 생성
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=10,
                tiles='OpenStreetMap'
            )
            
            # 각 레이어 추가
            colors = ['#3388ff', '#ff3388', '#33ff88', '#ff8833', '#8833ff', '#33ffaa']
            color_idx = 0
            
            # 대용량 데이터 처리를 위한 최대 피처 수 제한
            MAX_FEATURES_PER_LAYER = 10000  # 레이어당 최대 피처 수
            
            for layer_name, gdf in geo_layers_dict.items():
                # 대용량 레이어는 샘플링
                original_count = len(gdf)
                if original_count > MAX_FEATURES_PER_LAYER:
                    # 랜덤 샘플링 (균등하게 분포)
                    gdf = gdf.sample(n=MAX_FEATURES_PER_LAYER, random_state=42)
                    print(f"⚠️ {layer_name}: {original_count:,}개 피처 중 {MAX_FEATURES_PER_LAYER:,}개만 표시합니다.")
                
                # Geometry 타입에 따라 다르게 처리
                geom_types = gdf.geometry.geom_type.unique()
                color = colors[color_idx % len(colors)]
                color_idx += 1
                
                for geom_type in geom_types:
                    gdf_subset = gdf[gdf.geometry.geom_type == geom_type]
                    
                    if geom_type in ['Polygon', 'MultiPolygon']:
                        def make_style(color_val):
                            return lambda feature: {
                                'fillColor': color_val,
                                'color': color_val,
                                'weight': 2,
                                'fillOpacity': 0.3,
                            }
                        folium.GeoJson(
                            gdf_subset.to_json(),
                            name=f"{layer_name} ({geom_type})",
                            style_function=make_style(color),
                            tooltip=folium.GeoJsonTooltip(
                                fields=[col for col in gdf_subset.columns if col != 'geometry'][:5],
                                aliases=[col for col in gdf_subset.columns if col != 'geometry'][:5],
                                sticky=True
                            )
                        ).add_to(m)
                    
                    elif geom_type in ['LineString', 'MultiLineString']:
                        def make_line_style(color_val):
                            return lambda feature: {
                                'color': color_val,
                                'weight': 3,
                            }
                        folium.GeoJson(
                            gdf_subset.to_json(),
                            name=f"{layer_name} ({geom_type})",
                            style_function=make_line_style(color),
                            tooltip=folium.GeoJsonTooltip(
                                fields=[col for col in gdf_subset.columns if col != 'geometry'][:5],
                                aliases=[col for col in gdf_subset.columns if col != 'geometry'][:5],
                            )
                        ).add_to(m)
                    
                    elif geom_type in ['Point', 'MultiPoint']:
                        # Point를 Marker로 추가 (첫 1000개만)
                        for idx, row in gdf_subset.head(1000).iterrows():
                            popup_text = "<br>".join([
                                f"<b>{col}:</b> {row[col]}" 
                                for col in row.index 
                                if col != 'geometry' and pd.notna(row[col])
                            ])
                            folium.Marker(
                                location=[row.geometry.y, row.geometry.x],
                                popup=folium.Popup(popup_text, max_width=300),
                                icon=folium.Icon(color='red', icon='info-sign')
                            ).add_to(m)
            
            # 레이어 컨트롤 추가
            folium.LayerControl().add_to(m)
            
            # 전체 경계에 맞춰 줌 조정
            m.fit_bounds([[min_y, min_x], [max_y, max_x]])
            
            return m
            
        except Exception as e:
            print(f"Folium 다중 레이어 지도 생성 중 오류: {str(e)}")
            return None
    
    def create_folium_map(self, gdf: gpd.GeoDataFrame, layer_name: str = "Layer") -> Optional[Any]:
        """
        GeoDataFrame을 Folium 지도로 변환합니다.
        Polygon, LineString, Point 등 모든 geometry 타입을 지원합니다.
        
        Args:
            gdf: GeoDataFrame
            layer_name: 레이어 이름
        
        Returns:
            Folium Map 객체 또는 None (folium이 없을 경우)
        """
        try:
            import folium
            from folium import plugins
        except ImportError:
            return None
        
        try:
            # 중심점 계산
            bounds = gdf.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2
            
            # Folium 지도 생성
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=10,
                tiles='OpenStreetMap'
            )
            
            # Geometry 타입에 따라 다르게 처리
            geom_types = gdf.geometry.geom_type.unique()
            
            for geom_type in geom_types:
                gdf_subset = gdf[gdf.geometry.geom_type == geom_type]
                
                if geom_type in ['Polygon', 'MultiPolygon']:
                    # Polygon을 GeoJson으로 추가
                    folium.GeoJson(
                        gdf_subset.to_json(),
                        name=f"{layer_name} ({geom_type})",
                        style_function=lambda feature: {
                            'fillColor': '#3388ff',
                            'color': '#3388ff',
                            'weight': 2,
                            'fillOpacity': 0.3,
                        },
                        tooltip=folium.GeoJsonTooltip(
                            fields=[col for col in gdf_subset.columns if col != 'geometry'][:5],
                            aliases=[col for col in gdf_subset.columns if col != 'geometry'][:5],
                            sticky=True
                        )
                    ).add_to(m)
                
                elif geom_type in ['LineString', 'MultiLineString']:
                    # LineString을 GeoJson으로 추가
                    folium.GeoJson(
                        gdf_subset.to_json(),
                        name=f"{layer_name} ({geom_type})",
                        style_function=lambda feature: {
                            'color': '#ff3388',
                            'weight': 3,
                        },
                        tooltip=folium.GeoJsonTooltip(
                            fields=[col for col in gdf_subset.columns if col != 'geometry'][:5],
                            aliases=[col for col in gdf_subset.columns if col != 'geometry'][:5],
                        )
                    ).add_to(m)
                
                elif geom_type in ['Point', 'MultiPoint']:
                    # Point를 Marker로 추가 (첫 1000개만)
                    for idx, row in gdf_subset.head(1000).iterrows():
                        popup_text = "<br>".join([
                            f"<b>{col}:</b> {row[col]}" 
                            for col in row.index 
                            if col != 'geometry' and pd.notna(row[col])
                        ])
                        folium.Marker(
                            location=[row.geometry.y, row.geometry.x],
                            popup=folium.Popup(popup_text, max_width=300),
                            icon=folium.Icon(color='red', icon='info-sign')
                        ).add_to(m)
            
            # 레이어 컨트롤 추가
            folium.LayerControl().add_to(m)
            
            # 전체 경계에 맞춰 줌 조정
            m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
            
            return m
            
        except Exception as e:
            print(f"Folium 지도 생성 중 오류: {str(e)}")
            return None
    
    def get_layer_info(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """
        레이어의 상세 정보를 반환합니다.
        
        Args:
            gdf: GeoDataFrame
        
        Returns:
            레이어 정보 딕셔너리
        """
        try:
            bounds = gdf.total_bounds
            
            return {
                'feature_count': len(gdf),
                'columns': gdf.columns.tolist(),
                'geometry_columns': [col for col in gdf.columns if gdf[col].dtype.name == 'geometry'][0] if any(gdf[col].dtype.name == 'geometry' for col in gdf.columns) else 'geometry',
                'crs': gdf.crs.to_string() if gdf.crs else 'Not specified',
                'bounds': {
                    'min_x': bounds[0],
                    'min_y': bounds[1],
                    'max_x': bounds[2],
                    'max_y': bounds[3]
                },
                'geometry_types': gdf.geometry.geom_type.value_counts().to_dict(),
                'has_attribute_data': len(gdf.columns) > 1,
                'attribute_columns': [col for col in gdf.columns if col != 'geometry']
            }
        except Exception as e:
            return {
                'error': f'정보 추출 중 오류: {str(e)}'
            }


def validate_shapefile_data(gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    """
    로드된 Shapefile 데이터의 유효성을 검증합니다.
    
    Args:
        gdf: GeoDataFrame
    
    Returns:
        검증 결과 딕셔너리
    """
    try:
        issues = []
        warnings = []
        
        # 기본 검증
        if gdf is None or len(gdf) == 0:
            issues.append('데이터가 비어있습니다.')
        
        # 좌표계 확인
        if gdf.crs is None:
            warnings.append('좌표계 정보가 없습니다.')
        
        # 유효하지 않은 geometry 확인
        invalid_geom = gdf[~gdf.geometry.is_valid]
        if len(invalid_geom) > 0:
            issues.append(f'유효하지 않은 geometry가 {len(invalid_geom)}개 있습니다.')
        
        # 중복 geometry 확인
        if gdf.duplicated(subset=['geometry']).any():
            warnings.append('중복된 geometry가 있습니다.')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    except Exception as e:
        return {
            'valid': False,
            'issues': [f'검증 중 오류 발생: {str(e)}'],
            'warnings': []
        }


def extract_spatial_context_for_ai(gdf: gpd.GeoDataFrame, layer_type: str = 'general') -> str:
    """
    GeoDataFrame에서 AI가 이해할 수 있는 텍스트 컨텍스트를 추출합니다.
    
    Args:
        gdf: GeoDataFrame
        layer_type: 레이어 타입 ('administrative', 'land_price', 'ownership' 등)
    
    Returns:
        AI 분석에 사용할 수 있는 텍스트 요약
    """
    try:
        import numpy as np
        
        # 기본 정보
        total_features = len(gdf)
        
        # 컬럼 정보
        non_geom_columns = [col for col in gdf.columns if col.lower() != 'geometry']
        
        # 공간 범위
        bounds = gdf.total_bounds
        spatial_range = f"""
- 최서단(경도): {bounds[0]:.6f}
- 최남단(위도): {bounds[1]:.6f}
- 최동단(경도): {bounds[2]:.6f}
- 최북단(위도): {bounds[3]:.6f}
"""
        
        # 레이어 타입별 특화 정보 추출
        context_parts = []
        
        if layer_type in ['administrative', '행정구역', '시군구']:
            # 행정구역 특화: 명칭, 코드, 면적 등
            context_parts.append("**행정구역 경계 데이터:**")
            if 'EMD_NM' in gdf.columns:  # 읍면동명
                unique_areas = gdf['EMD_NM'].dropna().unique()[:10]
                context_parts.append(f"포함된 읍면동 예시: {', '.join(map(str, unique_areas))}")
            if 'SIG_CD' in gdf.columns:  # 시군구 코드
                context_parts.append(f"시군구 코드: {gdf['SIG_CD'].iloc[0] if len(gdf) > 0 else 'N/A'}")
                
        elif layer_type in ['land_price', '개별공시지가', '공시지가']:
            # 공시지가 특화: 지가 범위, 면적 등
            context_parts.append("**개별공시지가 데이터:**")
            
            # 지가 컬럼 찾기 (일반적인 컬럼명)
            price_columns = [col for col in gdf.columns if any(keyword in col.upper() for keyword in ['공시', 'PRICE', '가격', '시가'])]
            if price_columns:
                price_col = price_columns[0]
                prices = gdf[price_col].dropna()
                if len(prices) > 0:
                    context_parts.append(f"공시지가 범위: {prices.min():,.0f}원/㎡ ~ {prices.max():,.0f}원/㎡")
                    context_parts.append(f"평균 공시지가: {prices.mean():,.0f}원/㎡")
            
            # 면적 정보
            area_columns = [col for col in gdf.columns if any(keyword in col.upper() for keyword in ['AREA', '면적'])]
            if area_columns:
                area_col = area_columns[0]
                areas = gdf[area_col].dropna()
                if len(areas) > 0:
                    context_parts.append(f"대지 면적 범위: {areas.min():,.0f}㎡ ~ {areas.max():,.0f}㎡")
            
        elif layer_type in ['ownership', '토지소유', '소유']:
            # 토지소유 특화: 소유자 정보
            context_parts.append("**토지소유정보 데이터:**")
            
            # 소유자 컬럼 찾기
            owner_columns = [col for col in gdf.columns if any(keyword in col.upper() for keyword in ['OWNER', '소유', '소재'])]
            if owner_columns:
                owner_col = owner_columns[0]
                unique_owners = gdf[owner_col].dropna().unique()[:5]
                if len(unique_owners) > 0:
                    context_parts.append(f"주요 소유자 예시: {', '.join(map(str, unique_owners))}")
        
        # 일반 속성 정보 (모든 레이어 공통)
        if len(non_geom_columns) > 0:
            context_parts.append(f"**주요 속성 컬럼:** {', '.join(non_geom_columns)}")
            
            # 샘플 데이터 (최대 5개 필드, 상위 3개 행)
            sample_size = min(3, len(gdf))
            if sample_size > 0:
                context_parts.append("**샘플 데이터 (상위 3개):**")
                sample_df = gdf[non_geom_columns[:5]].head(sample_size)
                for idx, row in sample_df.iterrows():
                    row_data = []
                    for col in sample_df.columns:
                        val = row[col]
                        if pd.isna(val):
                            val = "N/A"
                        else:
                            val = str(val)[:50]  # 너무 긴 값은 자름
                        row_data.append(f"{col}={val}")
                    context_parts.append(f"  - 행 {idx}: {', '.join(row_data)}")
        
        # 통계 정보
        stats_info = f"""
**데이터 통계:**
- 총 피처 수: {total_features:,}개
{spatial_range}
"""
        context_parts.insert(0, stats_info.strip())
        
        # 최종 텍스트 조합
        context_text = "\n".join(context_parts)
        
        return context_text
        
    except Exception as e:
        return f"공간 데이터 요약 생성 중 오류 발생: {str(e)}"


# 주요 레이어 타입 매핑
LAYER_TYPE_MAPPING = {
    '행정구역': 'administrative',
    '읍면동': 'administrative',
    '법정동': 'administrative',
    '센서스': 'census',
    '시군구': 'boundary',
    '토지소유': 'ownership',
    '개별공시지가': 'land_price',
    '국토계획': 'national_planning',
    '공간시설': 'spatial_facility',
    '문화재': 'cultural_heritage',
    '도로명주소': 'address',
    '건물': 'building'
}


def filter_facilities_within_radius(center_lat: float, center_lon: float, 
                                   radius_km: float, facilities_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    중심점으로부터 반경 내에 있는 시설 필터링
    
    Args:
        center_lat: 중심점 위도
        center_lon: 중심점 경도
        radius_km: 반경 (km)
        facilities_gdf: 시설 GeoDataFrame
    
    Returns:
        필터링된 GeoDataFrame
    """
    try:
        # 중심점 생성
        from shapely.geometry import Point
        center_point = Point(center_lon, center_lat)
        center_gdf = gpd.GeoDataFrame([1], geometry=[center_point], crs='EPSG:4326')
        
        # 메트릭 좌표계로 변환 (거리 계산을 위해)
        if facilities_gdf.crs != 'EPSG:3857':
            facilities_proj = facilities_gdf.to_crs('EPSG:3857')
            center_proj = center_gdf.to_crs('EPSG:3857')
        else:
            facilities_proj = facilities_gdf
            center_proj = center_gdf
        
        # 반경을 미터로 변환
        radius_m = radius_km * 1000
        
        # 중심점에서 반경 내의 시설 필터링
        center_geom = center_proj.geometry.iloc[0]
        facilities_proj['distance'] = facilities_proj.geometry.distance(center_geom)
        filtered = facilities_proj[facilities_proj['distance'] <= radius_m].copy()
        
        # 원래 좌표계로 변환
        if filtered.crs != 'EPSG:4326':
            filtered = filtered.to_crs('EPSG:4326')
        
        return filtered
        
    except Exception as e:
        print(f"반경 내 시설 필터링 중 오류: {str(e)}")
        return gpd.GeoDataFrame()


def create_candidate_map_with_facilities(candidate_sites: List[Dict[str, Any]], 
                                       facilities_gdf: Optional[gpd.GeoDataFrame] = None,
                                       radius_km: float = 5.0):
    """
    후보지와 반경 내 시설을 표시하는 Folium 지도 생성
    
    Args:
        candidate_sites: 후보지 리스트 [{'name': '후보지 1', 'lat': 37.5, 'lon': 129.0, 'score': 85}]
        facilities_gdf: 시설 GeoDataFrame (선택사항)
        radius_km: 반경 (km, 기본값 5km)
    
    Returns:
        Folium Map 객체
    """
    try:
        import folium
        
        if not candidate_sites:
            return None
        
        # 중심점 계산
        center_lat = sum(site['lat'] for site in candidate_sites) / len(candidate_sites)
        center_lon = sum(site['lon'] for site in candidate_sites) / len(candidate_sites)
        
        # Folium 지도 생성
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # 후보지 마커 추가
        for site in candidate_sites:
            name = site.get('name', '후보지')
            lat = site.get('lat')
            lon = site.get('lon')
            score = site.get('score', 0)
            
            # 점수에 따른 색상
            if score >= 80:
                color = 'green'
                icon = 'star'
            elif score >= 60:
                color = 'blue'
                icon = 'info-sign'
            else:
                color = 'orange'
                icon = 'flag'
            
            # 마커 추가
            popup_text = f"<b>{name}</b><br>"
            popup_text += f"위도: {lat:.6f}<br>"
            popup_text += f"경도: {lon:.6f}<br>"
            if score > 0:
                popup_text += f"종합 점수: {score}점"
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color=color, icon=icon, prefix='fa')
            ).add_to(m)
            
            # 반경 5km 원 추가
            folium.Circle(
                location=[lat, lon],
                radius=radius_km * 1000,  # 미터로 변환
                popup=f"{name} 반경 {radius_km}km",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.1,
                weight=2
            ).add_to(m)
        
        # 시설 표시 (facilities_gdf가 있는 경우)
        if facilities_gdf is not None and not facilities_gdf.empty:
            facilities_layer = folium.FeatureGroup(name='반경 5km 내 시설')
            
            for site in candidate_sites:
                lat = site.get('lat')
                lon = site.get('lon')
                
                # 반경 내 시설 필터링
                nearby_facilities = filter_facilities_within_radius(
                    lat, lon, radius_km, facilities_gdf
                )
                
                # 시설 마커 추가
                for idx, facility in nearby_facilities.head(50).iterrows():  # 최대 50개
                    facility_name = facility.get('name', '시설') if 'name' in facility else '시설'
                    facility_info = "<br>".join([
                        f"<b>{col}:</b> {facility[col]}" 
                        for col in facility.index 
                        if col != 'geometry' and pd.notna(facility[col])
                    ][:5])
                    
                    folium.Marker(
                        location=[facility.geometry.y, facility.geometry.x],
                        popup=folium.Popup(facility_info, max_width=300),
                        icon=folium.Icon(color='gray', icon='building', prefix='fa')
                    ).add_to(facilities_layer)
            
            facilities_layer.add_to(m)
        
        # 레이어 컨트롤 추가
        folium.LayerControl().add_to(m)
        
        # 후보지 범위에 맞춰 줌 조정
        if len(candidate_sites) > 0:
            lats = [s['lat'] for s in candidate_sites]
            lons = [s['lon'] for s in candidate_sites]
            m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
        
        return m
        
    except Exception as e:
        print(f"후보지 지도 생성 중 오류: {str(e)}")
        return None
import geopandas as gpd
import pandas as pd
import streamlit as st
from typing import Dict, Any, Optional
import os
import zipfile
import io
import pyproj


class GeoDataLoader:
    """도시공간데이터 Shapefile을 로드하고 처리하는 클래스"""
    
    def __init__(self):
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


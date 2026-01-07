import pandas as pd
import geopandas as gpd
import requests
import json
import os
from typing import Dict, List, Tuple, Any
from shapely.geometry import Point
from shapely.geometry import CAP_STYLE
from pyproj import Transformer
import time
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

class UrbanDataCollector:
    """좌표 기반 도시 데이터 자동 수집기"""
    
    def __init__(self):
        # 좌표계 설정
        self.WGS84 = "EPSG:4326"
        self.KOREA_TM = "EPSG:5179"  # V-World/국토부 계열
        self.tf_to_tm = Transformer.from_crs(self.WGS84, self.KOREA_TM, always_xy=True)
        self.tf_to_wgs = Transformer.from_crs(self.KOREA_TM, self.WGS84, always_xy=True)
        
        # API 키 설정
        self.vworld_api_key = os.getenv("VWORLD_API_KEY")
        self.kosis_api_key = os.getenv("KOSIS_API_KEY")
        self.public_data_api_key = os.getenv("PUBLIC_DATA_API_KEY")
    
    def collect_site_data(self, lat: float, lon: float, radius_m: int = 1000, site_id: str = "S001") -> Dict[str, Any]:
        """특정 좌표 주변의 모든 데이터를 수집합니다."""
        
        print(f"📍 사이트 {site_id} 데이터 수집 시작: ({lat}, {lon}), 반경 {radius_m}m")
        
        # 1. 역지오코딩으로 행정코드 획득
        adm_info = self._vworld_reverse_geocode(lat, lon)
        
        # 2. 버퍼/바운딩박스 계산
        bbox = self._make_buffer_bbox(lat, lon, radius_m)
        
        # 3. 각 소스별 데이터 수집
        collected_data = {
            "site_info": {
                "site_id": site_id,
                "lat": lat,
                "lon": lon,
                "radius_m": radius_m,
                "adm_info": adm_info,
                "bbox": bbox
            }
        }
        
        # OSM 데이터 수집
        try:
            collected_data["osm_poi"] = self._collect_osm_poi(lat, lon, radius_m)
            print(f"✅ OSM POI 수집 완료: {len(collected_data['osm_poi'])}개")
        except Exception as e:
            print(f"❌ OSM POI 수집 실패: {e}")
            collected_data["osm_poi"] = pd.DataFrame()
        
        # V-World 데이터 수집
        try:
            collected_data["vworld_zoning"] = self._collect_vworld_zoning(bbox)
            print(f"✅ V-World 용도지역 수집 완료: {len(collected_data['vworld_zoning'])}개")
        except Exception as e:
            print(f"❌ V-World 용도지역 수집 실패: {e}")
            collected_data["vworld_zoning"] = gpd.GeoDataFrame()
        
        # KOSIS 통계 수집
        if adm_info.get("adm_code"):
            try:
                collected_data["kosis_stats"] = self._collect_kosis_stats(adm_info["adm_code"])
                print(f"✅ KOSIS 통계 수집 완료")
            except Exception as e:
                print(f"❌ KOSIS 통계 수집 실패: {e}")
                collected_data["kosis_stats"] = pd.DataFrame()
        
        # 공공데이터 수집
        try:
            collected_data["public_facilities"] = self._collect_public_facilities(lat, lon, radius_m)
            print(f"✅ 공공시설 데이터 수집 완료: {len(collected_data['public_facilities'])}개")
        except Exception as e:
            print(f"❌ 공공시설 데이터 수집 실패: {e}")
            collected_data["public_facilities"] = pd.DataFrame()
        
        return collected_data
    
    def _vworld_reverse_geocode(self, lat: float, lon: float) -> Dict[str, str]:
        """V-World 역지오코딩으로 행정코드 획득"""
        if not self.vworld_api_key:
            return {"error": "V-World API 키가 설정되지 않았습니다", "note": "API 키 없이도 OSM 데이터는 수집 가능합니다"}
        
        # V-World 역지오코딩 API (좌표 → 주소)
        url = "https://api.vworld.kr/req/address"
        params = {
            "service": "address",
            "request": "getAddress",
            "type": "both",
            "key": self.vworld_api_key,
            "point": f"{lon},{lat}",  # 좌표
            "format": "json"
        }
        
        try:
            print(f"V-World API 호출: {url}")
            print(f"파라미터: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            print(f"응답 상태 코드: {response.status_code}")
            print(f"응답 내용: {response.text[:500]}...")
            
            data = response.json()
            
            if data.get("response", {}).get("status") == "OK":
                result = data["response"]["result"][0]
                return {
                    "adm_si": result.get("structure", {}).get("level1", ""),
                    "adm_gu": result.get("structure", {}).get("level2", ""),
                    "adm_dong": result.get("structure", {}).get("level3", ""),
                    "adm_code": result.get("structure", {}).get("level4", ""),
                    "full_address": result.get("text", "")
                }
            else:
                error_msg = data.get("response", {}).get("error", {}).get("text", "알 수 없는 오류")
                return {
                    "error": f"역지오코딩 실패: {error_msg}", 
                    "note": "API 키 또는 좌표를 확인해주세요",
                    "debug_info": {
                        "status_code": response.status_code,
                        "response": data
                    }
                }
        except Exception as e:
            return {"error": f"역지오코딩 오류: {e}", "note": "네트워크 연결을 확인해주세요"}
    
    def _make_buffer_bbox(self, lat: float, lon: float, radius_m: int) -> Tuple[float, float, float, float]:
        """반경 기반 바운딩박스 계산"""
        x_tm, y_tm = self.tf_to_tm.transform(lon, lat)
        poly_tm = Point(x_tm, y_tm).buffer(radius_m, cap_style=CAP_STYLE.round)
        
        # bbox in TM
        minx, miny, maxx, maxy = poly_tm.bounds
        
        # bbox to WGS84
        minlon, minlat = self.tf_to_wgs.transform(minx, miny)
        maxlon, maxlat = self.tf_to_wgs.transform(maxx, maxy)
        
        return (minlon, minlat, maxlon, maxlat)
    
    def _collect_osm_poi(self, lat: float, lon: float, radius_m: int) -> pd.DataFrame:
        """OSM Overpass API로 POI 수집"""
        poi_types = [
            ("amenity", "hospital"),
            ("amenity", "school"),
            ("amenity", "university"),
            ("public_transport", "station"),
            ("shop", "supermarket"),
            ("leisure", "park")
        ]
        
        all_pois = []
        
        for tag_key, tag_val in poi_types:
            query = f"""
            [out:json][timeout:25];
            (
              node["{tag_key}"="{tag_val}"](around:{radius_m},{lat},{lon});
              way["{tag_key}"="{tag_val}"](around:{radius_m},{lat},{lon});
              relation["{tag_key}"="{tag_val}"](around:{radius_m},{lat},{lon});
            );
            out center;
            """
            
            try:
                response = requests.post(
                    "https://overpass-api.de/api/interpreter",
                    data=query,
                    timeout=30
                )
                data = response.json()
                
                for element in data.get("elements", []):
                    if element.get("type") == "node":
                        poi_lat, poi_lon = element["lat"], element["lon"]
                    else:
                        center = element.get("center", {})
                        poi_lat, poi_lon = center.get("lat"), center.get("lon")
                    
                    if poi_lat and poi_lon:
                        all_pois.append({
                            "poi_type": f"{tag_key}:{tag_val}",
                            "name": element.get("tags", {}).get("name", ""),
                            "lat": poi_lat,
                            "lon": poi_lon,
                            "distance_m": self._calculate_distance(lat, lon, poi_lat, poi_lon)
                        })
                
                time.sleep(1)  # API 제한 고려
                
            except Exception as e:
                print(f"OSM {tag_key}:{tag_val} 수집 오류: {e}")
                continue
        
        return pd.DataFrame(all_pois)
    
    def _collect_vworld_zoning(self, bbox: Tuple[float, float, float, float]) -> gpd.GeoDataFrame:
        """V-World WFS로 용도지역 데이터 수집"""
        if not self.vworld_api_key:
            print("V-World API 키가 없어서 용도지역 데이터를 수집할 수 없습니다.")
            return gpd.GeoDataFrame()
        
        minlon, minlat, maxlon, maxlat = bbox
        
        # 먼저 사용 가능한 레이어 목록을 확인
        available_layers = self._get_vworld_available_layers()
        if not available_layers:
            print("사용 가능한 V-World 레이어를 찾을 수 없습니다.")
            return gpd.GeoDataFrame()
        
        print(f"사용 가능한 레이어: {available_layers}")
        
        # 용도지역 관련 레이어만 필터링 (더 많은 키워드 추가)
        zoning_keywords = [
            'uddi', 'udpg', 'upisu',  # 기본 용도지역 키워드
            'zoning', 'landuse', 'land_use',  # 영어 키워드
            'yongdo', 'yongdodae', 'yongdogu',  # 한글 키워드
            'lt_c', 'lt_',  # V-World 레이어 접두사
            'plan', 'planning', 'urban'  # 도시계획 관련
        ]
        
        zoning_layers = [layer for layer in available_layers if any(keyword in layer.lower() for keyword in zoning_keywords)]
        
        if not zoning_layers:
            print("용도지역 관련 레이어를 찾을 수 없습니다.")
            return gpd.GeoDataFrame()
        
        print(f"용도지역 관련 레이어: {zoning_layers}")
        layers = zoning_layers  # 모든 용도지역 관련 레이어 시도
        
        all_zoning = []
        
        for layer in layers:
            print(f"V-World WFS API 호출: {layer}")
            
            # V-World WFS API 파라미터 (올바른 형식)
            params = {
                "service": "WFS",
                "version": "1.1.0",
                "request": "GetFeature",
                "typeName": layer,
                "bbox": f"{minlon},{minlat},{maxlon},{maxlat}",
                "srsName": "EPSG:4326",
                "outputFormat": "application/json",
                "key": self.vworld_api_key
            }
            
            print(f"레이어 {layer}에 대해 JSON 형식으로 요청합니다...")
            
            try:
                print(f"WFS 파라미터: {params}")
                response = requests.get("https://api.vworld.kr/req/wfs", params=params, timeout=30)
                print(f"WFS 응답 상태: {response.status_code}")
                
                if response.status_code == 200:
                    # 응답 내용 확인
                    response_text = response.text
                    print(f"WFS 응답 내용 (처음 500자): {response_text[:500]}...")
                    
                    # JSON 파싱 시도
                    try:
                        data = response.json()
                        print(f"JSON 파싱 성공: {str(data)[:200]}...")
                        
                        if "features" in data and data["features"]:
                            gdf = gpd.GeoDataFrame.from_features(data["features"], crs=self.WGS84)
                            gdf["layer_name"] = layer  # 레이어명 추가
                            all_zoning.append(gdf)
                            print(f"✅ {layer} 레이어에서 {len(gdf)}개 피처 수집")
                            
                            # 레이어별 상세 정보 출력
                            if len(gdf) > 0:
                                print(f"   - 컬럼: {list(gdf.columns)}")
                                if 'properties' in gdf.columns:
                                    print(f"   - 속성 샘플: {gdf['properties'].iloc[0] if len(gdf) > 0 else 'None'}")
                        else:
                            print(f"⚠️ {layer} 레이어에 데이터가 없습니다.")
                            
                    except ValueError as json_error:
                        print(f"❌ JSON 파싱 오류: {json_error}")
                        print(f"응답이 JSON 형식이 아닙니다. 응답 타입: {response.headers.get('content-type', 'unknown')}")
                        
                        # XML 응답인 경우 처리
                        if 'xml' in response.headers.get('content-type', '').lower():
                            print("XML 응답을 받았습니다. GeoJSON으로 변환을 시도합니다.")
                            # XML을 GeoJSON으로 변환하는 로직 추가 가능
                        else:
                            print("알 수 없는 응답 형식입니다.")
                            
                else:
                    print(f"❌ WFS API 오류: {response.status_code}")
                    print(f"응답 내용: {response.text[:200]}...")
                
                time.sleep(1)  # API 제한 고려
                
            except Exception as e:
                print(f"❌ V-World {layer} 수집 오류: {e}")
                continue
        
        if all_zoning:
            result = pd.concat(all_zoning, ignore_index=True)
            print(f"✅ 총 {len(result)}개 용도지역 데이터 수집 완료")
            return result
        else:
            print("⚠️ 용도지역 데이터를 수집할 수 없습니다.")
            return gpd.GeoDataFrame()
    
    def _get_vworld_available_layers(self) -> List[str]:
        """V-World에서 사용 가능한 레이어 목록을 가져옵니다."""
        try:
            # WFS GetCapabilities 요청
            params = {
                "service": "WFS",
                "version": "1.1.0",
                "request": "GetCapabilities",
                "key": self.vworld_api_key
            }
            
            response = requests.get("https://api.vworld.kr/req/wfs", params=params, timeout=30)
            
            if response.status_code == 200:
                # XML 응답에서 레이어명 추출
                import re
                layer_pattern = r'<Name>([^<]+)</Name>'
                layers = re.findall(layer_pattern, response.text)
                print(f"V-World에서 발견된 레이어 수: {len(layers)}")
                return layers
            else:
                print(f"GetCapabilities 요청 실패: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"레이어 목록 조회 오류: {e}")
            return []
    
    def _collect_kosis_stats(self, adm_code: str) -> pd.DataFrame:
        """KOSIS 행정구역별 통계 수집"""
        if not self.kosis_api_key or not adm_code:
            return pd.DataFrame()
        
        # 예시 통계 테이블 ID (실제로는 KOSIS에서 확인 필요)
        table_ids = ["DT_1B04005N"]  # 예시: 인구 및 가구 통계
        
        all_stats = []
        
        for table_id in table_ids:
            params = {
                "apiKey": self.kosis_api_key,
                "itmId": "T1+T2",
                "objL1": adm_code,
                "format": "json",
                "jsonVD": "Y",
                "tableId": table_id
            }
            
            try:
                response = requests.get(
                    "https://kosis.kr/openapi/Param/statisticsParameterData.do",
                    params=params,
                    timeout=30
                )
                data = response.json()
                
                # 응답 파싱 (실제 구조에 따라 수정 필요)
                if "data" in data:
                    stats_df = pd.DataFrame(data["data"])
                    all_stats.append(stats_df)
                
                time.sleep(1)  # API 제한 고려
                
            except Exception as e:
                print(f"KOSIS {table_id} 수집 오류: {e}")
                continue
        
        if all_stats:
            return pd.concat(all_stats, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def _collect_public_facilities(self, lat: float, lon: float, radius_m: int) -> pd.DataFrame:
        """공공데이터포털 시설 데이터 수집"""
        # 예시: 전국 병원 데이터 (실제 API는 데이터셋별로 다름)
        facilities = []
        
        # 여기에 실제 공공데이터 API 호출 로직 구현
        # 예시 데이터
        facilities.append({
            "facility_type": "hospital",
            "name": "예시 병원",
            "lat": lat + 0.001,
            "lon": lon + 0.001,
            "distance_m": 100
        })
        
        return pd.DataFrame(facilities)
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """두 좌표 간 거리 계산 (미터)"""
        from math import radians, cos, sin, asin, sqrt
        
        # Haversine 공식
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371000  # 지구 반지름 (미터)
        return c * r
    
    def save_collected_data(self, collected_data: Dict[str, Any], output_dir: str = "output") -> Dict[str, str]:
        """수집된 데이터를 파일로 저장"""
        os.makedirs(output_dir, exist_ok=True)
        
        site_id = collected_data["site_info"]["site_id"]
        saved_files = {}
        
        # 각 데이터별로 저장
        for data_type, data in collected_data.items():
            if data_type == "site_info":
                # 사이트 정보를 JSON으로 저장
                with open(f"{output_dir}/{site_id}_site_info.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                saved_files["site_info"] = f"{output_dir}/{site_id}_site_info.json"
            
            elif isinstance(data, pd.DataFrame) and not data.empty:
                # CSV로 저장
                csv_path = f"{output_dir}/{site_id}_{data_type}.csv"
                data.to_csv(csv_path, index=False, encoding="utf-8-sig")
                saved_files[data_type] = csv_path
            
            elif isinstance(data, gpd.GeoDataFrame) and not data.empty:
                # GeoJSON으로 저장
                geojson_path = f"{output_dir}/{site_id}_{data_type}.geojson"
                data.to_file(geojson_path, driver="GeoJSON", encoding="utf-8")
                saved_files[data_type] = geojson_path
        
        # 통합 XLSX 파일 생성
        xlsx_path = f"{output_dir}/{site_id}_bundle.xlsx"
        with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
            for data_type, data in collected_data.items():
                if isinstance(data, (pd.DataFrame, gpd.GeoDataFrame)) and not data.empty:
                    # GeoDataFrame은 geometry 컬럼 제외하고 저장
                    if isinstance(data, gpd.GeoDataFrame):
                        df_to_save = data.drop(columns=['geometry'], errors='ignore')
                    else:
                        df_to_save = data
                    
                    sheet_name = data_type[:31]  # Excel 시트명 길이 제한
                    df_to_save.to_excel(writer, sheet_name=sheet_name, index=False)
        
        saved_files["bundle"] = xlsx_path
        
        return saved_files
import pandas as pd
import fitz  # PyMuPDF
import os
from typing import Dict, Any, Union
import json

class UniversalFileAnalyzer:
    """다양한 파일 형식을 지원하는 범용 파일 분석기"""
    
    def __init__(self):
        self.supported_formats = {
            "pdf": self._analyze_pdf,
            "xlsx": self._analyze_excel,
            "xls": self._analyze_excel,
            "csv": self._analyze_csv,
            "txt": self._analyze_text,
            "json": self._analyze_json
        }
    
    def analyze_file(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """파일을 분석하고 텍스트를 추출합니다."""
        if file_type.lower() not in self.supported_formats:
            return {
                "success": False,
                "error": f"지원하지 않는 파일 형식입니다: {file_type}",
                "supported_formats": list(self.supported_formats.keys())
            }
        
        try:
            return self.supported_formats[file_type.lower()](file_path)
        except Exception as e:
            return {
                "success": False,
                "error": f"파일 분석 중 오류 발생: {str(e)}"
            }
    
    def _analyze_pdf(self, file_path: str) -> Dict[str, Any]:
        """PDF 파일 분석"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {file_path}")
            
            doc = fitz.open(file_path)
            text = ""
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"
            
            doc.close()
            
            if not text.strip():
                raise ValueError("PDF에서 텍스트를 추출할 수 없습니다.")
            
            return {
                "success": True,
                "file_type": "pdf",
                "text": text.strip(),
                "page_count": len(doc),
                "word_count": len(text.split()),
                "char_count": len(text),
                "preview": text[:500] + "..." if len(text) > 500 else text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"PDF 분석 오류: {str(e)}"
            }
    
    def _analyze_excel(self, file_path: str) -> Dict[str, Any]:
        """Excel 파일 분석"""
        try:
            # 모든 시트 읽기
            excel_file = pd.ExcelFile(file_path)
            sheets_data = {}
            all_text = ""
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # 데이터프레임을 텍스트로 변환
                sheet_text = df.to_string(index=False)
                sheets_data[sheet_name] = {
                    "shape": df.shape,
                    "columns": df.columns.tolist(),
                    "data_types": df.dtypes.to_dict(),
                    "text": sheet_text
                }
                all_text += f"\n=== {sheet_name} 시트 ===\n{sheet_text}\n"
            
            return {
                "success": True,
                "file_type": "excel",
                "text": all_text.strip(),
                "sheets": sheets_data,
                "sheet_count": len(excel_file.sheet_names),
                "sheet_names": excel_file.sheet_names,
                "word_count": len(all_text.split()),
                "char_count": len(all_text),
                "preview": all_text[:500] + "..." if len(all_text) > 500 else all_text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Excel 분석 오류: {str(e)}"
            }
    
    def _analyze_csv(self, file_path: str) -> Dict[str, Any]:
        """CSV 파일 분석"""
        try:
            # CSV 파일 읽기
            df = pd.read_csv(file_path, encoding="utf-8")
            
            # 데이터프레임을 텍스트로 변환
            csv_text = df.to_string(index=False)
            
            return {
                "success": True,
                "file_type": "csv",
                "text": csv_text,
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "data_types": df.dtypes.to_dict(),
                "word_count": len(csv_text.split()),
                "char_count": len(csv_text),
                "preview": csv_text[:500] + "..." if len(csv_text) > 500 else csv_text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"CSV 분석 오류: {str(e)}"
            }
    
    def _analyze_text(self, file_path: str) -> Dict[str, Any]:
        """텍스트 파일 분석"""
        try:
            # 다양한 인코딩으로 시도
            encodings = ["utf-8", "cp949", "euc-kr", "latin-1"]
            text = ""
            
            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        text = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if not text:
                raise ValueError("텍스트 파일을 읽을 수 없습니다.")
            
            return {
                "success": True,
                "file_type": "text",
                "text": text.strip(),
                "word_count": len(text.split()),
                "char_count": len(text),
                "line_count": len(text.split("\n")),
                "preview": text[:500] + "..." if len(text) > 500 else text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"텍스트 파일 분석 오류: {str(e)}"
            }
    
    def _analyze_json(self, file_path: str) -> Dict[str, Any]:
        """JSON 파일 분석"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # JSON을 텍스트로 변환
            json_text = json.dumps(data, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "file_type": "json",
                "text": json_text,
                "data": data,
                "word_count": len(json_text.split()),
                "char_count": len(json_text),
                "preview": json_text[:500] + "..." if len(json_text) > 500 else json_text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"JSON 파일 분석 오류: {str(e)}"
            }
    
    def get_supported_formats(self) -> list:
        """지원하는 파일 형식 목록 반환"""
        return list(self.supported_formats.keys())
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """파일 정보 반환"""
        try:
            stat = os.stat(file_path)
            return {
                "file_name": os.path.basename(file_path),
                "file_size": stat.st_size,
                "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
                "extension": os.path.splitext(file_path)[1].lower().lstrip("."),
                "is_supported": os.path.splitext(file_path)[1].lower().lstrip(".") in self.supported_formats
            }
        except Exception as e:
            return {
                "error": f"파일 정보 조회 오류: {str(e)}"
            }

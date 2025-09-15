import fitz  # PyMuPDF
import os
from typing import Dict, Any

def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF에서 텍스트를 추출합니다."""
    try:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        text = ""
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"
        
        doc.close()
        
        if not text.strip():
            raise ValueError("PDF에서 텍스트를 추출할 수 없습니다. 이미지 기반 PDF일 수 있습니다.")
        
        return text.strip()
        
    except Exception as e:
        print(f"PDF 텍스트 추출 오류: {e}")
        return ""

def analyze_pdf_content(text: str) -> Dict[str, Any]:
    """PDF 내용을 기본적으로 분석합니다."""
    if not text:
        return {"error": "텍스트를 추출할 수 없습니다."}
    
    # 기본 통계
    word_count = len(text.split())
    char_count = len(text)
    line_count = len(text.split('\n'))
    
    # 키워드 추출 (간단한 방식)
    keywords = []
    if "건축" in text:
        keywords.append("건축")
    if "설계" in text:
        keywords.append("설계")
    if "면적" in text:
        keywords.append("면적")
    if "법규" in text:
        keywords.append("법규")
    
    return {
        "word_count": word_count,
        "char_count": char_count,
        "line_count": line_count,
        "keywords": keywords,
        "text_preview": text[:500] + "..." if len(text) > 500 else text
    }

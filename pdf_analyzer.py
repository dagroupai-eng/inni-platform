import fitz  # PyMuPDF
import os
import time
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

# Gemini API 키 가져오기 (embedding_helper.py와 동일한 방식)
def _get_gemini_api_key() -> Optional[str]:
    """Gemini API 키를 가져옵니다."""
    try:
        import streamlit as st
        # 1. 먼저 세션 상태에서 확인 (사용자가 웹에서 입력한 키)
        if 'user_api_key_GEMINI_API_KEY' in st.session_state and st.session_state['user_api_key_GEMINI_API_KEY']:
            return st.session_state['user_api_key_GEMINI_API_KEY']
        # 2. Streamlit secrets에서 확인 (secrets 파일이 없을 수 있으므로 안전하게 처리)
        # 3. 환경변수에서 확인
        try:
            api_key = st.secrets.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')
        except (FileNotFoundError, AttributeError, KeyError):
            api_key = os.environ.get('GEMINI_API_KEY')
    except Exception:
        api_key = os.environ.get('GEMINI_API_KEY')
    
    return api_key

def extract_text_with_gemini_pdf(
    pdf_path: Union[str, Path, bytes],
    prompt: str = "이 PDF 문서의 모든 텍스트 내용을 추출해주세요.",
    model: str = "gemini-2.5-flash",
    use_files_api: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Gemini API를 사용하여 PDF를 네이티브로 처리합니다.
    텍스트뿐만 아니라 이미지, 다이어그램, 차트, 테이블까지 이해합니다.
    
    Args:
        pdf_path: PDF 파일 경로 또는 PDF 바이트 데이터
        prompt: PDF 분석을 위한 프롬프트
        model: 사용할 Gemini 모델
        use_files_api: Files API 사용 여부 (None이면 파일 크기에 따라 자동 선택)
    
    Returns:
        분석 결과 딕셔너리
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY가 설정되지 않았습니다."
        }
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        # PDF 데이터 준비
        if isinstance(pdf_path, bytes):
            pdf_bytes = pdf_path
            file_size = len(pdf_bytes)
        else:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                return {
                    "success": False,
                    "error": f"PDF 파일을 찾을 수 없습니다: {pdf_path}"
                }
            file_size = pdf_path.stat().st_size
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
        
        # 파일 크기에 따른 처리 방식 선택 (10MB 기준)
        FILE_SIZE_THRESHOLD = 10 * 1024 * 1024  # 10MB
        
        if use_files_api is None:
            use_files_api = file_size >= FILE_SIZE_THRESHOLD
        
        if use_files_api:
            # Files API 사용 (대용량 파일)
            return _process_pdf_with_files_api(
                client=client,
                pdf_bytes=pdf_bytes,
                pdf_path=pdf_path if isinstance(pdf_path, (str, Path)) else None,
                prompt=prompt,
                model=model
            )
        else:
            # 인라인 처리 (작은 파일)
            return _process_pdf_inline(
                client=client,
                pdf_bytes=pdf_bytes,
                prompt=prompt,
                model=model
            )
    
    except ImportError:
        return {
            "success": False,
            "error": "google-genai 패키지가 설치되지 않았습니다. pip install google-genai를 실행하세요."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Gemini PDF 처리 오류: {str(e)}"
        }


def _process_pdf_inline(
    client,
    pdf_bytes: bytes,
    prompt: str,
    model: str
) -> Dict[str, Any]:
    """인라인 방식으로 PDF 처리"""
    try:
        from google.genai import types
        
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(
                    data=pdf_bytes,
                    mime_type='application/pdf',
                ),
                prompt
            ]
        )
        
        return {
            "success": True,
            "text": response.text,
            "method": "inline",
            "model": model
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"인라인 PDF 처리 오류: {str(e)}"
        }


def _process_pdf_with_files_api(
    client,
    pdf_bytes: bytes,
    pdf_path: Optional[Union[str, Path]],
    prompt: str,
    model: str
) -> Dict[str, Any]:
    """Files API를 사용하여 PDF 처리"""
    try:
        import io
        from google.genai import types
        
        # 파일 업로드
        if pdf_path:
            # 파일 경로가 있으면 경로로 업로드
            uploaded_file = client.files.upload(
                file=str(pdf_path),
                config=dict(mime_type='application/pdf')
            )
        else:
            # 바이트 데이터는 BytesIO로 업로드
            pdf_io = io.BytesIO(pdf_bytes)
            uploaded_file = client.files.upload(
                file=pdf_io,
                config=dict(mime_type='application/pdf')
            )
        
        # 파일 처리 대기
        max_wait_time = 300  # 최대 5분 대기
        start_time = time.time()
        
        while uploaded_file.state == 'PROCESSING':
            if time.time() - start_time > max_wait_time:
                return {
                    "success": False,
                    "error": "파일 처리 시간이 초과되었습니다."
                }
            
            uploaded_file = client.files.get(name=uploaded_file.name)
            print(f"파일 처리 중... 상태: {uploaded_file.state}")
            time.sleep(2)
        
        if uploaded_file.state == 'FAILED':
            return {
                "success": False,
                "error": "파일 처리에 실패했습니다."
            }
        
        # 분석 요청
        response = client.models.generate_content(
            model=model,
            contents=[uploaded_file, prompt]
        )
        
        return {
            "success": True,
            "text": response.text,
            "method": "files_api",
            "model": model,
            "file_uri": uploaded_file.uri if hasattr(uploaded_file, 'uri') else None
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Files API PDF 처리 오류: {str(e)}"
        }


def process_multiple_pdfs_with_gemini(
    pdf_paths: List[Union[str, Path]],
    prompt: str = "이 PDF 문서들을 비교 분석해주세요.",
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    여러 PDF를 Gemini API로 동시에 처리합니다.
    
    Args:
        pdf_paths: PDF 파일 경로 목록
        prompt: 분석을 위한 프롬프트
        model: 사용할 Gemini 모델
    
    Returns:
        분석 결과 딕셔너리
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY가 설정되지 않았습니다."
        }
    
    try:
        from google import genai
        from google.genai import types
        import io
        
        client = genai.Client(api_key=api_key)
        
        uploaded_files = []
        contents = [prompt]
        
        # 모든 PDF 업로드
        for pdf_path in pdf_paths:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                continue
            
            uploaded_file = client.files.upload(
                file=str(pdf_path),
                config=dict(mime_type='application/pdf')
            )
            
            # 처리 대기
            while uploaded_file.state == 'PROCESSING':
                uploaded_file = client.files.get(name=uploaded_file.name)
                time.sleep(2)
            
            if uploaded_file.state == 'FAILED':
                continue
            
            uploaded_files.append(uploaded_file)
            contents.append(uploaded_file)
        
        if not uploaded_files:
            return {
                "success": False,
                "error": "업로드할 수 있는 PDF 파일이 없습니다."
            }
        
        # 분석 요청
        response = client.models.generate_content(
            model=model,
            contents=contents
        )
        
        return {
            "success": True,
            "text": response.text,
            "method": "files_api_multiple",
            "model": model,
            "file_count": len(uploaded_files)
        }
    
    except ImportError:
        return {
            "success": False,
            "error": "google-genai 패키지가 설치되지 않았습니다."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"다중 PDF 처리 오류: {str(e)}"
        }

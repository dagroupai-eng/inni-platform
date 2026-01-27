"""
V-World API 프록시 서버
Oracle Cloud 한국 리전에서 실행하여 V-World API 접근

실행 방법:
1. pip install flask requests flask-cors gunicorn
2. gunicorn -w 4 -b 0.0.0.0:8080 vworld_proxy:app

또는 개발용:
python vworld_proxy.py
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests
import logging

app = Flask(__name__)
CORS(app)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 허용된 V-World API 도메인
ALLOWED_DOMAINS = [
    'api.vworld.kr',
    'apis.vworld.kr',
    'map.vworld.kr'
]

# V-World 요청 헤더
VWORLD_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/xml, */*',
    'Accept-Language': 'ko-KR,ko;q=0.9',
    'Referer': 'https://map.vworld.kr/',
    'Origin': 'https://map.vworld.kr',
}


def is_allowed_url(url):
    """URL이 허용된 도메인인지 확인"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return any(
            parsed.hostname == domain or parsed.hostname.endswith('.' + domain)
            for domain in ALLOWED_DOMAINS
        )
    except:
        return False


@app.route('/')
@app.route('/health')
def health():
    """헬스 체크"""
    return jsonify({
        'status': 'ok',
        'service': 'V-World API Proxy (Oracle Cloud Korea)',
        'endpoints': {
            'GET /proxy?url=...': 'Proxy GET request to V-World API',
            'POST /proxy': 'Proxy request with JSON body { url, params, method }'
        }
    })


@app.route('/proxy', methods=['GET'])
def proxy_get():
    """GET 방식 프록시"""
    target_url = request.args.get('url')

    if not target_url:
        return jsonify({'error': 'Missing url parameter'}), 400

    if not is_allowed_url(target_url):
        return jsonify({'error': 'URL not allowed'}), 403

    try:
        logger.info(f"[PROXY GET] {target_url}")
        response = requests.get(target_url, headers=VWORLD_HEADERS, timeout=30)

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
    except Exception as e:
        logger.error(f"[PROXY ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/proxy', methods=['POST'])
def proxy_post():
    """POST 방식 프록시 (JSON body)"""
    try:
        data = request.get_json()
    except:
        return jsonify({'error': 'Invalid JSON body'}), 400

    target_url = data.get('url')
    params = data.get('params', {})
    method = data.get('method', 'GET').upper()

    if not target_url:
        return jsonify({'error': 'Missing url in body'}), 400

    if not is_allowed_url(target_url):
        return jsonify({'error': 'URL not allowed'}), 403

    try:
        # params가 있으면 URL에 추가
        if params:
            from urllib.parse import urlencode
            target_url = f"{target_url}?{urlencode(params)}"

        logger.info(f"[PROXY {method}] {target_url}")

        if method == 'POST':
            response = requests.post(target_url, headers=VWORLD_HEADERS, timeout=30)
        else:
            response = requests.get(target_url, headers=VWORLD_HEADERS, timeout=30)

        logger.info(f"[PROXY RESPONSE] Status: {response.status_code}")

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
    except Exception as e:
        logger.error(f"[PROXY ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/proxy', methods=['OPTIONS'])
def proxy_options():
    """CORS preflight"""
    return '', 204


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

/**
 * Cloudflare Worker - V-World API Proxy
 *
 * 이 Worker는 Cloudflare의 서울 데이터센터를 통해 V-World API 요청을 프록시합니다.
 * V-World API는 해외 IP를 차단하므로, 한국 IP가 필요합니다.
 *
 * 배포 방법:
 * 1. Cloudflare 계정 생성 (https://dash.cloudflare.com)
 * 2. Workers & Pages > Create application > Create Worker
 * 3. 이 코드를 붙여넣기
 * 4. Deploy 클릭
 * 5. Settings > Triggers에서 Custom Domain 설정 (선택사항)
 *
 * 사용법:
 * Worker URL: https://your-worker-name.your-subdomain.workers.dev
 * 요청: POST /proxy with JSON body { "url": "https://api.vworld.kr/...", "params": {...} }
 * 또는: GET /proxy?url=encoded_url
 */

// 허용된 V-World API 도메인
const ALLOWED_DOMAINS = [
  'api.vworld.kr',
  'apis.vworld.kr',
  'map.vworld.kr'
];

// CORS 헤더
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Max-Age': '86400',
};

/**
 * URL이 허용된 도메인인지 확인
 */
function isAllowedUrl(url) {
  try {
    const parsed = new URL(url);
    return ALLOWED_DOMAINS.some(domain => parsed.hostname === domain || parsed.hostname.endsWith('.' + domain));
  } catch {
    return false;
  }
}

/**
 * V-World API로 요청을 프록시
 */
async function proxyRequest(targetUrl, method = 'GET', body = null, request = null) {
  const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/xml, */*',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://map.vworld.kr/',
    'Origin': 'https://map.vworld.kr',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
  };

  const fetchOptions = {
    method: method,
    headers: headers,
  };

  if (body && method === 'POST') {
    fetchOptions.body = body;
    fetchOptions.headers['Content-Type'] = 'application/x-www-form-urlencoded';
  }

  // 디버깅용: 요청 정보 로깅
  const cfInfo = request?.cf || {};
  console.log(`[PROXY] URL: ${targetUrl}`);
  console.log(`[PROXY] Method: ${method}`);
  console.log(`[PROXY] CF Colo: ${cfInfo.colo || 'unknown'}`);
  console.log(`[PROXY] CF Country: ${cfInfo.country || 'unknown'}`);

  try {
    const response = await fetch(targetUrl, fetchOptions);

    // 응답 본문 읽기
    const responseBody = await response.text();

    console.log(`[PROXY] Response Status: ${response.status}`);
    console.log(`[PROXY] Response Body (first 200 chars): ${responseBody.substring(0, 200)}`);

    // V-World 에러 감지 (IP 차단 등)
    if (response.status !== 200 || responseBody.includes('blocked') || responseBody.includes('denied') || responseBody.includes('ERROR')) {
      console.log(`[PROXY] Possible block detected. Full response: ${responseBody.substring(0, 500)}`);
    }

    // 새 Response 생성 (CORS 헤더 포함)
    return new Response(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: {
        ...corsHeaders,
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
        'X-CF-Colo': cfInfo.colo || 'unknown',
        'X-CF-Country': cfInfo.country || 'unknown',
      },
    });
  } catch (fetchError) {
    console.log(`[PROXY] Fetch error: ${fetchError.message}`);
    throw fetchError;
  }
}

/**
 * GET 요청 처리
 */
async function handleGet(request) {
  const url = new URL(request.url);
  const targetUrl = url.searchParams.get('url');

  if (!targetUrl) {
    return new Response(JSON.stringify({
      error: 'Missing url parameter',
      usage: 'GET /proxy?url=https://api.vworld.kr/...'
    }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }

  const decodedUrl = decodeURIComponent(targetUrl);

  if (!isAllowedUrl(decodedUrl)) {
    return new Response(JSON.stringify({
      error: 'URL not allowed. Only V-World API domains are permitted.',
      allowed: ALLOWED_DOMAINS
    }), {
      status: 403,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }

  return proxyRequest(decodedUrl, 'GET', null, request);
}

/**
 * POST 요청 처리
 */
async function handlePost(request) {
  let body;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({
      error: 'Invalid JSON body',
      usage: 'POST /proxy with { "url": "...", "params": {...} }'
    }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }

  const { url: targetUrl, params, method = 'GET' } = body;

  if (!targetUrl) {
    return new Response(JSON.stringify({ error: 'Missing url in body' }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }

  if (!isAllowedUrl(targetUrl)) {
    return new Response(JSON.stringify({
      error: 'URL not allowed. Only V-World API domains are permitted.',
      allowed: ALLOWED_DOMAINS
    }), {
      status: 403,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }

  // params가 있으면 URL에 추가
  let finalUrl = targetUrl;
  if (params && typeof params === 'object') {
    const searchParams = new URLSearchParams(params);
    finalUrl = `${targetUrl}?${searchParams.toString()}`;
  }

  return proxyRequest(finalUrl, method, null, request);
}

/**
 * 메인 요청 핸들러
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // CORS preflight 처리
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // 헬스 체크
    if (url.pathname === '/' || url.pathname === '/health') {
      return new Response(JSON.stringify({
        status: 'ok',
        service: 'V-World API Proxy',
        endpoints: {
          'GET /proxy?url=...': 'Proxy GET request to V-World API',
          'POST /proxy': 'Proxy request with JSON body { url, params, method }'
        },
        allowed_domains: ALLOWED_DOMAINS
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // 프록시 엔드포인트
    if (url.pathname === '/proxy') {
      try {
        if (request.method === 'GET') {
          return await handleGet(request);
        } else if (request.method === 'POST') {
          return await handlePost(request);
        }
      } catch (error) {
        return new Response(JSON.stringify({
          error: 'Proxy error',
          message: error.message
        }), {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
    }

    return new Response(JSON.stringify({ error: 'Not found' }), {
      status: 404,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  },
};

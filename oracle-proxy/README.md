# V-World API Proxy - Oracle Cloud 한국 설정 가이드

V-World API는 해외 IP를 차단하므로, Oracle Cloud 한국(서울) 리전에서 프록시 서버를 운영합니다.

## 1. Oracle Cloud 계정 생성

1. https://www.oracle.com/cloud/free/ 접속
2. **Start for free** 클릭
3. **Home Region**: `South Korea Central (Seoul)` 선택 ⚠️ 중요!
4. 계정 정보 입력 및 신용카드 등록 (무료 티어는 과금 안 됨)

## 2. VM 인스턴스 생성

1. Oracle Cloud Console 접속: https://cloud.oracle.com
2. 좌측 메뉴 → **Compute** → **Instances**
3. **Create Instance** 클릭

### 인스턴스 설정:
- **Name**: `vworld-proxy`
- **Compartment**: 기본값
- **Placement**: `AD-1` (Seoul)
- **Image**: `Ubuntu 22.04` (Canonical Ubuntu)
- **Shape**: `VM.Standard.E2.1.Micro` (Always Free) ⚠️ 무료!
- **Networking**: 기본 VCN 사용 또는 새로 생성
- **Add SSH keys**:
  - Generate a key pair → **Save Private Key** 다운로드
  - 또는 기존 공개키 업로드

4. **Create** 클릭 → 몇 분 대기

## 3. 네트워크 보안 설정 (포트 열기)

1. 생성된 인스턴스 클릭 → **Subnet** 링크 클릭
2. **Security Lists** → 기본 Security List 클릭
3. **Add Ingress Rules** 클릭:
   - **Source CIDR**: `0.0.0.0/0`
   - **Destination Port Range**: `8080`
   - **Description**: `V-World Proxy`
4. **Add Ingress Rules** 저장

## 4. VM에 SSH 접속

```bash
# 다운로드한 Private Key 권한 설정
chmod 400 ~/Downloads/ssh-key-*.key

# SSH 접속 (Public IP는 인스턴스 상세에서 확인)
ssh -i ~/Downloads/ssh-key-*.key ubuntu@<PUBLIC_IP>
```

Windows라면 PuTTY 사용 또는 PowerShell:
```powershell
ssh -i C:\Users\<username>\Downloads\ssh-key-*.key ubuntu@<PUBLIC_IP>
```

## 5. 프록시 서버 배포

### 5.1 파일 업로드 (로컬에서)
```bash
scp -i ~/Downloads/ssh-key-*.key vworld_proxy.py ubuntu@<PUBLIC_IP>:~/
scp -i ~/Downloads/ssh-key-*.key setup.sh ubuntu@<PUBLIC_IP>:~/
```

### 5.2 서버 설정 (VM에서)
```bash
# 설정 스크립트 실행
chmod +x setup.sh
bash setup.sh
```

### 5.3 수동 설정 (스크립트 대신)
```bash
# 패키지 설치
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# 프로젝트 설정
mkdir -p ~/vworld-proxy
cd ~/vworld-proxy
python3 -m venv venv
source venv/bin/activate
pip install flask requests flask-cors gunicorn

# vworld_proxy.py 파일을 ~/vworld-proxy/에 복사

# 서버 실행 (테스트)
python vworld_proxy.py

# 또는 gunicorn으로 실행 (프로덕션)
gunicorn -w 4 -b 0.0.0.0:8080 vworld_proxy:app
```

## 6. 테스트

```bash
# 로컬에서 테스트
curl http://<PUBLIC_IP>:8080/health

# 응답 예시:
# {"status": "ok", "service": "V-World API Proxy (Oracle Cloud Korea)", ...}
```

## 7. Streamlit 설정

Streamlit secrets에 프록시 URL 추가:

```toml
# .streamlit/secrets.toml 또는 Streamlit Cloud Secrets
ORACLE_PROXY_URL = "http://<PUBLIC_IP>:8080"
```

## 8. 서비스 관리

```bash
# 상태 확인
sudo systemctl status vworld-proxy

# 재시작
sudo systemctl restart vworld-proxy

# 로그 확인
sudo journalctl -u vworld-proxy -f

# 중지
sudo systemctl stop vworld-proxy
```

## 비용

Oracle Cloud Always Free Tier:
- VM.Standard.E2.1.Micro: **무료** (영구)
- 네트워크 대역폭: 월 10TB 무료
- 스토리지: 200GB 무료

⚠️ 무료 티어를 초과하지 않도록 Always Free Shape만 사용하세요.

## 문제 해결

### 연결 안 됨
1. Security List에 8080 포트 Ingress Rule 확인
2. VM 내부 방화벽 확인: `sudo iptables -L`
3. 서비스 실행 확인: `sudo systemctl status vworld-proxy`

### V-World API 오류
1. 서버 로그 확인: `sudo journalctl -u vworld-proxy -f`
2. V-World API 키 확인

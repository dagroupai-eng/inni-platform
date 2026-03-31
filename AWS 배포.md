# AWS Lightsail 배포 가이드 (inni-platform)

## 전체 순서 요약
- [x] 1. Lightsail 인스턴스 생성 (USDL-teamA, USDL-teamB)
- [x] 2. Static IP 연결
- [x] 3. SSH 키 다운로드
- [x] 4. SSH 접속 확인
- [x] 5. 서버 초기 세팅 (apt upgrade, python3, git, geopandas 의존성)
- [x] 6. 코드 배포 (git clone, venv, pip install)
- [x] 7. 환경변수 설정 (.streamlit/secrets.toml)
- [x] 8. 서비스 등록 (systemd active running 확인)
- [x] 9. 방화벽 포트 열기 (TCP 8501)
- [x] 10. 접속 확인 완료
- [x] 11. GitHub Actions 자동 배포 완료 (teamA, teamB 동시 배포)

---

## STEP 1 — Lightsail 인스턴스 생성

1. AWS 콘솔 상단 검색창에 `Lightsail` 입력 → 클릭
2. **Create instance** 버튼 클릭
3. 아래 항목 설정:

| 항목 | 값 |
|------|-----|
| Region | **Asia Pacific (Seoul) ap-northeast-2** |
| Availability zone | ap-northeast-2a (기본값) |
| Platform | **Linux/Unix** |
| Blueprint | **OS Only → Ubuntu 24.04 LTS** |
| Instance plan | **$12/month** (2GB RAM / 2vCPU / 60GB SSD) |
| Instance name | `inni-platform` (자유) |

4. **Create instance** 클릭
5. 상태가 `Running` 이 될 때까지 대기 (1~2분)

---

## STEP 2 — SSH 접속

### 방법 A — 브라우저에서 바로 접속 (가장 간단)
1. Lightsail 콘솔에서 인스턴스 클릭
2. **Connect using SSH** 버튼 클릭
3. 브라우저에서 터미널 창 열림 → 바로 사용 가능

### 방법 B — 로컬 터미널에서 접속
1. Lightsail 콘솔 → 인스턴스 → **Account** 탭
2. **Download default key** 클릭 → `.pem` 파일 저장
3. Git Bash 또는 PowerShell에서:

```bash
chmod 400 LightsailDefaultKey-ap-northeast-2.pem
ssh -i LightsailDefaultKey-ap-northeast-2.pem ubuntu@[공인IP]
```

공인 IP는 인스턴스 상세 페이지에서 확인

---

## STEP 3 — 서버 초기 세팅

SSH 접속 후 아래 명령어 순서대로 실행:

```bash
# 패키지 업데이트 ✅ 완료
sudo apt update && sudo apt upgrade -y

# Python, Git 설치 ← 다음 할 것
sudo apt install python3-pip python3-venv git -y

# geopandas 시스템 의존성 설치 (필수)
sudo apt install libgeos-dev libproj-dev gdal-bin libgdal-dev -y
```

---

## STEP 4 — 코드 배포

```bash
# GitHub에서 코드 클론
git clone https://github.com/[계정명]/inni-platform.git
cd inni-platform

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 패키지 설치 (5~10분 소요)
pip install -r requirements.txt
```

> GitHub 레포가 **private**인 경우:
> ```bash
> git clone https://[GitHub토큰]@github.com/[계정명]/inni-platform.git
> ```
> GitHub → Settings → Developer settings → Personal access tokens에서 토큰 발급

---

## STEP 5 — 환경변수 설정

### .env 파일 생성

```bash
nano .env
```

아래 내용 입력 (실제 키값으로 교체):

```env
GEMINI_API_KEY=실제키값
VWORLD_API_KEY=실제키값
ENCRYPTION_MASTER_KEY=실제키값
ADMIN_PERSONAL_NUMBERS=ADMIN001
SUPABASE_URL=https://실제프로젝트.supabase.co
SUPABASE_SERVICE_ROLE_KEY=실제키값
```

저장: `Ctrl+O` → Enter → `Ctrl+X`

### Streamlit secrets.toml 생성

```bash
mkdir -p .streamlit
nano .streamlit/secrets.toml
```

아래 내용 입력:

```toml
GEMINI_API_KEY = "실제키값"
VWORLD_API_KEY = "실제키값"
ENCRYPTION_MASTER_KEY = "실제키값"
ADMIN_PERSONAL_NUMBERS = "ADMIN001"
SUPABASE_URL = "https://실제프로젝트.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "실제키값"
```

저장: `Ctrl+O` → Enter → `Ctrl+X`

---

## STEP 6 — 서비스 등록 (상시 실행)

서버 재부팅 후에도 자동 시작되도록 systemd에 등록:

```bash
sudo nano /etc/systemd/system/streamlit.service
```

아래 내용 붙여넣기:

```ini
[Unit]
Description=Streamlit inni-platform
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/inni-platform
Environment="PATH=/home/ubuntu/inni-platform/venv/bin"
ExecStart=/home/ubuntu/inni-platform/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

저장 후 서비스 시작:

```bash
sudo systemctl daemon-reload
sudo systemctl enable streamlit
sudo systemctl start streamlit
sudo systemctl status streamlit
```

`Active: active (running)` 표시되면 성공

---

## STEP 7 — 방화벽 포트 열기

### Lightsail 콘솔에서 설정

1. Lightsail 콘솔 → 인스턴스 클릭
2. **Networking** 탭 클릭
3. **Firewall** 섹션 → **Add rule** 클릭
4. 아래 설정:

| 항목 | 값 |
|------|-----|
| Application | Custom |
| Protocol | TCP |
| Port | 8501 |

5. **Create** 저장

---

## STEP 8 — 접속 확인

브라우저에서 접속:
```
http://[서버공인IP]:8501
```

앱이 정상 표시되면 배포 완료.

---

## STEP 9 — GitHub Actions 자동 배포 설정

`git push` 하면 서버에 자동으로 반영됩니다.

### 9-1. 서버에 deploy 키 등록

서버(SSH 접속 후)에서:

```bash
# 배포 전용 SSH 키 생성
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -N ""

# 공개키 출력 (복사해둘 것)
cat ~/.ssh/deploy_key.pub

# SSH 설정에 등록
echo 'Host github.com
  IdentityFile ~/.ssh/deploy_key' >> ~/.ssh/config

# GitHub Actions가 서버에 접속할 수 있도록 authorized_keys에 추가 (필수!)
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys
```

### 9-2. GitHub에 공개키 등록

1. GitHub 레포 → **Settings → Deploy keys → Add deploy key**
2. Title: `lightsail-server`
3. Key: 위에서 복사한 공개키 붙여넣기
4. **Allow write access 체크 안 함** → **Add key**

### 9-3. GitHub Actions 워크플로우 파일 생성

로컬에서 파일 생성:

```bash
mkdir -p .github/workflows
```

`.github/workflows/deploy.yml` 파일 생성 후 아래 내용 입력:

```yaml
name: Deploy to Lightsail

on:
  push:
    branches:
      - master

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SERVER_IP }}
          username: ubuntu
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /home/ubuntu/inni-platform
            git pull
            source venv/bin/activate
            pip install -r requirements.txt --quiet
            sudo systemctl restart streamlit
```

### 9-4. GitHub Secrets 등록

GitHub 레포 → **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|------|-------|
| `SERVER_IP` | 서버 공인 IP |
| `SERVER_SSH_KEY` | 서버의 private key 내용 (`cat ~/.ssh/deploy_key`) |

### 9-5. 서버 sudo 권한 설정 (systemctl restart 허용)

서버에서:

```bash
echo 'ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart streamlit' | sudo tee /etc/sudoers.d/streamlit
```

### 9-6. 동작 확인

로컬에서 코드 수정 후:

```bash
git add .
git commit -m "수정 내용"
git push origin master
```

→ GitHub Actions 탭에서 자동 배포 진행 확인

---

## 수동 업데이트 (긴급 시)

```bash
ssh -i LightsailDefaultKey-ap-northeast-2.pem ubuntu@[서버IP]
cd inni-platform && git pull && sudo systemctl restart streamlit
```

---

## 로그 확인 (문제 발생 시)

```bash
# 실시간 로그
sudo journalctl -u streamlit -f

# 최근 50줄
sudo journalctl -u streamlit -n 50
```

---

## 코드 변경 사항

- `pages/2_Mapping.py` — `_vworld_get()` 함수에서 Oracle 프록시 분기 제거
  - 서울 리전 서버에서 VWorld 직접 호출하므로 우회 불필요
  - `ORACLE_PROXY_URL` 환경변수도 더 이상 불필요

---

## 메모

- 리전: Asia Pacific (Seoul) ap-northeast-2
- 월 비용: $12 × 2 = $24
- **Static IP**: 인스턴스 생성 후 Lightsail 콘솔 → Networking → Static IP 생성 및 연결 필수 (재시작 시 IP 변경 방지)

| 인스턴스 | IP | 용도 |
|---------|-----|------|
| USDL-teamA | 13.209.225.230 | A팀 |
| USDL-teamB | 3.34.113.163 | B팀 |

- SSH 키 위치: (여기에 기록)

## 향후 구현 예정

- **분석 대기열 시스템**: 동시 분석 요청 시 Supabase queue 테이블로 순서 관리
  - 동시 분석 인원 제한 → $12 플랜으로 안정적 운영 가능
  - 유저에게 대기 순서 실시간 표시 (st.rerun() polling 방식)

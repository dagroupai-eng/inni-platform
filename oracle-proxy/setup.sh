#!/bin/bash
# Oracle Cloud VM 초기 설정 스크립트
# VM에 SSH 접속 후 실행: bash setup.sh

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 및 pip 설치
sudo apt install -y python3 python3-pip python3-venv

# 프로젝트 디렉토리 생성
mkdir -p ~/vworld-proxy
cd ~/vworld-proxy

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 패키지 설치
pip install flask requests flask-cors gunicorn

# vworld_proxy.py 파일을 이 디렉토리에 복사해야 함
# scp vworld_proxy.py user@<VM_IP>:~/vworld-proxy/

# systemd 서비스 파일 생성
sudo tee /etc/systemd/system/vworld-proxy.service > /dev/null <<EOF
[Unit]
Description=V-World API Proxy
After=network.target

[Service]
User=$USER
WorkingDirectory=/home/$USER/vworld-proxy
Environment="PATH=/home/$USER/vworld-proxy/venv/bin"
ExecStart=/home/$USER/vworld-proxy/venv/bin/gunicorn -w 4 -b 0.0.0.0:8080 vworld_proxy:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 서비스 시작
sudo systemctl daemon-reload
sudo systemctl enable vworld-proxy
sudo systemctl start vworld-proxy

# 방화벽에서 포트 8080 열기 (Ubuntu)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT
sudo netfilter-persistent save

echo ""
echo "======================================"
echo "설정 완료!"
echo "======================================"
echo ""
echo "서비스 상태 확인: sudo systemctl status vworld-proxy"
echo "로그 확인: sudo journalctl -u vworld-proxy -f"
echo ""
echo "테스트: curl http://localhost:8080/health"
echo ""
echo "중요: Oracle Cloud 콘솔에서 Security List에 포트 8080 추가 필요!"

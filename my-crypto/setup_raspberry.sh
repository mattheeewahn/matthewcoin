#!/bin/bash
# 라즈베리파이 초기 설정 스크립트
# 실행: bash setup_raspberry.sh

echo "=== MATTHEW Coin 서버 설정 ==="

# 패키지 설치
pip install flask cryptography requests

# systemd 서비스 등록 (재부팅해도 자동 시작)
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
USER=$(whoami)

sudo tee /etc/systemd/system/matthewcoin.service > /dev/null <<EOF
[Unit]
Description=MATTHEW Coin Server
After=network.target

[Service]
User=$USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $SCRIPT_DIR/server.py --port 5000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable matthewcoin
sudo systemctl start matthewcoin

echo ""
echo "서버 시작됨!"
echo "상태 확인: sudo systemctl status matthewcoin"
echo "로그 확인: sudo journalctl -u matthewcoin -f"
echo ""
echo "=== Cloudflare Tunnel 설치 (외부 접속용) ==="
echo "아래 명령어를 실행하세요:"
echo ""
echo "  # ARM64 (라즈베리파이 5)"
echo "  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -o cloudflared"
echo "  chmod +x cloudflared && sudo mv cloudflared /usr/local/bin/"
echo ""
echo "  # 터널 실행 (임시 URL)"
echo "  cloudflared tunnel --url http://localhost:5000"

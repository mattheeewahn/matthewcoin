#!/bin/bash
echo "============================================"
echo "  MATTHEW Coin (MTW) - macOS DMG 빌드"
echo "============================================"

# PyInstaller 설치
pip install pyinstaller --quiet

# .app 빌드
echo ""
echo "[1/3] PyInstaller 빌드 중..."
pyinstaller build.spec --clean --noconfirm

# create-dmg 설치 (없으면)
if ! command -v create-dmg &> /dev/null; then
    echo "[2/3] create-dmg 설치 중..."
    brew install create-dmg
fi

# DMG 생성
echo "[3/3] DMG 패키징 중..."
create-dmg \
  --volname "MATTHEW Coin Wallet" \
  --volicon "icon.icns" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "MatthewCoin.app" 175 190 \
  --hide-extension "MatthewCoin.app" \
  --app-drop-link 425 190 \
  "MatthewCoin-1.0.0.dmg" \
  "dist/MatthewCoin.app" 2>/dev/null || \
  hdiutil create -volname "MatthewCoin" -srcfolder dist/MatthewCoin.app \
    -ov -format UDZO MatthewCoin-1.0.0.dmg

echo ""
echo "완료! 결과물: MatthewCoin-1.0.0.dmg"

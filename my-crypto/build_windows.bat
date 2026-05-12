@echo off
echo ============================================
echo   MATTHEW Coin (MTW) - Windows EXE 빌드
echo ============================================

:: PyInstaller 설치 확인
python -m pip install pyinstaller --quiet

:: 빌드
echo.
echo [1/2] PyInstaller 빌드 중...
python -m PyInstaller build.spec --clean --noconfirm

echo.
echo [2/2] 완료!
echo   결과물: dist\MatthewCoin.exe
echo.
pause

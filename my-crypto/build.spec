# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec - MATTHEW Coin (MTW)

block_cipher = None

a = Analysis(
    ['ui.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'cryptography',
        'cryptography.hazmat.primitives.asymmetric.ec',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.primitives.serialization',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',
        'cryptography.hazmat.backends.openssl.backend',
        'cryptography.exceptions',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'PIL', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MatthewCoin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI 앱 - 콘솔 창 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # 아이콘 파일 있으면 'icon.ico' 로 변경
)

# macOS용 .app 번들
app = BUNDLE(
    exe,
    name='MatthewCoin.app',
    icon=None,              # 아이콘 파일 있으면 'icon.icns' 로 변경
    bundle_identifier='com.matthewcoin.wallet',
    info_plist={
        'CFBundleName': 'MatthewCoin',
        'CFBundleDisplayName': 'MATTHEW Coin Wallet',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
)

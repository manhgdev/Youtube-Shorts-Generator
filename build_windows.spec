# PyInstaller spec — build trên Windows:
#   pip install -r requirements.txt
#   pyinstaller build_windows.spec
#
# Bản exe nằm trong dist/. FFmpeg không được đóng gói — cài FFmpeg và thêm vào PATH trên máy Windows.
# Đặt console=True nếu cần cửa sổ console khi gỡ lỗi khởi động GUI.

from pathlib import Path

block_cipher = None
root = Path(SPECPATH).resolve()

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "google.genai",
        "google.genai.types",
        "websockets",
        "certifi",
        "mutagen.mp3",
        "ffmpeg",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="AI-Youtube-Shorts-Generator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

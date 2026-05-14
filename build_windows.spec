# PyInstaller spec — build trên Windows:
#   pip install -r requirements.txt
#   pyinstaller build_windows.spec
#
# Bản exe nằm trong dist/. FFmpeg: đóng gói kèm imageio-ffmpeg (PyInstaller collect_all).
# Vẫn có thể dùng ffmpeg hệ thống hoặc đặt ffmpeg.exe cạnh exe.
# Đặt console=True nếu cần cửa sổ console khi gỡ lỗi khởi động GUI.

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
root = Path(SPECPATH).resolve()

_iio_datas, _iio_binaries, _iio_hidden = collect_all("imageio_ffmpeg")

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=_iio_binaries,
    datas=_iio_datas,
    hiddenimports=[
        "google.genai",
        "google.genai.types",
        "websockets",
        "certifi",
        "mutagen.mp3",
        "ffmpeg",
        "imageio_ffmpeg",
        "modules.ffmpeg_env",
        "modules.media_probe",
        *_iio_hidden,
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

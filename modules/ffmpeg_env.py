"""Cấu hình PATH để tìm ffmpeg: bundle imageio-ffmpeg, thư mục cạnh exe, PATH hệ thống."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser


def app_binary_directory() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def prepend_imageio_ffmpeg() -> None:
    try:
        import imageio_ffmpeg

        bindir = os.path.dirname(os.path.abspath(imageio_ffmpeg.get_ffmpeg_exe()))
    except Exception:
        return
    if not bindir or not os.path.isdir(bindir):
        return
    path = os.environ.get("PATH", "")
    parts = path.split(os.pathsep) if path else []
    if bindir in parts or path.startswith(bindir + os.pathsep):
        return
    os.environ["PATH"] = bindir + os.pathsep + path


def prepend_adjacent_ffmpeg_dirs() -> None:
    root = app_binary_directory()
    guess_dirs = [
        root,
        os.path.join(root, "bin"),
        os.path.join(root, "ffmpeg", "bin"),
        os.path.join(root, "ffmpeg"),
    ]
    path = os.environ.get("PATH", "")
    parts = path.split(os.pathsep) if path else []
    prepend: list[str] = []
    for d in guess_dirs:
        if not d or not os.path.isdir(d):
            continue
        exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        if os.path.isfile(os.path.join(d, exe)) and d not in prepend and d not in parts:
            prepend.append(d)
    if prepend:
        os.environ["PATH"] = os.pathsep.join(prepend) + os.pathsep + path


def configure_all_ffmpeg_paths() -> None:
    prepend_imageio_ffmpeg()
    prepend_adjacent_ffmpeg_dirs()


def ffmpeg_executable() -> str | None:
    configure_all_ffmpeg_paths()
    return shutil.which("ffmpeg")


def ffmpeg_health_message() -> tuple[bool, str]:
    exe = ffmpeg_executable()
    if not exe:
        return False, "Chưa tìm thấy ffmpeg."
    kw: dict = {}
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        r = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=20, check=False, **kw)
        if r.returncode != 0:
            return False, f"Không chạy được: {exe}"
        line = ((r.stdout or r.stderr) or "").splitlines()[0] if (r.stdout or r.stderr) else exe
        return True, line[:160]
    except Exception as e:
        return False, str(e)


def open_app_folder() -> None:
    path = app_binary_directory()
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except OSError:
        pass


def open_ffmpeg_download_page() -> None:
    webbrowser.open("https://www.gyan.dev/ffmpeg/builds/")


def try_winget_install_ffmpeg() -> tuple[bool, str]:
    if sys.platform != "win32":
        return False, "Chỉ hỗ trợ winget trên Windows."
    try:
        subprocess.Popen(
            [
                "winget",
                "install",
                "-e",
                "--id",
                "Gyan.FFmpeg",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
        )
        return True, "Đã khởi chạy winget. Khi cài xong, đóng app và mở lại, rồi bấm «Kiểm tra FFmpeg»."
    except FileNotFoundError:
        return False, "Không tìm thấy winget. Mở trang tải FFmpeg (nút «Trang tải FFmpeg») hoặc đặt ffmpeg.exe cạnh file exe."
    except OSError as e:
        return False, str(e)

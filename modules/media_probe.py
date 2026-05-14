"""Đo độ dài media: ưu tiên ffprobe; chỉ có ffmpeg (imageio-ffmpeg) thì parse stderr của ffmpeg -i."""
from __future__ import annotations

import os
import re
import shutil
import subprocess


def _subprocess_kw() -> dict:
    kw: dict = {}
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kw


def media_duration_seconds(filepath: str) -> float:
    if not filepath or not os.path.isfile(filepath):
        return 0.0
    kw = _subprocess_kw()

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            out = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    filepath,
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
                **kw,
            )
            if out.returncode == 0 and (out.stdout or "").strip():
                return float((out.stdout or "").strip())
        except (ValueError, subprocess.TimeoutExpired, OSError):
            pass

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return 0.0
    try:
        p = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", filepath],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            **kw,
        )
    except (subprocess.TimeoutExpired, OSError):
        return 0.0
    err = (p.stderr or "") + (p.stdout or "")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", err)
    if not m:
        return 0.0
    h, mi, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s

"""Đường dẫn media khi đóng gói PyInstaller: file trong datas nằm dưới sys._MEIPASS."""
from __future__ import annotations

import os
import sys


def resolve_media_path(raw: str) -> str:
    """
    - Đường dẫn tuyệt đối: giữ nguyên (chuẩn hóa).
    - Đường dẫn tương đối: nếu frozen và file có trong bundle (_MEIPASS) thì dùng đó;
      không thì dùng thư mục làm việc hiện tại (dev / file cạnh exe).
    """
    p = (raw or "").strip()
    if not p:
        return ""
    if os.path.isabs(p):
        return os.path.normpath(p)
    rel = p.replace("\\", "/").lstrip("/")
    parts = rel.split("/")
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = os.path.normpath(os.path.join(sys._MEIPASS, *parts))
        if os.path.isfile(bundled):
            return bundled
    return os.path.normpath(os.path.join(os.getcwd(), *parts))

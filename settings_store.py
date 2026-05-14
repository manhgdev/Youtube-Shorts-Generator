"""
Lưu / đọc cấu hình người dùng (API keys, model Gemini, prompt).
File JSON nằm cạnh exe (frozen) hoặc thư mục gốc project (dev).
"""
import json
import os
import sys
from typing import Any, Dict

DEFAULT_TOPIC_PROMPT = (
    "Give me 1 specific, viral, and engaging topic for a Short Documentary. "
    "It should be a 'Engaging Did you know' fact or a 'Fun/intriguing Engaging News'. "
    "return ONLY the topic name."
)

AVATAR_VIDEO_DEFAULT_REL = os.path.join("assets", "avatar", "avatars.mp4")
AVATAR_IMAGE_DEFAULT_REL = os.path.join(
    "assets", "avatar", "Gemini_Generated_Image_ww2ko4ww2ko4ww2k.png"
)


def _project_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def get_app_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return _project_root()


def get_settings_path() -> str:
    return os.path.join(get_app_root(), "user_settings.json")


def _default_gemini_model() -> str:
    from config import MODEL_CONFIG

    return MODEL_CONFIG["models"][0]["name"]


def default_settings() -> Dict[str, Any]:
    return {
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", "").strip(),
        "pexels_api_key": os.environ.get("PEXELS_API_KEY", "").strip(),
        "gemini_model": _default_gemini_model(),
        "topic_prompt": DEFAULT_TOPIC_PROMPT,
        "use_manual_topic": False,
        "manual_topic": "",
        "script_extra_instructions": "",
        "video_mode": "short",
        "avatar_mode": "default",
        "avatar_video_path": "",
        "avatar_image_path": "",
        "output_dir": os.path.join("assets", "final"),
    }


def load_settings() -> Dict[str, Any]:
    path = get_settings_path()
    data = default_settings()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user = json.load(f)
            if isinstance(user, dict):
                for k in data:
                    if k in user:
                        data[k] = user[k]
                if "avatar_mode" not in user:
                    if (str(user.get("avatar_video_path") or "").strip() or str(user.get("avatar_image_path") or "").strip()):
                        data["avatar_mode"] = "custom"
        except (json.JSONDecodeError, OSError):
            pass
    return data


def save_settings(data: Dict[str, Any]) -> None:
    path = get_settings_path()
    base = {k: data.get(k, default_settings()[k]) for k in default_settings()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(base, f, indent=2, ensure_ascii=False)


def effective_gemini_model(settings: Dict[str, Any]) -> str:
    name = (settings.get("gemini_model") or "").strip()
    return name or _default_gemini_model()

import argparse
import asyncio
import os
import shutil
import sys

from settings_store import (
    DEFAULT_TOPIC_PROMPT,
    effective_gemini_model,
    load_settings,
    save_settings,
)


def ensure_working_directory() -> None:
    """Khi đóng gói exe, cwd có thể không phải thư mục app — chuyển về thư mục chứa exe / project."""
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))


def ensure_ffmpeg_available() -> None:
    """
    Cần lệnh ffmpeg (bundle imageio-ffmpeg, thư mục cạnh exe, hoặc PATH).
    Độ dài clip dùng ffprobe nếu có, không thì parse từ ffmpeg -i (không bắt buộc ffprobe).
    """
    from modules.ffmpeg_env import app_binary_directory, configure_all_ffmpeg_paths

    configure_all_ffmpeg_paths()
    if shutil.which("ffmpeg"):
        return

    app_root = app_binary_directory()
    raise RuntimeError(
        "Không tìm thấy ffmpeg (WinError 2 nếu thiếu file).\n\n"
        "• Bản build đầy đủ đã gói ffmpeg qua imageio-ffmpeg — build lại exe sau khi cập nhật repo.\n"
        "• Hoặc cài FFmpeg (winget / trang Gyan), hoặc đặt ffmpeg.exe cạnh file exe:\n"
        f"  {app_root}"
    )


async def run_pipeline(settings: dict) -> None:
    """Chạy toàn bộ pipeline với dict cấu hình (từ UI hoặc user_settings.json)."""
    ensure_working_directory()
    ensure_ffmpeg_available()
    from modules.brain import ContentBrain
    from modules.asset_manager import AssetManager
    from modules.audio import AudioEngine
    from modules.composer import Composer

    gemini_key = (settings.get("gemini_api_key") or "").strip()
    pexels_key = (settings.get("pexels_api_key") or "").strip()
    if not gemini_key:
        raise ValueError("Thiếu Gemini API key — nhập trong ứng dụng hoặc biến môi trường GEMINI_API_KEY.")
    if not pexels_key:
        raise ValueError("Thiếu Pexels API key — nhập trong ứng dụng hoặc biến môi trường PEXELS_API_KEY.")

    print("🚀 STARTING AUTOMATION...")

    model_name = effective_gemini_model(settings)
    topic_prompt = (settings.get("topic_prompt") or "").strip() or DEFAULT_TOPIC_PROMPT
    script_extra = (settings.get("script_extra_instructions") or "").strip()

    brain = ContentBrain(
        api_key=gemini_key,
        model_name=model_name,
        topic_prompt=topic_prompt,
        script_extra_instructions=script_extra,
        video_mode=(settings.get("video_mode") or "short"),
    )

    if settings.get("use_manual_topic") and not (settings.get("manual_topic") or "").strip():
        raise ValueError("Chế độ topic cố định bật nhưng 'manual_topic' đang trống.")

    try:
        if settings.get("use_manual_topic") and (settings.get("manual_topic") or "").strip():
            topic = (settings.get("manual_topic") or "").strip()
            print(f"🎯 Manual topic: {topic}")
        else:
            topic = brain.get_trending_topic()
        script = brain.generate_script(topic)
    except Exception as e:
        print(f"❌ Brain Error: {e}")
        raise

    if not script:
        print("❌ Script generation failed.")
        raise RuntimeError("Script generation failed (empty or invalid JSON).")

    audio_engine = AudioEngine()
    try:
        script = await audio_engine.process_script(script)
    except Exception as e:
        print(f"❌ Audio Error: {e}")
        raise

    asset_manager = AssetManager(api_key=pexels_key)
    assets_map = asset_manager.get_videos(script)

    composer = Composer(settings)
    final_scene_paths = composer.render_all_scenes(script, assets_map)

    if final_scene_paths:
        composer.concatenate_with_transitions(final_scene_paths)
        clean_cache()
    else:
        print("❌ Failed to generate any scenes.")
        raise RuntimeError("No scenes rendered.")


def clean_cache():
    """
    Safely deletes temporary files.
    Includes a Safety Lock to prevent deleting anything outside the project.
    """
    import shutil

    print("🧹 Cleaning up temporary files...")

    folders_to_clean = [
        os.path.join(os.getcwd(), "assets", "audio_clips"),
        os.path.join(os.getcwd(), "assets", "video_clips"),
        os.path.join(os.getcwd(), "assets", "temp"),
    ]

    for folder in folders_to_clean:
        if not os.path.exists(folder):
            continue

        if "assets" not in folder:
            print(f"   🚨 SECURITY ALERT: Skipping {folder} because it looks unsafe!")
            continue

        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)

            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    print(f"      Deleted: {filename}")
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except OSError as e:
                print(f"   ❌ Failed to delete {file_path}. Reason: {e}")

    print("✨ Workspace clean!")


def launch_gui() -> None:
    from gui_launcher import run_app

    run_app()


def main() -> None:
    ensure_working_directory()
    parser = argparse.ArgumentParser(description="AI Youtube Shorts Generator")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Chạy không GUI (đọc user_settings.json hoặc .env).",
    )
    args = parser.parse_args()

    if args.cli:
        asyncio.run(run_pipeline(load_settings()))
    else:
        launch_gui()


if __name__ == "__main__":
    main()

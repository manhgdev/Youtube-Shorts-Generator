"""
Giao diện cấu hình: API keys, model Gemini, prompt topic / hướng dẫn thêm cho script.
"""
import asyncio
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from config import VIDEO_CONFIG, gemini_model_presets
from main import ensure_working_directory, run_pipeline
from settings_store import (
    DEFAULT_TOPIC_PROMPT,
    default_settings,
    get_app_root,
    get_settings_path,
    load_settings,
    save_settings,
)

from modules.ffmpeg_env import (
    configure_all_ffmpeg_paths,
    ffmpeg_health_message,
    open_app_folder,
    open_ffmpeg_download_page,
    try_winget_install_ffmpeg,
)


def _normalize_saved_media_path(path: str) -> str:
    """Lưu đường dẫn tương đối nếu file nằm trong thư mục ứng dụng (exe / project)."""
    path = (path or "").strip()
    if not path:
        return ""
    root = os.path.abspath(get_app_root())
    abs_p = os.path.abspath(os.path.expanduser(path))
    try:
        rel = os.path.relpath(abs_p, root)
        if not rel.startswith(".." + os.sep) and rel != "..":
            return rel
    except ValueError:
        pass
    return abs_p


class _TeeQueue:
    """Tee log ra queue; exe windowed (console=False) có thể có stdout/stderr = None."""

    def __init__(self, q: "queue.Queue[str]", orig):
        self.q = q
        self.orig = orig

    def write(self, s: str) -> int:
        if s:
            if self.orig is not None:
                self.orig.write(s)
            self.q.put(s)
        return len(s) if s else 0

    def flush(self) -> None:
        if self.orig is not None:
            self.orig.flush()


def run_app() -> None:
    ensure_working_directory()
    configure_all_ffmpeg_paths()
    root = tk.Tk()
    root.title("AI Youtube Shorts — Cấu hình & Chạy")
    root.minsize(720, 720)

    presets = gemini_model_presets()
    defaults = default_settings()
    loaded = load_settings()

    pad = {"padx": 8, "pady": 4}

    frm = ttk.Frame(root, padding=10)
    frm.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frm, text="Gemini API Key").grid(row=0, column=0, sticky="w", **pad)
    gemini_var = tk.StringVar(value=loaded.get("gemini_api_key", defaults["gemini_api_key"]))
    ttk.Entry(frm, textvariable=gemini_var, width=64, show="*").grid(row=0, column=1, sticky="ew", **pad)

    ttk.Label(frm, text="Pexels API Key").grid(row=1, column=0, sticky="w", **pad)
    pexels_var = tk.StringVar(value=loaded.get("pexels_api_key", defaults["pexels_api_key"]))
    ttk.Entry(frm, textvariable=pexels_var, width=64, show="*").grid(row=1, column=1, sticky="ew", **pad)

    ttk.Label(frm, text="FFmpeg (ghép video)").grid(row=2, column=0, sticky="nw", **pad)
    ffmpeg_wrap = ttk.Frame(frm)
    ffmpeg_wrap.grid(row=2, column=1, sticky="ew", **pad)
    ffmpeg_status_var = tk.StringVar(value="…")
    ttk.Label(ffmpeg_wrap, textvariable=ffmpeg_status_var, wraplength=480, justify=tk.LEFT).pack(
        side=tk.TOP, anchor="w", fill=tk.X
    )
    ffmpeg_btns = ttk.Frame(ffmpeg_wrap)
    ffmpeg_btns.pack(side=tk.TOP, anchor="w", pady=(4, 0))

    def _refresh_ffmpeg_status() -> None:
        ok, msg = ffmpeg_health_message()
        ffmpeg_status_var.set(("✓ " if ok else "✗ ") + msg)

    def _on_check_ffmpeg() -> None:
        configure_all_ffmpeg_paths()
        _refresh_ffmpeg_status()
        ok, msg = ffmpeg_health_message()
        if ok:
            messagebox.showinfo("FFmpeg", msg)
        else:
            messagebox.showwarning("FFmpeg", msg + "\n\nDùng nút «Cài qua winget» (Windows) hoặc «Trang tải FFmpeg».")

    def _on_winget_ffmpeg() -> None:
        ok, msg = try_winget_install_ffmpeg()
        if ok:
            messagebox.showinfo("Cài FFmpeg", msg)
        else:
            messagebox.showerror("Cài FFmpeg", msg)

    ttk.Button(ffmpeg_btns, text="Kiểm tra FFmpeg", command=_on_check_ffmpeg).pack(side=tk.LEFT, padx=(0, 6))
    if sys.platform == "win32":
        ttk.Button(ffmpeg_btns, text="Cài qua winget", command=_on_winget_ffmpeg).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(ffmpeg_btns, text="Trang tải FFmpeg", command=open_ffmpeg_download_page).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(ffmpeg_btns, text="Mở thư mục app", command=open_app_folder).pack(side=tk.LEFT, padx=(0, 6))

    ttk.Label(frm, text="Gemini model").grid(row=3, column=0, sticky="w", **pad)
    model_var = tk.StringVar(value=loaded.get("gemini_model", defaults["gemini_model"]))
    model_combo = ttk.Combobox(frm, textvariable=model_var, values=presets, width=62)
    model_combo.grid(row=3, column=1, sticky="ew", **pad)
    ttk.Label(frm, text="(có thể gõ model ID khác)", font=("TkDefaultFont", 9)).grid(
        row=4, column=1, sticky="w", padx=8
    )

    sm = VIDEO_CONFIG["short_mode"]
    lm = VIDEO_CONFIG["long_mode"]
    ttk.Label(frm, text="Độ dài video").grid(row=5, column=0, sticky="nw", **pad)
    video_mode_var = tk.StringVar(value=loaded.get("video_mode", defaults["video_mode"]))
    fr_len = ttk.Frame(frm)
    fr_len.grid(row=5, column=1, sticky="w", **pad)
    ttk.Radiobutton(
        fr_len,
        text=f"Ngắn — khoảng {sm['target_duration']}s tổng (gợi ý 40–50s), {sm['min_scenes']}–{sm['max_scenes']} cảnh",
        variable=video_mode_var,
        value="short",
    ).pack(anchor="w")
    ttk.Radiobutton(
        fr_len,
        text=f"Dài — thường ~60–90s, mục tiêu ~{lm['target_duration']}s, {lm['min_scenes']}–{lm['max_scenes']} cảnh",
        variable=video_mode_var,
        value="long",
    ).pack(anchor="w")

    ttk.Label(frm, text="Prompt chọn topic (Gemini)").grid(row=6, column=0, sticky="nw", **pad)
    topic_prompt = scrolledtext.ScrolledText(frm, height=5, width=70, wrap=tk.WORD)
    topic_prompt.grid(row=6, column=1, sticky="ew", **pad)
    topic_prompt.insert("1.0", loaded.get("topic_prompt", DEFAULT_TOPIC_PROMPT))

    manual_var = tk.BooleanVar(value=bool(loaded.get("use_manual_topic", False)))
    ttk.Checkbutton(frm, text="Dùng topic cố định (bỏ qua prompt chọn topic)", variable=manual_var).grid(
        row=7, column=1, sticky="w", **pad
    )

    ttk.Label(frm, text="Topic cố định").grid(row=8, column=0, sticky="w", **pad)
    manual_topic_var = tk.StringVar(value=loaded.get("manual_topic", ""))
    ttk.Entry(frm, textvariable=manual_topic_var, width=64).grid(row=8, column=1, sticky="ew", **pad)

    ttk.Label(frm, text="Hướng dẫn thêm cho kịch bản (tùy chọn)").grid(row=9, column=0, sticky="nw", **pad)
    script_extra = scrolledtext.ScrolledText(frm, height=4, width=70, wrap=tk.WORD)
    script_extra.grid(row=9, column=1, sticky="ew", **pad)
    script_extra.insert("1.0", loaded.get("script_extra_instructions", ""))

    ttk.Label(frm, text="Video nhân vật (avatar)").grid(row=10, column=0, sticky="w", **pad)
    avatar_vid_var = tk.StringVar(value=loaded.get("avatar_video_path", defaults["avatar_video_path"]))
    av_vid_row = ttk.Frame(frm)
    av_vid_row.grid(row=10, column=1, sticky="ew", **pad)
    ttk.Entry(av_vid_row, textvariable=avatar_vid_var, width=56).pack(side=tk.LEFT, fill=tk.X, expand=True)
    ttk.Button(
        av_vid_row,
        text="Chọn…",
        command=lambda: _browse_video(avatar_vid_var),
    ).pack(side=tk.LEFT, padx=(6, 0))

    ttk.Label(frm, text="Ảnh nhân vật (dự phòng)").grid(row=11, column=0, sticky="nw", **pad)
    avatar_img_var = tk.StringVar(value=loaded.get("avatar_image_path", defaults["avatar_image_path"]))
    av_img_row = ttk.Frame(frm)
    av_img_row.grid(row=11, column=1, sticky="ew", **pad)
    ttk.Entry(av_img_row, textvariable=avatar_img_var, width=56).pack(side=tk.LEFT, fill=tk.X, expand=True)
    ttk.Button(
        av_img_row,
        text="Chọn…",
        command=lambda: _browse_image(avatar_img_var),
    ).pack(side=tk.LEFT, padx=(6, 0))
    ttk.Label(
        frm,
        text="Ưu tiên video nếu file tồn tại; nếu không (hoặc để trống ô video) thì dùng ảnh khi file ảnh có mặt.",
        font=("TkDefaultFont", 9),
    ).grid(row=12, column=1, sticky="w", padx=8)

    def _browse_video(var: tk.StringVar) -> None:
        p = filedialog.askopenfilename(
            title="Chọn video avatar",
            filetypes=[
                ("Video", "*.mp4 *.mov *.webm *.mkv"),
                ("Tất cả", "*.*"),
            ],
        )
        if p:
            var.set(p)

    def _browse_image(var: tk.StringVar) -> None:
        p = filedialog.askopenfilename(
            title="Chọn ảnh avatar",
            filetypes=[
                ("Ảnh", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("Tất cả", "*.*"),
            ],
        )
        if p:
            var.set(p)

    log_q: queue.Queue[str] = queue.Queue()
    log_box = scrolledtext.ScrolledText(frm, height=12, width=70, wrap=tk.WORD, state=tk.DISABLED)
    log_box.grid(row=13, column=0, columnspan=2, sticky="nsew", pady=8)
    frm.rowconfigure(13, weight=1)
    frm.columnconfigure(1, weight=1)

    def _append_log(text: str) -> None:
        log_box.configure(state=tk.NORMAL)
        log_box.insert(tk.END, text)
        log_box.see(tk.END)
        log_box.configure(state=tk.DISABLED)

    def _drain_log_queue() -> None:
        try:
            while True:
                chunk = log_q.get_nowait()
                _append_log(chunk)
        except queue.Empty:
            pass
        root.after(120, _drain_log_queue)

    _drain_log_queue()

    def _gather_settings() -> dict:
        return {
            "gemini_api_key": gemini_var.get().strip(),
            "pexels_api_key": pexels_var.get().strip(),
            "gemini_model": model_var.get().strip(),
            "topic_prompt": topic_prompt.get("1.0", tk.END).strip(),
            "use_manual_topic": manual_var.get(),
            "manual_topic": manual_topic_var.get().strip(),
            "script_extra_instructions": script_extra.get("1.0", tk.END).strip(),
            "video_mode": video_mode_var.get().strip().lower(),
            "avatar_video_path": _normalize_saved_media_path(avatar_vid_var.get()),
            "avatar_image_path": _normalize_saved_media_path(avatar_img_var.get()),
        }

    def on_save() -> None:
        save_settings(_gather_settings())
        messagebox.showinfo("Đã lưu", f"Cấu hình đã ghi vào:\n{get_settings_path()}")

    run_btn: ttk.Button | None = None

    def on_run() -> None:
        data = _gather_settings()
        save_settings(data)
        if not data["gemini_api_key"]:
            messagebox.showerror("Thiếu key", "Nhập Gemini API key.")
            return
        if not data["pexels_api_key"]:
            messagebox.showerror("Thiếu key", "Nhập Pexels API key.")
            return
        if not data["gemini_model"]:
            messagebox.showerror("Model", "Chọn hoặc nhập tên model Gemini.")
            return
        if not data["use_manual_topic"] and not data["topic_prompt"]:
            messagebox.showerror("Prompt", "Prompt chọn topic không được để trống.")
            return
        if data["video_mode"] not in ("short", "long"):
            messagebox.showerror("Độ dài video", "Chọn Ngắn hoặc Dài.")
            return
        configure_all_ffmpeg_paths()
        ok_ff, ff_msg = ffmpeg_health_message()
        if not ok_ff:
            messagebox.showerror("FFmpeg", f"Chưa sẵn sàng:\n{ff_msg}\n\nBấm «Kiểm tra FFmpeg» hoặc «Cài qua winget» / «Trang tải FFmpeg».")
            return
        run_btn.configure(state=tk.DISABLED)
        log_box.configure(state=tk.NORMAL)
        log_box.delete("1.0", tk.END)
        log_box.configure(state=tk.DISABLED)

        result: dict = {}

        def worker() -> None:
            old_out, old_err = sys.stdout, sys.stderr
            tee_out = _TeeQueue(log_q, old_out)
            tee_err = _TeeQueue(log_q, old_err)
            try:
                sys.stdout, sys.stderr = tee_out, tee_err
                asyncio.run(run_pipeline(data))
                result["ok"] = True
            except Exception as e:
                result["err"] = e
            finally:
                sys.stdout, sys.stderr = old_out, old_err

            def done() -> None:
                run_btn.configure(state=tk.NORMAL)
                if result.get("err"):
                    messagebox.showerror("Lỗi", str(result["err"]))
                else:
                    messagebox.showinfo("Hoàn tất", "Pipeline chạy xong. Video: assets/final/final_short.mp4")

            root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    btn_row = ttk.Frame(frm)
    btn_row.grid(row=14, column=0, columnspan=2, pady=6)
    ttk.Button(btn_row, text="Lưu cấu hình", command=on_save).pack(side=tk.LEFT, padx=4)
    run_btn = ttk.Button(btn_row, text="Chạy tạo video", command=on_run)
    run_btn.pack(side=tk.LEFT, padx=4)

    _refresh_ffmpeg_status()

    root.mainloop()


if __name__ == "__main__":
    run_app()

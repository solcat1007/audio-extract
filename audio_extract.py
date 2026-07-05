# -*- coding: utf-8 -*-
"""
音频提取器 v1.0 — 从视频中提取音频
====================================
痛点：需要从视频素材中提取音频（如提取BGM、人声、环境音），单独用于其他项目。

功能：
  - 单个或批量添加视频文件
  - 选择输出格式（mp3 / wav / aac / flac）
  - 选择比特率（128k / 192k / 256k / 320k）
  - 用 ffmpeg 提取音频流，输出到源目录（同名不同后缀）
  - 进度提示，批量逐个处理

依赖：仅使用 Python 标准库，外部依赖 ffmpeg。
"""

import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

# ============================================================================
# 配色与常量
# ============================================================================
COLOR_BG = "#1e1e2e"
COLOR_CARD = "#2a2a3c"
COLOR_ACCENT = "#f97316"          # 橙色强调
COLOR_ACCENT_HOVER = "#ea580c"
COLOR_TEXT = "#e0e0e0"
COLOR_TEXT_SECONDARY = "#a0a0b0"
COLOR_ENTRY_BG = "#3a3a4c"
COLOR_GREEN = "#4ade80"
COLOR_WARN = "#fbbf24"
COLOR_DANGER = "#f87171"

AUDIO_FORMATS = {
    "mp3":  {"codec": "libmp3lame", "ext": ".mp3"},
    "wav":  {"codec": "pcm_s16le",  "ext": ".wav"},
    "aac":  {"codec": "aac",        "ext": ".aac"},
    "flac": {"codec": "flac",       "ext": ".flac"},
}


def find_ffmpeg() -> str | None:
    result = subprocess.run(["where", "ffmpeg"], capture_output=True, text=True, timeout=5)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().split("\n")[0].strip()
    common = [r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"]
    for p in common:
        if os.path.exists(p):
            return p
    return None


# ============================================================================
# 主程序
# ============================================================================

class AudioExtractApp:
    """音频提取器 v1.0"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("音频提取器 v1.0")
        self.root.geometry("460x350")
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG)

        self.video_files: list[str] = []
        self.ffmpeg_path = find_ffmpeg()
        self.processing = False

        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=COLOR_BG, foreground=COLOR_TEXT, font=("微软雅黑", 9))
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT)
        style.configure("Card.TLabelframe", background=COLOR_CARD, foreground=COLOR_ACCENT)
        style.configure("Card.TLabelframe.Label", background=COLOR_CARD, foreground=COLOR_ACCENT,
                        font=("微软雅黑", 10, "bold"))
        style.configure("Accent.TButton", background=COLOR_ACCENT, foreground="#ffffff",
                        borderwidth=0, font=("微软雅黑", 9, "bold"))
        style.map("Accent.TButton", background=[("active", COLOR_ACCENT_HOVER)])
        style.configure("Secondary.TButton", background="#444466", foreground=COLOR_TEXT, borderwidth=0)
        style.map("Secondary.TButton", background=[("active", "#555577")])

    def _build_ui(self):
        pad = {"padx": 8, "pady": 2}

        # ---- 视频列表 ----
        frm_list = ttk.LabelFrame(self.root, text="视频文件列表", style="Card.TLabelframe")
        frm_list.pack(fill=tk.BOTH, expand=True, **pad, pady=(8, 4))

        list_inner = tk.Frame(frm_list, bg=COLOR_CARD)
        list_inner.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        self.listbox = tk.Listbox(list_inner, height=6, bg=COLOR_ENTRY_BG, fg=COLOR_TEXT,
                                   font=("Consolas", 9), selectbackground=COLOR_ACCENT,
                                   selectforeground="#ffffff", relief=tk.FLAT)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(list_inner, orient=tk.VERTICAL, command=self.listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=sb.set)

        # 按钮行
        btn_row = tk.Frame(self.root, bg=COLOR_BG)
        btn_row.pack(fill=tk.X, **pad)

        ttk.Button(btn_row, text="添加视频", command=self._on_add_videos,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="移除选中", command=self._on_remove,
                   style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="清空列表", command=self._on_clear,
                   style="Secondary.TButton").pack(side=tk.LEFT)

        # ---- 输出设置 ----
        frm_opts = ttk.LabelFrame(self.root, text="输出设置", style="Card.TLabelframe")
        frm_opts.pack(fill=tk.X, **pad)

        opts_inner = tk.Frame(frm_opts, bg=COLOR_CARD)
        opts_inner.pack(fill=tk.X, padx=6, pady=4)

        # 格式
        tk.Label(opts_inner, text="输出格式：", bg=COLOR_CARD, fg=COLOR_TEXT).pack(side=tk.LEFT)
        self.fmt_var = tk.StringVar(value="mp3")
        self.fmt_combo = ttk.Combobox(opts_inner, textvariable=self.fmt_var, state="readonly",
                                       values=list(AUDIO_FORMATS.keys()), width=6,
                                       font=("微软雅黑", 9))
        self.fmt_combo.pack(side=tk.LEFT, padx=(4, 16))

        # 比特率
        tk.Label(opts_inner, text="比特率：", bg=COLOR_CARD, fg=COLOR_TEXT).pack(side=tk.LEFT)
        self.br_var = tk.StringVar(value="192k")
        br_combo = ttk.Combobox(opts_inner, textvariable=self.br_var, state="readonly",
                                 values=["128k", "192k", "256k", "320k"], width=6,
                                 font=("微软雅黑", 9))
        br_combo.pack(side=tk.LEFT, padx=(4, 0))

        # ---- 进度条 ----
        self.progress = ttk.Progressbar(self.root, mode="determinate", length=440)
        self.progress.pack(fill=tk.X, **pad, pady=(4, 2))

        # ---- 状态 ----
        self.lbl_status = tk.Label(self.root, text="就绪", bg=COLOR_BG, fg=COLOR_TEXT_SECONDARY,
                                    font=("微软雅黑", 8))
        self.lbl_status.pack(**pad)

        # ---- 提取按钮 ----
        self.btn_extract = ttk.Button(self.root, text="开始提取音频", command=self._on_extract,
                                       style="Accent.TButton", state="disabled")
        self.btn_extract.pack(pady=(2, 8), ipadx=20, ipady=4)

        # ffmpeg 状态
        ff_text = "ffmpeg: 已检测到" if self.ffmpeg_path else "ffmpeg: 未检测到！"
        ff_color = COLOR_GREEN if self.ffmpeg_path else COLOR_DANGER
        tk.Label(self.root, text=ff_text, bg=COLOR_BG, fg=ff_color, font=("微软雅黑", 8)).pack()

    # ------------------------------------------------------------------
    def _on_add_videos(self):
        files = filedialog.askopenfilenames(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm *.m4v *.ts *.mts *.m2ts"),
                       ("所有文件", "*.*")],
        )
        for f in files:
            if f not in self.video_files:
                self.video_files.append(f)
                self.listbox.insert(tk.END, f"  {os.path.basename(f)}")
        self._update_state()

    def _on_remove(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        for idx in reversed(sel):
            del self.video_files[idx]
            self.listbox.delete(idx)
        self._update_state()

    def _on_clear(self):
        self.video_files.clear()
        self.listbox.delete(0, tk.END)
        self._update_state()

    def _update_state(self):
        n = len(self.video_files)
        self.lbl_status.config(
            text=f"{n} 个视频就绪" if n else "请添加视频文件",
            fg=COLOR_GREEN if n else COLOR_TEXT_SECONDARY,
        )
        has_ff = self.ffmpeg_path is not None
        self.btn_extract.configure(state="normal" if n > 0 and has_ff and not self.processing else "disabled")

    # ------------------------------------------------------------------
    def _on_extract(self):
        if not self.ffmpeg_path:
            messagebox.showerror("缺少 ffmpeg", "请安装 ffmpeg 并添加到 PATH")
            return
        if not self.video_files:
            return

        self.processing = True
        self.btn_extract.configure(state="disabled", text="提取中...")
        self.progress["maximum"] = len(self.video_files)
        self.progress["value"] = 0

        thread = threading.Thread(target=self._extract_thread, daemon=True)
        thread.start()

    def _extract_thread(self):
        fmt = self.fmt_var.get()
        br = self.br_var.get()
        fmt_info = AUDIO_FORMATS[fmt]
        codec = fmt_info["codec"]
        ext = fmt_info["ext"]

        total = len(self.video_files)
        success = 0
        failed = []

        for i, video_path in enumerate(self.video_files):
            src_dir = os.path.dirname(video_path)
            stem = Path(video_path).stem
            out_path = os.path.join(src_dir, f"{stem}{ext}")

            # 处理重名
            counter = 1
            while os.path.exists(out_path):
                out_path = os.path.join(src_dir, f"{stem}_{counter}{ext}")
                counter += 1

            cmd = [
                self.ffmpeg_path, "-y",
                "-i", video_path,
                "-vn",              # 不要视频流
                "-c:a", codec,
            ]
            if fmt != "wav" and fmt != "flac":
                cmd += ["-b:a", br]
            cmd.append(out_path)

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if result.returncode == 0:
                    success += 1
                else:
                    failed.append(os.path.basename(video_path))
            except subprocess.TimeoutExpired:
                failed.append(f"{os.path.basename(video_path)} (超时)")
            except Exception as e:
                failed.append(f"{os.path.basename(video_path)} ({e})")

            # 更新进度
            self.root.after(0, lambda v=i+1: self.progress.configure(value=v))
            self.root.after(0, lambda s=success, t=i+1:
                self.lbl_status.configure(text=f"处理中... {s}/{t}"))

        self.root.after(0, self._on_extract_done, success, failed, total)

    def _on_extract_done(self, success: int, failed: list, total: int):
        self.processing = False
        self.btn_extract.configure(state="normal", text="开始提取音频")
        self.progress["value"] = 0

        msg = f"提取完成：{success}/{total} 成功"
        if failed:
            msg += f"\n失败 {len(failed)} 个：\n" + "\n".join(f"  - {f}" for f in failed[:15])
        self.lbl_status.config(text=msg.split("\n")[0], fg=COLOR_GREEN if not failed else COLOR_WARN)
        messagebox.showinfo("提取完成", msg)


# ============================================================================
# 入口
# ============================================================================

def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    AudioExtractApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

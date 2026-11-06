"""Windows desktop preview. Network and disk work never run on the Tk thread."""

import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from queue import Empty
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .desktop_service import BackgroundJobs, DesktopService, DownloadOptions, SearchRequest, SOURCES


APP_TITLE = "dv365-music-downloader · 技术预发布"
PREVIEW_VERSION = "0.1.0-preview"
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "dv365-music-downloader"
LEGACY_DATA_DIR = DATA_DIR.parent / "MusicDLPreview"
BG, INK, MUTED, ACCENT, NAVY = "#f3f5fa", "#17243d", "#65738c", "#6257e8", "#14213b"


class MusicDesktop:
    def __init__(self, root, service=None, settings_path=None):
        self.root = root
        self.service = service or DesktopService()
        self.settings_path = Path(settings_path) if settings_path else DATA_DIR / "settings.json"
        self.jobs = BackgroundJobs()
        self.active = False
        self.closing = False
        self.songs = []
        self.saved_paths = {}
        self.inputs = []
        self.download_records = []
        self.query = tk.StringVar(root)
        self.mode = tk.StringVar(root, "关键词")
        self.limit = tk.StringVar(root, "10")
        self.filters = tk.StringVar(root)
        self.directory = tk.StringVar(root, str(Path.home() / "Music" / "dv365-music-downloader"))
        self.lyrics = tk.BooleanVar(root, False)
        self.cover = tk.BooleanVar(root, False)
        self.sources = {name: tk.BooleanVar(root, name == "netease") for name in SOURCES}
        self.status = tk.StringVar(root, "准备就绪 · 输入歌名或歌手，开始搜索")
        self.count = tk.StringVar(root, "搜索结果")
        self.load_settings()
        root.title(APP_TITLE)
        width = min(1180, max(900, root.winfo_screenwidth() - 80))
        height = min(800, max(600, root.winfo_screenheight() - 100))
        root.geometry("%dx%d" % (width, height))
        root.minsize(min(980, width), min(720, height))
        root.configure(bg=BG)
        # A transparent window icon avoids both branding and Tk's default logo.
        self._window_icon = tk.PhotoImage(master=root, width=1, height=1)
        root.iconphoto(True, self._window_icon)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.report_callback_exception = self.callback_error
        self.build_ui()
        root.after(80, self.poll)

    def build_ui(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background="white")
        style.configure("TLabel", background=BG, foreground=INK, font=("Microsoft YaHei UI", 10))
        style.configure("Card.TLabel", background="white")
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 22, "bold"))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(12, 8))
        style.configure("Accent.TButton", background=ACCENT, foreground="white", borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#5147cb"), ("disabled", "#bbc0d4")])
        style.configure("TEntry", padding=8, font=("Microsoft YaHei UI", 11))
        style.configure("TCombobox", padding=6, font=("Microsoft YaHei UI", 10))
        style.configure("TCheckbutton", background="white", font=("Microsoft YaHei UI", 10))
        style.configure("Treeview", rowheight=38, font=("Microsoft YaHei UI", 10),
                        background="white", fieldbackground="white", foreground=INK, borderwidth=0)
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 10, "bold"),
                        background="#e9edf5", foreground=MUTED, padding=8)
        style.map("Treeview", background=[("selected", "#e5e2ff")], foreground=[("selected", INK)])
        style.configure("TProgressbar", background=ACCENT, troughcolor="#e5e9f2", borderwidth=0)

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        side = tk.Frame(self.root, bg=NAVY, width=180)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        tk.Label(side, text="MUSIC\nDL", fg="white", bg=NAVY, font=("Segoe UI", 28, "bold"),
                 justify="left", anchor="w").pack(fill="x", padx=26, pady=(30, 4))
        tk.Label(side, text="DESKTOP PREVIEW", fg="#a8b8d4", bg=NAVY,
                 font=("Segoe UI", 8)).pack(anchor="w", padx=26, pady=(0, 35))
        for title, action in (("音乐搜索", lambda: self.show_view("results")),
                              ("下载记录", lambda: self.show_view("history")),
                              ("打开保存目录", self.open_directory), ("关于与许可", self.about)):
            tk.Button(side, text=title, command=action, bg="#203150", fg="white",
                      activebackground="#324367", activeforeground="white", relief="flat",
                      anchor="w", padx=18, pady=12, font=("Microsoft YaHei UI", 10)).pack(fill="x", padx=14, pady=4)
        tk.Label(side, text="0.1.0 PREVIEW\n授权待核实\n仅供技术评估", fg="#a8b8d4", bg=NAVY,
                 font=("Microsoft YaHei UI", 9), justify="left").pack(side="bottom", anchor="w", padx=26, pady=24)

        main = ttk.Frame(self.root, padding=(24, 22))
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(4, weight=1)
        ttk.Label(main, text="发现音乐，整理你的收藏", style="Title.TLabel").grid(row=0, sticky="w")
        ttk.Label(main, text="聚合搜索  /  选择下载  /  本地保存", style="Muted.TLabel").grid(row=1, sticky="w", pady=(4, 16))

        card = ttk.Frame(main, style="Card.TFrame", padding=16)
        card.grid(row=2, sticky="ew")
        card.columnconfigure(1, weight=1)
        mode = ttk.Combobox(card, textvariable=self.mode, values=("关键词", "单曲链接", "歌单链接"), width=10, state="readonly")
        mode.grid(row=0, column=0, padx=(0, 10))
        query = ttk.Entry(card, textvariable=self.query)
        query.grid(row=0, column=1, sticky="ew")
        query.bind("<Return>", lambda event: self.search() if not self.active else None)
        self.search_button = ttk.Button(card, text="搜索音乐", command=self.search, style="Accent.TButton")
        self.search_button.grid(row=0, column=2, padx=(10, 0))
        self.inputs.extend([mode, query, self.search_button])
        source_row = ttk.Frame(card, style="Card.TFrame")
        source_row.grid(row=1, column=0, columnspan=3, sticky="w", pady=(14, 10))
        for name, label in SOURCES.items():
            control = ttk.Checkbutton(source_row, text=label, variable=self.sources[name])
            control.pack(side="left", padx=(0, 14))
            self.inputs.append(control)
        options = ttk.Frame(card, style="Card.TFrame")
        options.grid(row=2, column=0, columnspan=3, sticky="ew")
        ttk.Label(options, text="每源数量", style="Card.TLabel").pack(side="left")
        number = ttk.Combobox(options, textvariable=self.limit, values=("5", "10", "20", "50"), width=4, state="readonly")
        number.pack(side="left", padx=(8, 16))
        ttk.Label(options, text="过滤条件", style="Card.TLabel").pack(side="left")
        filters = ttk.Entry(options, textvariable=self.filters, width=21)
        filters.pack(side="left", padx=8)
        ttk.Label(options, text="如 size>3,length<300", style="Card.TLabel", foreground=MUTED).pack(side="left")
        self.inputs.extend([number, filters])

        storage = ttk.Frame(main, padding=(0, 14))
        storage.grid(row=3, sticky="ew")
        storage.columnconfigure(1, weight=1)
        ttk.Label(storage, text="保存到").grid(row=0, column=0, padx=(0, 10))
        ttk.Entry(storage, textvariable=self.directory, state="readonly").grid(row=0, column=1, sticky="ew")
        browse = ttk.Button(storage, text="选择目录", command=self.choose_directory)
        browse.grid(row=0, column=2, padx=(8, 0))
        self.inputs.append(browse)

        self.views = ttk.Frame(main)
        self.views.grid(row=4, sticky="nsew")
        self.views.columnconfigure(0, weight=1)
        self.views.rowconfigure(0, weight=1)
        self.result_view = ttk.Frame(self.views)
        self.history_view = ttk.Frame(self.views)
        for view in (self.result_view, self.history_view):
            view.grid(row=0, column=0, sticky="nsew")
            view.columnconfigure(0, weight=1)
            view.rowconfigure(1, weight=1)
        ttk.Label(self.result_view, textvariable=self.count).grid(row=0, sticky="w", pady=(0, 10))
        self.results = self.make_tree(self.result_view, ("title", "singer", "size", "duration", "source", "status"),
                                     ("歌名", "歌手", "大小", "时长", "来源", "状态"), (230, 150, 85, 85, 90, 100))
        self.results.bind("<Double-1>", lambda event: self.open_selected())
        ttk.Label(self.history_view, text="本次会话的下载记录 · 双击成功记录打开文件").grid(row=0, sticky="w", pady=(0, 10))
        self.history = self.make_tree(self.history_view, ("name", "status", "path"),
                                     ("文件", "结果", "保存位置 / 失败原因"), (250, 85, 470))
        self.history.bind("<Double-1>", lambda event: self.open_history())
        self.history_paths = {}
        self.show_view("results")

        actions = ttk.Frame(main, padding=(0, 12))
        actions.grid(row=5, sticky="ew")
        self.download_button = ttk.Button(actions, text="下载选中歌曲", style="Accent.TButton", command=self.download)
        self.download_button.pack(side="left")
        ttk.Button(actions, text="全选", command=lambda: self.results.selection_set(self.results.get_children())).pack(side="left", padx=8)
        ttk.Button(actions, text="打开已下载文件", command=self.open_selected).pack(side="left")
        for title, variable in (("歌词", self.lyrics), ("封面", self.cover)):
            button = ttk.Checkbutton(actions, text=title, variable=variable)
            button.pack(side="left", padx=(14, 0))
            self.inputs.append(button)
        self.cancel_button = ttk.Button(actions, text="取消任务", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="right")
        self.download_button.configure(state="disabled")

        self.progress = ttk.Progressbar(main, maximum=100)
        self.progress.grid(row=6, sticky="ew")
        ttk.Label(main, textvariable=self.status, wraplength=880).grid(row=7, sticky="w", pady=(8, 7))
        self.log = tk.Text(main, height=3, bg="#e9edf5", fg=MUTED, relief="flat",
                           font=("Microsoft YaHei UI", 9), padx=8, pady=5, state="disabled")
        self.log.grid(row=8, sticky="ew")
        self.write_log("第三方音乐源为实验功能；搜到歌曲不代表平台提供下载权限。")
        query.focus_set()

    def make_tree(self, parent, columns, labels, widths):
        tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="extended")
        tree.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)
        for key, label, width in zip(columns, labels, widths):
            tree.heading(key, text=label)
            tree.column(key, width=width, minwidth=55, stretch=key in ("title", "name", "path"))
        tree.tag_configure("success", foreground="#16784b")
        tree.tag_configure("error", foreground="#bb3f44")
        return tree

    def show_view(self, name):
        (self.result_view if name == "results" else self.history_view).tkraise()

    def start_job(self, operation, kind):
        if self.active:
            return
        self.active = True
        for widget in self.inputs:
            widget.state(["disabled"])
        self.download_button.state(["disabled"])
        self.cancel_button.state(["!disabled"])
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)
        self.jobs.start(operation, kind)

    def search(self):
        if self.active:
            return
        try:
            request = SearchRequest(self.query.get().strip(), tuple(k for k, v in self.sources.items() if v.get()),
                                    int(self.limit.get()), {"关键词": "keyword", "单曲链接": "single", "歌单链接": "playlist"}[self.mode.get()],
                                    self.filters.get())
            request.validate()
        except (ValueError, KeyError) as exc:
            self.notify(str(exc))
            return
        self.status.set("正在查询音乐源，界面可继续操作；可取消当前任务…")
        self.show_view("results")
        self.start_job(lambda event, emit: self.service.search(request, event), "search_result")

    def download(self):
        if self.active:
            return
        selected = [(int(key), self.songs[int(key)]) for key in self.results.selection()]
        if not selected:
            self.notify("请先选中要下载的歌曲，可按 Ctrl / Shift 多选")
            return
        options = DownloadOptions(self.directory.get(), self.lyrics.get(), self.cover.get())
        self.status.set("正在准备下载 %d 首歌曲…" % len(selected))
        self.start_job(lambda event, emit: self.service.download(selected, options, event, emit), "download_result")

    def poll(self):
        try:
            for _ in range(200):
                kind, payload = self.jobs.events.get_nowait()
                self.handle_event(kind, payload)
        except Empty:
            pass
        if self.closing and not self.active:
            self.save_settings()
            self.root.destroy()
            return
        self.root.after(80, self.poll)

    def handle_event(self, kind, payload):
        if kind == "search_result":
            self.songs = payload.songs
            self.saved_paths = {}
            self.results.delete(*self.results.get_children())
            for index, song in enumerate(self.songs):
                self.results.insert("", "end", iid=str(index), values=(song.title, song.singer,
                                    "%.2f MB" % float(song.size or 0) if song.size else "未知", song.duration or "未知",
                                    SOURCES.get(song.source.lower(), song.source), "待选择"))
            self.count.set("搜索结果 · %d 首" % len(self.songs))
            self.status.set("找到 %d 首歌曲 · 选择后下载%s" % (len(self.songs), "；部分来源失败，见下方提示" if payload.warnings else ""))
            if not self.songs:
                self.status.set("未找到可用结果，请更换关键词、音乐源或减少过滤条件")
            for warning in payload.warnings:
                self.write_log(warning)
        elif kind == "download_started":
            index, name = payload
            self.results.set(str(index), "status", "下载中")
            self.status.set("正在下载：" + name)
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)
        elif kind == "progress":
            done, total = payload
            if total:
                self.progress.configure(value=min(100, done / total * 100))
            else:
                self.status.set("下载中 · 已收到 %.2f MB（来源未提供总大小）" % (done / 1048576))
        elif kind == "download_finished":
            key = str(payload["index"])
            success = bool(payload["path"])
            self.results.set(key, "status", "已下载" if success else "失败，可重试")
            self.results.item(key, tags=("success" if success else "error",))
            if success:
                self.saved_paths[key] = payload["path"]
            record_key = self.history.insert("", "end", values=(payload["name"], "成功" if success else "失败",
                                                             payload["path"] or payload["error"]),
                                              tags=("success" if success else "error",))
            self.history_paths[record_key] = payload["path"]
            self.download_records.append(payload)
            for warning in payload["warnings"]:
                self.write_log(warning)
            if not success:
                self.write_log(payload["name"] + "：" + payload["error"])
        elif kind == "download_result":
            successes = sum(bool(item["path"]) for item in payload)
            self.status.set("下载完成 · 成功 %d / 失败 %d · 失败项可重新选择下载" % (successes, len(payload) - successes))
        elif kind == "error":
            self.notify(payload)
        elif kind == "finished":
            self.active = False
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)
            for widget in self.inputs:
                widget.state(["!disabled"])
            self.cancel_button.state(["disabled"])
            self.download_button.state(["!disabled"] if self.songs else ["disabled"])
            if payload:
                self.status.set("任务已取消 · 已完成的下载文件保留")
                for key in self.results.get_children():
                    if self.results.set(key, "status") == "下载中":
                        self.results.set(key, "status", "已取消")

    def cancel(self):
        self.jobs.cancel()
        self.cancel_button.state(["disabled"])
        self.status.set("正在取消… 等待当前网络请求结束")

    def notify(self, text):
        self.status.set(text)
        self.write_log(text)

    def write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        if int(self.log.index("end-1c").split(".")[0]) > 150:
            self.log.delete("1.0", "20.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def choose_directory(self):
        directory = filedialog.askdirectory(parent=self.root, initialdir=str(Path(self.directory.get()).parent))
        if directory:
            self.directory.set(directory)

    def open_path(self, path):
        try:
            if not path or not Path(path).exists():
                self.notify("文件不存在，或所选歌曲尚未下载成功")
                return
            os.startfile(str(path))
        except OSError as exc:
            self.notify("无法打开文件：%s" % exc)

    def open_selected(self):
        selection = self.results.selection()
        if selection:
            self.open_path(self.saved_paths.get(selection[0], ""))

    def open_history(self):
        selection = self.history.selection()
        if selection:
            self.open_path(self.history_paths.get(selection[0], ""))

    def open_directory(self):
        try:
            folder = Path(self.directory.get())
            folder.mkdir(parents=True, exist_ok=True)
            self.open_path(folder)
        except OSError as exc:
            self.notify("保存目录不可用：%s" % exc)

    def about(self):
        messagebox.showinfo("关于与许可", "dv365-music-downloader " + PREVIEW_VERSION +
                            "\n\nWindows 技术预发布版，仅供技术评估。\n保留项目原始 LICENSE 与 README 商用限制说明。"
                            "\n软件授权冲突及音乐来源的商业授权尚未核实。\n不提供付费歌曲权限绕过。"
                            "\n\n配置与崩溃日志保存在：\n" + str(DATA_DIR) +
                            "\n第三方许可见交付目录中的 THIRD_PARTY_NOTICES.txt。", parent=self.root)

    def load_settings(self):
        try:
            settings_path = self.settings_path
            if settings_path == DATA_DIR / "settings.json" and not settings_path.exists():
                settings_path = LEGACY_DATA_DIR / "settings.json"
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return
            if isinstance(data.get("directory"), str) and data["directory"]:
                self.directory.set(data["directory"])
            if str(data.get("limit", "")) in ("5", "10", "20", "50"):
                self.limit.set(str(data["limit"]))
            for key in ("lyrics", "cover"):
                if isinstance(data.get(key), bool):
                    getattr(self, key).set(data[key])
            selected = data.get("sources")
            if isinstance(selected, list) and any(key in SOURCES for key in selected):
                for key, variable in self.sources.items():
                    variable.set(key in selected)
        except (OSError, ValueError, TypeError):
            pass

    def save_settings(self):
        data = {"directory": self.directory.get(), "limit": self.limit.get(), "lyrics": self.lyrics.get(),
                "cover": self.cover.get(), "sources": [key for key, variable in self.sources.items() if variable.get()]}
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.settings_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.settings_path)
        except OSError:
            logging.getLogger(__name__).warning("无法保存桌面设置")

    def close(self):
        if self.active and not messagebox.askyesno("任务仍在进行", "取消当前任务并退出？\n已完成的文件会保留。", parent=self.root):
            return
        self.closing = True
        if self.active:
            self.cancel()

    def callback_error(self, exc_type, value, traceback):
        logging.getLogger(__name__).error("桌面操作异常", exc_info=(exc_type, value, traceback))
        self.notify("操作未完成：" + str(value))


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(DATA_DIR / "desktop.log", maxBytes=524288, backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.WARNING, handlers=[handler], format="%(asctime)s %(levelname)s %(name)s %(message)s")
    root = tk.Tk()
    MusicDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()

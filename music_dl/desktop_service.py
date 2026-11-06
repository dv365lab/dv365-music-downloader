"""Serial desktop jobs; all UI communication goes through an event queue."""

from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue, Full
import threading

from . import config
from .exceptions import CancelledError, DownloadError
from .filters import filter_songs, parse_filter
from .source import MusicSource


SOURCES = {"netease": "网易云", "qq": "QQ 音乐", "kugou": "酷狗", "migu": "咪咕", "baidu": "百度（历史源）"}


@dataclass(frozen=True)
class SearchRequest:
    text: str
    sources: tuple = ("netease",)
    limit: int = 10
    mode: str = "keyword"
    filters: str = ""

    def validate(self):
        if not self.text.strip():
            raise ValueError("请先输入歌名、歌手或链接")
        if self.mode not in ("keyword", "single", "playlist"):
            raise ValueError("查询类型无效")
        if not 1 <= self.limit <= 50:
            raise ValueError("每个来源的搜索数量须为 1–50")
        if self.mode == "keyword" and (not self.sources or any(s not in SOURCES for s in self.sources)):
            raise ValueError("请至少选择一个有效音乐源")
        parse_filter(self.filters)


@dataclass(frozen=True)
class DownloadOptions:
    outdir: str
    lyrics: bool = False
    cover: bool = False


@dataclass
class SearchResult:
    songs: list
    warnings: list = field(default_factory=list)


class DesktopService:
    def search(self, request, cancel_event):
        request.validate()
        config.init()
        config.set("keyword", request.text if request.mode == "keyword" else "")
        config.set("number", request.limit)
        config.set("cancel_event", cancel_event)
        source = MusicSource()
        if request.mode == "single":
            song = source.single(request.text)
            if song is None:
                raise DownloadError("无法获取歌曲，请检查网易云单曲链接或音乐源状态")
            songs = [song]
        elif request.mode == "playlist":
            songs = source.playlist(request.text)
            if not songs:
                raise DownloadError("无法获取歌单，请检查网易云 / 酷狗歌单链接或音乐源状态")
        else:
            songs = source.search(request.text, request.sources)
        if cancel_event.is_set():
            raise CancelledError("操作已取消")
        return SearchResult(filter_songs(songs, request.filters),
                            ["%s：%s" % (SOURCES.get(name, name), error) for name, error in source.errors])

    def download(self, selected, options, cancel_event, emit):
        output = Path(options.outdir).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        config.set("outdir", str(output))
        config.set("lyrics", options.lyrics)
        config.set("cover", options.cover)
        config.set("cancel_event", cancel_event)
        results = []
        try:
            for index, song in selected:
                if cancel_event.is_set():
                    break
                display_name = "%s - %s" % (song.singer, song.title)
                emit("download_started", (index, display_name))
                config.set("progress_callback", lambda done, total: emit("progress", (done, total)))
                song._fullname = ""  # Resolve against this job's directory, not an earlier search.
                try:
                    saved = song.download()
                    if not saved or not Path(saved).is_file() or Path(saved).stat().st_size == 0:
                        raise DownloadError("音乐源未提供可用下载链接；请在平台确认歌曲是否可下载")
                    record = {"index": index, "name": Path(saved).name, "path": saved,
                              "error": "", "warnings": list(song.download_warnings)}
                except CancelledError:
                    break
                except Exception as exc:
                    record = {"index": index, "name": display_name, "path": "",
                              "error": str(exc) or type(exc).__name__, "warnings": []}
                results.append(record)
                emit("download_finished", record)
            return results
        finally:
            config.set("progress_callback", None)


class BackgroundJobs:
    def __init__(self):
        self.events = Queue(maxsize=512)
        self.busy = False
        self.cancel_event = threading.Event()
        self.thread = None

    def emit(self, kind, payload=None):
        if kind == "progress":
            try:
                self.events.put_nowait((kind, payload))
            except Full:
                pass
        else:
            self.events.put((kind, payload))

    def start(self, operation, result_kind):
        if self.busy:
            raise RuntimeError("请等待当前任务完成")
        self.busy = True
        self.cancel_event = threading.Event()

        def work():
            try:
                result = operation(self.cancel_event, self.emit)
                if not self.cancel_event.is_set():
                    self.emit(result_kind, result)
            except CancelledError:
                self.cancel_event.set()
            except Exception as exc:
                self.emit("error", str(exc) or type(exc).__name__)
            finally:
                self.busy = False
                self.emit("finished", self.cancel_event.is_set())

        self.thread = threading.Thread(target=work, name="dv365-music-downloader-desktop", daemon=True)
        self.thread.start()

    def cancel(self):
        self.cancel_event.set()

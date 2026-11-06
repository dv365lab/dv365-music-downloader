import time
import gc
import tkinter as tk

from music_dl.desktop import MusicDesktop
from music_dl.desktop_service import SearchResult
from music_dl.song import BasicSong


def test_gui_search_and_download_use_background_jobs(tmp_path):
    class FakeService:
        def search(self, request, cancel):
            song = BasicSong()
            song.title, song.singer = "测试歌曲", "测试歌手"
            song.source = "netease"
            song.size = 3
            return SearchResult([song], ["测试来源提示"])

        def download(self, selected, options, cancel, emit):
            saved = tmp_path / "测试歌曲.mp3"
            saved.write_bytes(b"test audio")
            record = {"index": 0, "name": saved.name, "path": str(saved), "error": "", "warnings": []}
            emit("download_started", (0, saved.name))
            emit("progress", (10, 10))
            emit("download_finished", record)
            return [record]

    root = tk.Tk()
    root.withdraw()
    try:
        app = MusicDesktop(root, service=FakeService(), settings_path=tmp_path / "settings.json")
        app.query.set("测试")
        app.search()

        def settle():
            deadline = time.monotonic() + 5
            while app.active and time.monotonic() < deadline:
                root.update()
                time.sleep(0.01)
            assert not app.active

        settle()
        assert len(app.results.get_children()) == 1
        assert "1" in app.status.get()
        app.results.selection_set("0")
        app.download()
        settle()
        assert len(app.history.get_children()) == 1
        assert app.saved_paths["0"].endswith("测试歌曲.mp3")
        assert "成功 1" in app.status.get()
        app.save_settings()
        assert (tmp_path / "settings.json").is_file()
    finally:
        root.destroy()
        root.report_callback_exception = lambda *args: None
        del app
        gc.collect()  # Tk variables must be finalized on the UI thread, not a later HTTP worker.

"""PyInstaller entry point, with a report-writing startup check for release QA."""

import json
import sys
import tkinter as tk
from pathlib import Path
import gc
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import tempfile
import threading
import wave

from music_dl.desktop import MusicDesktop, main, PREVIEW_VERSION


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        report = Path(sys.argv[2])
        try:
            from music_dl import config
            config.init()
            from music_dl.addons.netease import NeteaseApi
            from music_dl.addons import qq, kugou, migu, baidu
            assert NeteaseApi.encrypted_request({"ids": [1]})["params"]
            root = tk.Tk()
            root.withdraw()
            app = MusicDesktop(root, settings_path=report.with_suffix(".settings.json"))
            root.update()
            root.destroy()
            root.report_callback_exception = lambda *args: None
            del app
            gc.collect()
            from music_dl.song import BasicSong
            from music_dl.desktop_service import DesktopService, DownloadOptions
            audio = BytesIO()
            with wave.open(audio, "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(8000)
                output.writeframes(b"\x00\x00" * 800)
            payload = audio.getvalue()

            class AudioHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/wav")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)

                def log_message(self, *args):
                    pass

            server = ThreadingHTTPServer(("127.0.0.1", 0), AudioHandler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                with tempfile.TemporaryDirectory() as directory:
                    song = BasicSong()
                    song.title, song.singer, song.ext = "Startup test", "dv365-music-downloader", "wav"
                    song.song_url = "http://127.0.0.1:%d/sample.wav" % server.server_port
                    records = DesktopService().download([(0, song)], DownloadOptions(directory), threading.Event(), lambda *args: None)
                    assert records[0]["path"], records
                    assert hashlib.sha256(Path(records[0]["path"]).read_bytes()).digest() == hashlib.sha256(payload).digest()
            finally:
                server.shutdown()
                server.server_close()
                worker.join(2)
            report.write_text(json.dumps({"ok": True, "version": PREVIEW_VERSION,
                                           "checks": ["tk", "desktop_widgets", "provider_imports", "AES", "RSA", "local_http_download", "sha256_audio_match"]}), encoding="utf-8")
        except Exception as exc:
            report.write_text(json.dumps({"ok": False, "error": repr(exc)}), encoding="utf-8")
            raise
    else:
        main()

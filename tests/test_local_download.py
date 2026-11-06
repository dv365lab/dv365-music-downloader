"""Real HTTP smoke test using only this repository's bundled audio sample."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

import pytest

from music_dl import config
from music_dl.song import BasicSong
from music_dl.exceptions import DownloadError


@pytest.fixture
def audio_server():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    sample_dir = Path(__file__).resolve().parents[1] / "static"
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(sample_dir)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:%d" % server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_real_download_matches_sample_and_preserves_duplicate(audio_server, tmp_path):
    config.init()
    config.set("outdir", str(tmp_path / "new-directory"))
    sample = Path(__file__).resolve().parents[1] / "static" / "sample.mp3"
    outputs = []
    for _ in range(2):
        song = BasicSong()
        song.title, song.singer = "本地测试", "示例"
        song.song_url = audio_server + "/sample.mp3"
        outputs.append(Path(song.download()))
    assert outputs[0] != outputs[1]
    assert all(path.read_bytes() == sample.read_bytes() for path in outputs)
    assert not list(tmp_path.rglob("*.part"))


def test_real_http_404_creates_no_music(audio_server, tmp_path):
    config.init()
    with pytest.raises(DownloadError, match="404"):
        BasicSong()._download_file(audio_server + "/missing.mp3", str(tmp_path / "bad.mp3"), True)
    assert not list(tmp_path.iterdir())

import threading
from unittest.mock import Mock, patch

import pytest
import requests
from click.testing import CliRunner

from music_dl import config, main
from music_dl.song import BasicSong


@pytest.fixture(autouse=True)
def reset_config(tmp_path):
    config.init()
    config.set("outdir", str(tmp_path))


def response(chunks=(b"audio",), status=200, length="5", content_type="audio/mpeg"):
    result = Mock()
    result.headers = requests.structures.CaseInsensitiveDict(
        {"Content-Length": length, "Content-Type": content_type}
    )
    result.iter_content.return_value = iter(chunks)
    result.raise_for_status.side_effect = requests.HTTPError("404") if status == 404 else None
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    return result


def test_http_error_is_not_saved_as_music(tmp_path):
    target = tmp_path / "song.mp3"
    with patch("music_dl.song.requests.get", return_value=response(status=404)):
        with pytest.raises(Exception, match="404"):
            BasicSong()._download_file("https://example.test/song", str(target), True)
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_interrupted_download_preserves_existing_file(tmp_path):
    target = tmp_path / "song.mp3"
    target.write_bytes(b"original")
    reply = response()

    def broken_stream():
        yield b"partial"
        raise requests.ConnectionError("connection lost")

    reply.iter_content.return_value = broken_stream()
    with patch("music_dl.song.requests.get", return_value=reply):
        with pytest.raises(Exception, match="connection lost"):
            BasicSong()._download_file("https://example.test/song", str(target), True)
    assert target.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [target]


def test_download_without_content_length(tmp_path):
    target = tmp_path / "song.mp3"
    reply = response(length="")
    with patch("music_dl.song.requests.get", return_value=reply) as request:
        BasicSong()._download_file("https://example.test/song", str(target), True)
    assert target.read_bytes() == b"audio"
    assert request.call_args.kwargs["timeout"]
    reply.close.assert_called_once()


def test_html_error_is_rejected(tmp_path):
    with patch("music_dl.song.requests.get", return_value=response(content_type="text/html")):
        with pytest.raises(Exception, match="HTML|网页"):
            BasicSong()._download_file("https://example.test/song", str(tmp_path / "song.mp3"), True)
    assert not list(tmp_path.iterdir())


def test_truncated_download_is_rejected(tmp_path):
    with patch("music_dl.song.requests.get", return_value=response(length="100")):
        with pytest.raises(Exception, match="不完整|incomplete"):
            BasicSong()._download_file("https://example.test/song", str(tmp_path / "song.mp3"), True)
    assert not list(tmp_path.iterdir())


def test_cancelled_download_leaves_no_partial_file(tmp_path):
    event = threading.Event()
    event.set()
    config.set("cancel_event", event)
    with patch("music_dl.song.requests.get", return_value=response()):
        with pytest.raises(Exception, match="取消|cancel"):
            BasicSong()._download_file("https://example.test/song", str(tmp_path / "song.mp3"), True)
    assert not list(tmp_path.iterdir())


def test_invalid_filter_is_friendly_cli_error():
    with patch("music_dl.__main__.MusicSource.search", return_value=[]):
        result = CliRunner().invoke(main, ["-k", "test", "--filter", "size>abc"])
    assert result.exit_code == 2
    assert "filter" in result.output
    assert not isinstance(result.exception, ValueError)


def test_unavailable_single_is_friendly_cli_error():
    with patch("music_dl.__main__.MusicSource.single", return_value=None):
        result = CliRunner().invoke(main, ["-u", "https://music.163.com/song?id=1"])
    assert result.exit_code == 1
    assert "无法获取" in result.output
    assert not isinstance(result.exception, AttributeError)


def test_version_works_with_editable_install():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "3.0.1" in result.output


def test_song_without_size_can_be_displayed():
    assert BasicSong().row


def test_out_of_range_selection_is_rejected_before_allocating_range():
    song = BasicSong()
    song.title, song.size = "Test", 3
    with patch("music_dl.__main__.MusicSource.search", return_value=[song]):
        result = CliRunner().invoke(main, ["-k", "test"], input="0-1000000000\n")
    assert result.exit_code == 2
    assert "超出范围" in result.output


def test_cancel_during_optional_files_preserves_successful_audio(tmp_path):
    from music_dl.exceptions import CancelledError
    song = BasicSong()
    song._song_url = "https://example.test/song"
    config.set("lyrics", True)
    target = tmp_path / "good.mp3"
    target.write_bytes(b"audio")
    with patch.object(song, "download_song", return_value=str(target)), patch.object(song, "download_lyrics", side_effect=CancelledError("取消")):
        assert song.download() == str(target)
    assert song.download_warnings
    assert target.read_bytes() == b"audio"


def test_midstream_cancel_removes_partial_download(tmp_path):
    event = threading.Event()
    config.set("cancel_event", event)
    reply = response()

    def chunks():
        yield b"first"
        event.set()
        yield b"second"

    reply.iter_content.return_value = chunks()
    with patch("music_dl.song.requests.get", return_value=reply):
        with pytest.raises(Exception, match="取消"):
            BasicSong()._download_file("https://example.test/song", str(tmp_path / "cancel.mp3"), True)
    assert not list(tmp_path.iterdir())


def test_migu_missing_album_and_cover_are_supported():
    from music_dl.addons.migu import MiguApi, search
    data = {"songResultData": {"result": [{"id": "1", "name": "Test", "singers": [], "albums": [], "imgItems": [], "rateFormats": []}]}}
    with patch.object(MiguApi, "request", return_value=data):
        songs = search("Test")
    assert len(songs) == 1
    assert songs[0].album == ""
    assert songs[0].cover_url == ""

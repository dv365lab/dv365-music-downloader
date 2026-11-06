import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from music_dl import config
from music_dl.desktop_service import BackgroundJobs, DesktopService, DownloadOptions, SearchRequest
from music_dl.filters import filter_songs
from music_dl.song import BasicSong


def make_song(size=0, seconds=0):
    song = BasicSong()
    song.title, song.singer = "Test", "Artist"
    song.size = size
    song.duration = seconds
    return song


@pytest.mark.parametrize("search_request", [SearchRequest(""), SearchRequest("x", ()),
                                         SearchRequest("x", limit=0), SearchRequest("x", filters="size>oops")])
def test_search_validation(search_request):
    with pytest.raises(ValueError):
        search_request.validate()


def test_production_filters_use_song_metadata():
    songs = [make_song(2, 100), make_song(10, 250), make_song(8, 350), make_song()]
    assert filter_songs(songs, "size>3,length<300") == [songs[1], songs[3]]


def test_search_preserves_partial_results_and_source_errors():
    config.init()
    song = make_song()
    with patch("music_dl.desktop_service.MusicSource") as factory:
        factory.return_value.search.return_value = [song]
        factory.return_value.errors = [("qq", "接口不可用")]
        result = DesktopService().search(SearchRequest("test"), threading.Event())
    assert result.songs == [song]
    assert result.warnings == ["QQ 音乐：接口不可用"]


def test_download_reports_failure_and_continues(tmp_path):
    config.init()
    bad, good = make_song(), make_song()
    saved = tmp_path / "valid.mp3"
    saved.write_bytes(b"audio")
    with patch.object(bad, "download", return_value=None), patch.object(good, "download", return_value=str(saved)):
        result = DesktopService().download([(0, bad), (1, good)], DownloadOptions(str(tmp_path)),
                                           threading.Event(), lambda *args: None)
    assert result[0]["error"]
    assert result[1]["path"] == str(saved)


def test_jobs_return_promptly_and_disallow_overlapping_work():
    jobs = BackgroundJobs()
    release = threading.Event()

    def slow_operation(cancel, emit):
        release.wait(5)
        return "complete"

    jobs.start(slow_operation, "result")
    assert jobs.busy
    with pytest.raises(RuntimeError):
        jobs.start(slow_operation, "result")
    release.set()
    jobs.thread.join(5)
    assert not jobs.thread.is_alive()
    assert list(jobs.events.queue) == [("result", "complete"), ("finished", False)]


def test_cancel_discards_late_search_results():
    jobs = BackgroundJobs()
    release = threading.Event()
    jobs.start(lambda cancel, emit: release.wait(5), "result")
    jobs.cancel()
    release.set()
    jobs.thread.join(5)
    assert list(jobs.events.queue) == [("finished", True)]


def test_source_url_requires_real_provider_hostname():
    from music_dl.source import MusicSource
    from music_dl.exceptions import ParameterError
    with pytest.raises(ParameterError):
        MusicSource().single("https://example.test/?url=163.com/song?id=1")


def test_bad_extension_is_an_item_failure_not_a_batch_crash(tmp_path):
    config.init()
    bad, good = make_song(), make_song()
    bad.ext = "../invalid"
    saved = tmp_path / "good.mp3"
    saved.write_bytes(b"audio")
    with patch.object(good, "download", return_value=str(saved)):
        results = DesktopService().download([(0, bad), (1, good)], DownloadOptions(str(tmp_path)),
                                            threading.Event(), lambda *args: None)
    assert results[0]["error"]
    assert results[1]["path"] == str(saved)

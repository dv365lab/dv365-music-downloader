from music_dl import config
from music_dl.song import BasicSong


def test_song_metadata_and_safe_paths(tmp_path):
    config.init()
    config.set("outdir", str(tmp_path))
    song = BasicSong()
    song.title = 'test/track:*?"<>|'
    song.singer = r"test\artist"
    song.duration = 28
    assert song.title == "testtrack"
    assert song.singer == "testartist"
    assert song.duration == "0:00:28"
    assert song.song_fullname == str(tmp_path / "testartist - testtrack.mp3")
    assert song.cover_fullname == str(tmp_path / "testartist - testtrack.jpg")
    assert song.lyrics_fullname == str(tmp_path / "testartist - testtrack.lrc")
    assert not song.available

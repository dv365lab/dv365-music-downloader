#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: HJK
@file: test_main
@time: 2019-01-30
"""
import click
from click.testing import CliRunner
from music_dl import __main__ as m
from music_dl import config
from unittest.mock import patch
from music_dl.song import BasicSong


def test_run():
    config.init()
    song = BasicSong()
    song.title, song.singer, song.source, song.size = "Test", "Artist", "netease", 3
    with patch.object(m.MusicSource, "search", return_value=[song]), patch.object(song, "download") as download:
        result = CliRunner().invoke(m.main, ["-k", "test"], input="N\n")
    assert result.exit_code == 0
    assert "Test" in result.output
    download.assert_not_called()


def test_main():
    result = CliRunner().invoke(m.main, ["-k", "test", "-u", "https://music.163.com/song?id=1"])
    assert result.exit_code == 2
    assert "只能选择一种" in result.output

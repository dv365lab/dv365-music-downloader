#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: HJK
@file: basic.py
@time: 2019-05-07
"""

"""
    Basic song object
"""

import os
import re
import datetime
import logging
import click
import requests
import tempfile
from pathlib import Path
from . import config
from .utils import colorize
from .exceptions import DownloadError, CancelledError


class BasicSong:
    """
        Define the basic properties and methods of a song.
        Such as title, name, singer etc.
    """

    def __init__(self):
        self.idx = 0
        self.id = 0
        self._title = ""
        self._singer = ""
        self.ext = "mp3"
        self.album = ""
        self.size = 0
        self.rate = ""
        self._duration = ""
        self.source = ""
        self._song_url = ""
        # self.song_file = ""
        self.cover_url = ""
        # self.cover_file = ""
        self.lyrics_url = ""
        self.lyrics_text = ""
        # self.lyrics_file = ""
        self._fullname = ""
        self.logger = logging.getLogger(__name__)
        self.download_warnings = []

    def __repr__(self):
        """ Abstract of the song """
        source = colorize("%s" % self.source.upper(), self.source)
        return "%s #%s %s-%s-%s \n %s \n" % (
            source,
            self.id,
            self.title,
            self.singer,
            self.album,
            self.song_url,
        )

    def __str__(self):
        """ Song details """
        source = colorize("%s" % self.source.upper(), self.source)
        return _(
            " -> Source: {source} #{id}\n"
            " -> Title: {title}\n"
            " -> Singer: {singer}\n"
            " -> Album: {album}\n"
            " -> Duration: {duration}\n"
            " -> Size: {size}MB\n"
            " -> Bit Rate: {rate}\n"
            " -> Song URL: {song_url}\n"
            " -> Lyrics URL: {lyrics_url}\n"
            " -> Cover URL: {cover_url}\n"
        ).format(
            source=source,
            id=self.id,
            title=self.title,
            singer=self.singer,
            album=self.album,
            duration=self.duration,
            size=self.size,
            rate=self.rate,
            song_url=self.song_url,
            lyrics_url=self.lyrics_url,
            cover_url=self.cover_url,
        )

    @property
    def available(self) -> bool:
        """ Not available when url is none or size equal 0 """
        return bool(self.song_url)

    @property
    def name(self) -> str:
        """ Song file name """
        if not re.fullmatch(r"[a-zA-Z0-9]{1,8}", self.ext):
            raise DownloadError("音乐源返回了无效的文件扩展名")
        base = ("%s - %s" % (self.singer, self.title)).strip(" .")[:180].rstrip(" .") or "未命名歌曲"
        return "%s.%s" % (base, self.ext)

    @property
    def duration(self):
        """ 持续时间 H:M:S """
        return self._duration

    @duration.setter
    def duration(self, seconds):
        self._duration = str(datetime.timedelta(seconds=int(seconds)))

    @property
    def song_url(self) -> str:
        return self._song_url

    @song_url.setter
    def song_url(self, url):
        """ Set song url and update size. """
        self._song_url = ""
        if not url:
            return
        self._check_cancel()
        r = None
        try:
            r = requests.get(
                url,
                stream=True,
                headers=config.get("wget_headers"),
                proxies=config.get("proxies"),
                timeout=config.get("timeout") or (5, 10),
            )
            r.raise_for_status()
            if "text/html" in r.headers.get("Content-Type", "").lower():
                raise DownloadError("音乐源返回了网页，未提供可用音频")
            if r.headers.get("Content-Length") == "0":
                return
            size = int(r.headers.get("Content-Length") or 0)
            # 转换成MB并保留两位小数
            self.size = round(size / 1048576, 2)
            self._song_url = url
        except (requests.RequestException, ValueError) as e:
            raise DownloadError("无法获取音乐链接：%s" % e) from e
        finally:
            if r is not None:
                r.close()

    @property
    def row(self) -> list:
        """ Song details in list form """

        def highlight(s, k):
            return s.replace(k, colorize(k, "xiami")).replace(
                k.title(), colorize(k.title(), "xiami")
            )

        ht_singer = self.singer if len(self.singer) < 30 else self.singer[:30] + "..."
        ht_title = self.title if len(self.title) < 30 else self.title[:30] + "..."
        ht_album = self.album if len(self.album) < 20 else self.album[:20] + "..."

        if config.get("keyword"):
            keywords = re.split(r";|,|\s|\*", config.get("keyword"))
            for k in keywords:
                if not k:
                    continue
                ht_singer = highlight(ht_singer, k)
                ht_title = highlight(ht_title, k)
                ht_album = highlight(ht_album, k)

        size = "%sMB" % self.size
        ht_size = size if float(self.size or 0) < 8 else colorize(size, "flac")

        return [
            colorize(self.idx, "baidu"),
            ht_title,
            ht_singer,
            ht_size,
            self.duration,
            ht_album,
            self.source.upper(),
        ]


    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        value = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", str(value or ""))
        self._title = value

    @property
    def singer(self):
        return self._singer

    @singer.setter
    def singer(self, value):
        value = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", str(value or ""))
        self._singer = value

    def _set_fullname(self):
        """ Full name without suffix, to resolve file name conflicts"""
        outdir = os.path.abspath(config.get("outdir") or ".")
        os.makedirs(outdir, exist_ok=True)
        base, ext = os.path.splitext(self.name)
        candidate = base
        index = 1
        while os.path.exists(os.path.join(outdir, candidate + ext)):
            candidate = "%s (%d)" % (base, index)
            index += 1
        self._fullname = os.path.join(outdir, candidate)

    @property
    def song_fullname(self):
        if not self._fullname:
            self._set_fullname()
        return self._fullname + "." + self.ext

    @property
    def lyrics_fullname(self):
        if not self._fullname:
            self._set_fullname()
        return self._fullname + ".lrc"

    @property
    def cover_fullname(self):
        if not self._fullname:
            self._set_fullname()
        return self._fullname + ".jpg"

    def _download_file(self, url, outfile, stream=False):
        """
            Helper function for download
        :param url:
        :param outfile:
        :param stream: need process bar or not
        :return:
        """
        if not url:
            raise DownloadError("音乐源未提供可用的下载链接")
        self._check_cancel()
        target = Path(outfile)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        r = None
        try:
            r = requests.get(
                url,
                stream=True,
                headers=config.get("wget_headers"),
                proxies=config.get("proxies"),
                timeout=config.get("timeout") or (5, 10),
            )
            r.raise_for_status()
            content_type = r.headers.get("Content-Type", "").lower()
            if stream and any(kind in content_type for kind in ("text/html", "application/json", "text/plain")):
                raise DownloadError("音乐源返回了 HTML 网页或错误信息，未保存为音乐")
            length = r.headers.get("Content-Length", "")
            total_size = int(length) if length and str(length).isdigit() else 0
            callback = config.get("progress_callback")
            fd, temporary = tempfile.mkstemp(prefix=target.name + ".", suffix=".part", dir=target.parent)
            received = 0
            with os.fdopen(fd, "wb") as output:
                for chunk in r.iter_content(chunk_size=65536):
                    self._check_cancel()
                    if chunk:
                        output.write(chunk)
                        received += len(chunk)
                        if callback and stream:
                            callback(received, total_size)
            self._check_cancel()
            if not received:
                raise DownloadError("下载内容为空")
            if total_size and received != total_size:
                raise DownloadError("下载不完整：预期 %d 字节，收到 %d 字节" % (total_size, received))
            os.replace(temporary, target)
            temporary = None
            click.echo(
                _(" :: Saved to: {outfile}").format(
                    outfile=colorize(outfile, "highlight")
                )
            )
            return str(target)
        except (requests.RequestException, OSError) as e:
            raise DownloadError("下载失败：%s" % e) from e
        finally:
            if r is not None:
                r.close()
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)

    @staticmethod
    def _check_cancel():
        event = config.get("cancel_event")
        if event and event.is_set():
            raise CancelledError("操作已取消")

    def _save_lyrics_text(self):
        with open(self.lyrics_fullname, "w", encoding="utf-8") as f:
            f.write(self.lyrics_text)
            click.echo(
                _(" :: Saved to: {outfile}").format(
                    outfile=colorize(self.lyrics_fullname, "highlight")
                )
            )

    def download_song(self):
        if self.song_url:
            return self._download_file(self.song_url, self.song_fullname, stream=True)
        else:
            raise DownloadError("音乐源未提供可用下载链接，歌曲可能需要平台授权或接口已变更")

    def download_lyrics(self):
        if self.lyrics_url:
            self._download_file(self.lyrics_url, self.lyrics_fullname, stream=False)

    def download_cover(self):
        if self.cover_url:
            self._download_file(self.cover_url, self.cover_fullname, stream=False)

    def download(self):
        """ Main download function """
        click.echo("===============================================================")
        if config.get("verbose"):
            click.echo(str(self))
        else:
            click.echo(" | ".join(self.row))

        result = self.download_song()
        self.download_warnings = []
        for enabled, action in ((config.get("lyrics"), self.download_lyrics), (config.get("cover"), self.download_cover)):
            if enabled:
                try:
                    action()
                except CancelledError:
                    self.download_warnings.append("歌词 / 封面已取消，音频文件已保存")
                    break
                except Exception as exc:
                    self.download_warnings.append("附加文件未完成：%s" % exc)
                    self.logger.warning(self.download_warnings[-1])

        click.echo("===============================================================\n")
        return result

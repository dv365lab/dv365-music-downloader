#!/usr/bin/env python
# -*- coding:utf-8 _*-
"""
@author: HJK
@file: main.py
@time: 2019-01-08
"""

import sys
import os
import re
import gettext
import click
import logging
import prettytable as pt
from . import config
from .utils import colorize
from .source import MusicSource
from .filters import filter_songs, parse_filter
from .__version__ import __version__

gettext.install("music-dl", "locale")


def play_music(files):
    from .player import play_music as play
    return play(files)


def menu(songs_list):
    # 创建table
    tb = pt.PrettyTable()
    tb.field_names = ["序号", "歌名", "歌手", "大小", "时长", "专辑", "来源"]
    # 遍历输出搜索列表
    songs_list.sort(key=lambda x: x.size)
    for index, song in enumerate(songs_list):
        song.idx = index
        tb.add_row(song.row)
        # click.echo(song.info)
    tb.align = "l"
    click.echo(tb)
    click.echo("")

    # 用户指定下载序号
    prompt = (
        _("请输入{下载序号}，支持形如 {numbers} 的格式，输入 {N} 跳过下载").format(
            下载序号=colorize(_("下载序号"), "yellow"),
            numbers=colorize("0 3-5 8", "yellow"),
            N=colorize("N", "yellow"),
        )
        + "\n >>"
    )

    choices = click.prompt(prompt)

    while not re.match(r"^((\d+\-\d+)|(\d+)|\s+)+$", choices):
        if choices.lower() == "n":
            return
        choices = click.prompt("%s%s" % (colorize(_("输入有误!"), "red"), prompt))

    click.echo("")
    selected_list = []
    downloaded_files = []
    
    for choice in choices.split():
        start, to, end = choice.partition("-")
        if int(start) >= len(songs_list) or (end and int(end) >= len(songs_list)):
            raise click.BadParameter("下载序号超出范围")
        if end and int(end) < int(start):
            raise click.BadParameter("下载序号范围必须由小到大")
        if end:
            selected_list += range(int(start), int(end) + 1)
        else:
            selected_list.append(int(start))

    if any(idx < 0 or idx >= len(songs_list) for idx in selected_list):
        raise click.BadParameter("下载序号超出范围")
    for idx in dict.fromkeys(selected_list):
        song = songs_list[idx]
        try:
            result = song.download()
            if result:
                downloaded_files.append(result)
            else:
                click.echo("该音乐源未提供可用下载链接", err=True)
        except RuntimeError as exc:
            click.echo("下载失败：%s" % exc, err=True)

    # 如果启用了播放功能，则播放下载的音乐
    if config.get("play") and downloaded_files:
        play_music(downloaded_files)


def run():
    ms = MusicSource()
    while config.get("keyword"):
        songs_list = ms.search(config.get("keyword"), config.get("source").split())
        songs_list = filter_songs(songs_list, config.get("filter"))
        if songs_list:
            menu(songs_list)
        else:
            click.echo("未找到可用结果，请更换关键词或音乐源。")
        config.set("keyword", click.prompt(_("请输入要搜索的歌曲，或Ctrl+C退出") + "\n >>"))
    if config.get("playlist"):
        songs_list = ms.playlist(config.get("playlist"))
        if songs_list:
            menu(songs_list)
        else:
            raise click.ClickException("无法获取歌单或歌单为空")
    elif config.get("url"):
        song = ms.single(config.get("url"))
        if song is None:
            raise click.ClickException("无法获取歌曲，请检查链接或音乐源状态")
        result = song.download()
        if config.get("play") and result:
            play_music([result])


@click.command()
@click.version_option(version=__version__, prog_name="dv365-music-downloader")
@click.option("-k", "--keyword", help=_("搜索关键字，歌名和歌手同时输入可以提高匹配（如 空帆船 朴树）"))
@click.option("-u", "--url", default="", help=_("通过指定的歌曲URL下载音乐"))
@click.option("-p", "--playlist", default="", help=_("通过指定的歌单URL下载音乐"))
@click.option(
    "-s",
    "--source",
    # default="qq netease kugou baidu",
    help=_("支持的数据源: ") + "netease qq kugou migu baidu（历史接口）",
)
@click.option("-n", "--number", type=click.IntRange(1, 50), default=5, help=_("搜索数量限制"))
@click.option("-o", "--outdir", default=".", help=_("指定输出目录"))
@click.option("-x", "--proxy", default="", help=_("指定代理（如http://127.0.0.1:1087）"))
@click.option("-v", "--verbose", default=False, is_flag=True, help=_("详细模式"))
@click.option("--lyrics", default=False, is_flag=True, help=_("同时下载歌词"))
@click.option("--cover", default=False, is_flag=True, help=_("同时下载封面"))
@click.option("--nomerge", default=False, is_flag=True, help=_("不对搜索结果列表排序和去重"))
@click.option("--filter", default="", help=_("过滤条件，如'size>8,length>300'表示大于8MB且时长超过5分钟"))
@click.option("--play", default=False, is_flag=True, help=_("下载完成后播放音乐"))
def main(
    keyword,
    url,
    playlist,
    source,
    number,
    outdir,
    proxy,
    verbose,
    lyrics,
    cover,
    nomerge,
    filter,
    play,
):
    """
        Search and download music from netease, qq, kugou, baidu and xiami.
        Example: dv365-music-downloader -k "周杰伦"
    """
    try:
        parse_filter(filter)
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="--filter") from exc
    selected_modes = sum([bool(keyword), bool(url), bool(playlist)])
    if selected_modes > 1:
        raise click.UsageError("搜索关键字、单曲链接和歌单链接只能选择一种")
    if selected_modes == 0:
        # click.echo(_("ERROR: 必须指定搜索关键字、歌曲的URL或歌单的URL中的一个") + "\n", err=True)
        # ctx = click.get_current_context()
        # click.echo(ctx.get_help())
        # ctx.exit()
        keyword = click.prompt(_("搜索关键字，歌名和歌手同时输入可以提高匹配（如 空帆船 朴树）") + "\n >>")

    # 初始化全局变量
    config.init()
    config.set("keyword", keyword)
    config.set("url", url)
    config.set("playlist", playlist)
    if source:
        config.set("source", source)
    config.set("number", min(number, 50))
    config.set("outdir", outdir)
    config.set("verbose", verbose)
    config.set("lyrics", lyrics)
    config.set("cover", cover)
    config.set("nomerge", nomerge)
    config.set("filter", filter)
    config.set("play", play)
    if proxy:
        proxies = {"http": proxy, "https": proxy}
        config.set("proxies", proxies)

    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)-8s | %(name)s: %(message)s ",
        datefmt="%H:%M:%S",
    )

    try:
        run()
    except (EOFError, KeyboardInterrupt, click.Abort):
        return
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    main()

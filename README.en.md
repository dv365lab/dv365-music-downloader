# dv365-music-downloader: Listen to what you want



**dv365-music-downloader** is a command line tool which helps you search and download music from multiple sources.

Support for QQ music, Netease music, Xiami music, Kugou music and Baidu music. See [supported sources](#supported-sources).

**Python3 Only. Python 3.5+ Recommended.**

English | [中文文档](README.md)

> Note: Some music sources may not be available in your region. Configure a proxy only where permitted by local laws and platform rules.
- Support for lossless music
- Search for high-quality music with priority ( flac -> 320K -> 128K )
- Support for HTTP and SOCKS proxy
- Support for multithreading searching
- Support for merging and sorting results
- Support keyword highlighting
- Support for filtering search results by file size and song duration (using `--filter` parameter)
- Support for auto-play after downloading (using `--play` parameter)
- Player supports common controls: space to pause/resume, left/right to switch songs, ,/. to move 5 seconds backward/forward, q to quit
- While playing, press d to delete songs you don't like (removes from disk and playlist)

## Installation

Install using pip (Recommended)

```bash
$ pip3 install -e .
```

Manual

```bash
$ cd dv365-music-downloader
$ python3 setup.py install
```

Use directly

```bash
$ cd dv365-music-downloader
$ pip3 install -r requirements.txt
$ ./dv365-music-downloader

# OR python3 dv365-music-downloader
```

## Usage

```
$ dv365-music-downloader --help
Usage: dv365-music-downloader [OPTIONS]

  Search and download music from netease, qq, kugou, baidu and xiami.
  Example: dv365-music-downloader -k "Bruno Mars"

Options:
  --version            Show the version and exit.
  -k, --keyword TEXT   Query keyword
  -s, --source TEXT    Support for qq netease kugou baidu xiami flac
  -c, --count INTEGER  Searching count limit (default: 5)
  -o, --outdir TEXT    Output dir (default: current dir)
  -x, --proxy TEXT     Set proxy (like http://127.0.0.1:1087)
  -m, --merge          Sort and merge
  -v, --verbose        Verbose mode
  --lyrics              Download lyrics
  --cover               Download cover image
  --nomerge             Don't sort and merge search results
  --filter TEXT         Filter search results by file size and song duration
  --play                Enable auto-play after downloading
  --help               Show this message and exit.
```

- Default search sources are `qq netease kugou baidu`, with a limit of 5 results each, and the save directory is the current directory.
- When specifying numbers, you can use formats like `1-5 7 10`.
- By default, search results are sorted and deduplicated. Sorting is based on artist and song name, and when both are the same, the largest file is kept.
- Lossless music tracks are limited in number. If lossless is not available, 320K or 128K will be displayed.
- HTTP and SOCKS proxies are supported, in formats like `-x http://127.0.0.1:1087` or `-x socks5://127.0.0.1:1086`.

- Attributes supported by filter include:
  - `size`: File size in MB
  - `length`: Song duration in seconds

- Operators supported by filter include:
  - `>`: Greater than
  - `<`: Less than
  - `=`: Equal to

  ```bash
  dv365-music-downloader -k --filter "size>8" # Only show songs larger than 8MB
  dv365-music-downloader -k --filter "size<3" # Only show songs smaller than 3MB
  dv365-music-downloader -k --filter "length>300" # Only show songs longer than 5 minutes
  dv365-music-downloader -k --filter "length>180,length<300" # Only show songs between 3-5 minutes
  dv365-music-downloader -k --filter "size>3,size<8,length>240" # Only show songs between 3-8MB and longer than 4 minutes
  ```



## Supported sources

| Music sources             | Abbreviation | Websites                  |
| ------------------------- | ------------ | ------------------------- |
| QQ Music                  | qq           | <https://y.qq.com/>       |
| Kugou Music               | kugou        | <http://www.kugou.com/>   |
| Netease Music             | netease      | <https://music.163.com/>  |
| Baidu Music               | baidu        | <http://music.baidu.com/> |
| Xiami Music               | xiami        | <https://www.xiami.com/>  |
| Lossless Music From Baidu | flac         | <http://music.baidu.com/> |

Welcome to submit plugins to support more music sources! Refer to the files in `extractors`.



## Credits

Thanks to the developers of requests, you-get, music, and NeteaseCloudMusicFlac for their ideas.

## LICENSE

[MIT License](LICENSE)

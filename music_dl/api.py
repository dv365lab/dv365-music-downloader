#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: HJK
@file: api.py
@time: 2019-06-11
"""

import requests
from . import config
from .exceptions import RequestError, ResponseError, DataError, CancelledError


class MusicApi:
    # class property
    # 子类修改时使用deepcopy
    session = requests.Session()
    session.headers.update(config.get("fake_headers"))
    if config.get("proxies"):
        session.proxies.update(config.get("proxies"))
    session.headers.update({"referer": "http://www.google.com/"})

    @classmethod
    def request(cls, url, method="POST", data=None):
        resp = cls.requestInstance(url, method, data)
        try:
            try:
                result = resp.json()
            except ValueError as exc:
                raise ResponseError("音乐源返回了非 JSON 数据，接口可能已变更") from exc
            if not isinstance(result, dict):
                raise DataError("音乐源返回了无法识别的数据结构")
            return result
        finally:
            resp.close()

    @classmethod
    def requestInstance(cls, url, method="POST", data=None):
        event = config.get("cancel_event")
        if event and event.is_set():
            raise CancelledError("操作已取消")
        cls.session.proxies.clear()
        if config.get("proxies"):
            cls.session.proxies.update(config.get("proxies"))
        try:
            if method == "GET":
                resp = cls.session.get(url, params=data, timeout=config.get("timeout") or (5, 10))
            else:
                resp = cls.session.post(url, data=data, timeout=config.get("timeout") or (5, 10))
        except requests.RequestException as exc:
            raise RequestError("音乐源连接失败或超时") from exc
        if resp.status_code != requests.codes.ok:
            resp.close()
            raise RequestError("音乐源返回 HTTP %s" % resp.status_code)
        if not resp.text:
            resp.close()
            raise ResponseError("音乐源未返回数据")
        if event and event.is_set():
            resp.close()
            raise CancelledError("操作已取消")
        return resp

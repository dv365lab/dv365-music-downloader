"""Validated filters shared by the command line and desktop interfaces."""

import math
import re

from .utils import time_duration_to_seconds


def parse_filter(expression):
    conditions = []
    for part in expression.split(","):
        if not part.strip():
            continue
        match = re.fullmatch(r"\s*(size|length)\s*([<>=])\s*(\d+(?:\.\d+)?)\s*", part)
        if not match:
            raise ValueError("过滤条件格式错误，请使用 size>3,length<300（大小 MB，时长秒）")
        field, operator, value = match.groups()
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("过滤数值必须为有限的非负数")
        conditions.append((field, operator, value))
    return conditions


def filter_songs(songs, expression):
    conditions = parse_filter(expression)

    def matches(song):
        for field, operator, target in conditions:
            raw = song.size if field == "size" else song.duration
            if not raw:
                continue  # Unknown metadata is retained, as in the original CLI.
            actual = float(raw) if field == "size" else time_duration_to_seconds(raw)
            if operator == ">" and actual <= target:
                return False
            if operator == "<" and actual >= target:
                return False
            if operator == "=" and abs(actual - target) >= (0.01 if field == "size" else 0.000001):
                return False
        return True

    return [song for song in songs if matches(song)]

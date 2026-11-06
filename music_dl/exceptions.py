#!/usr/bin/env python
# -*- coding:utf-8 _*-
"""
@author: HJK
@file: exceptions.py
@time: 2019-01-09

自定义异常

"""


class RequestError(RuntimeError):
    """ 请求时的状态码错误 """



class ResponseError(RuntimeError):
    """ 得到的response状态错误 """



class DataError(RuntimeError):
    """ 得到的data中没有预期的内容 """



class ParameterError(RuntimeError):
    """ 输入的参数错误 """



class DownloadError(RuntimeError):
    """A download could not be completed and must not be reported as successful."""


class CancelledError(RuntimeError):
    """The user cancelled the current operation."""

# coding=utf-8
import sys
import traceback


def trace():
    """
    用于输出异常的堆栈信息
    :return: 异常的堆栈信息
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()
    error_str = ""
    for e in traceback.format_exception(exc_type, exc_value, exc_traceback):
        error_str += e

    return error_str

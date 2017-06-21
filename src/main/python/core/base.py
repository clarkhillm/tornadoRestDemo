# coding=utf-8
import abc
import types


class ECloudException(Exception):
    msg = "An unknown exception occurred."
    code = 500
    args = []

    def __init__(self, message=None, args=None):
        self.code = self.code
        self.args = args

        if not message:
            message = self.msg
        super(ECloudException, self).__init__(message)

    def format_message(self):
        return self.args[0]


class ToDict(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def to_dict(self):
        raise NotImplementedError()


class AllFiledToDict(ToDict):
    """
    用于mixin的一种基类，包含一个方法可以把类序列化成dict。
    """

    def to_dict(self):
        rs = {}
        for k, v in self.__dict__.items():
            if isinstance(v, types.FunctionType):
                pass
            elif isinstance(v, types.ClassType):
                if isinstance(v, AllFiledToDict):
                    rs[k] = v.to_dict()
            else:
                rs[k] = v

        return rs

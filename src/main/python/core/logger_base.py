import types
import base

__author__ = 'cuigang@easted.com.cn'

system_log_level = 'DEBUG'

system_log_format = (
    '%(asctime)s <%(process)d-%(processName)s> %(filename)s(line:%(lineno)d)'
    ' - [%(levelname)s] - %(message)s'
)


class LoggerHandler(base.ToDict):
    def __init__(self):
        self.class_name = 'logging.StreamHandler'
        self.level = system_log_level

    def to_dict(self):
        rs = {}
        for k, v in self.__dict__.items():
            if isinstance(v, types.FunctionType):
                pass
            else:
                if k == 'class_name':
                    k = 'class'
                rs[k] = v
        return rs


class LoggerFormatter(base.AllFiledToDict):
    def __init__(self):
        self.format = system_log_format


class Loggers(base.AllFiledToDict):
    def __init__(self):
        self.level = system_log_level
        self.handlers = []
        self.propagate = False


class LoggerConfig(object):
    def __init__(self):
        self.handlers = {}

    def add_handler(self, handler, logger, formatter):
        self.handlers[handler.__name__] = handler.to_dict()
        for k, v in self.__dict__.items():
            if formatter == v:
                self.handlers[handler.__name__]['formatter'] = k
        logger.handlers.append(handler.__name__)
        return self

    def get_dict_config(self):
        rs = {
            'version': 1,
            'handlers': self.handlers,
            'formatters': {},
            'loggers': {}
        }
        for k, v in self.__dict__.items():
            if isinstance(v, Loggers):
                rs['loggers'][k] = v.to_dict()
            if isinstance(v, LoggerFormatter):
                rs['formatters'][k] = v.to_dict()

        return rs

import logger_base as log

__author__ = 'cuigang@easted.com.cn'


class SystemFormat(log.LoggerFormatter):
    pass


class SyslogFormat(log.LoggerFormatter):
    def __init__(self):
        super(SyslogFormat, self).__init__()
        self.format = '%(message)s'


class TimedRotatingFileHandler(log.LoggerHandler):
    __name__ = 'ecloud_handler'

    def __init__(self):
        super(TimedRotatingFileHandler, self).__init__()
        self.class_name = "core.logger_handler.TimedRotatingFileHandler"
        self.when = 'midnight'
        self.interval = 1
        self.backupCount = 3650


class ErrorHandler(TimedRotatingFileHandler):
    __name__ = 'error_handler'

    def __init__(self):
        super(ErrorHandler, self).__init__()
        self.level = 'ERROR'

from core.logger import TimedRotatingFileHandler, SystemFormat
from core.logger_base import LoggerConfig, Loggers

__all__ = [
    'ecloud_config'
]

log_dir = '/var/log'
region_name = 'DEMO'


class SystemLogger(Loggers):
    pass


class EcloudHandler(TimedRotatingFileHandler):
    def __init__(self):
        super(EcloudHandler, self).__init__()
        self.filename = '%s/tornado_%s.log' % (
            log_dir, region_name
        )


class WebLogConfig(LoggerConfig):
    def __init__(self):
        super(WebLogConfig, self).__init__()
        self.system = SystemLogger()
        self.system_format = SystemFormat()


ecloud_config = WebLogConfig()
ecloud_config.add_handler(
    EcloudHandler(),
    ecloud_config.system,
    ecloud_config.system_format
)

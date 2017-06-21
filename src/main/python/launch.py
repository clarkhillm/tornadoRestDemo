# coding=utf-8
import importlib
import logging.config
import os
import sys

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

import logger
from core import rest
from handlers import handlers

logging.config.dictConfig(logger.ecloud_config.get_dict_config())

LOG = logging.getLogger('system')

try:
    service_modules_name = [_.split('.')[0] for _ in os.listdir('./ws')
                            if _.split('.')[0] != '__init__']

    service_modules_name = list(set(service_modules_name))

    modules = []
    for m in service_modules_name:
        ws_module = importlib.import_module('ws.' + m)
        modules.append(getattr(ws_module, 'Service'))

    settings = {
        'debug': 'DEBUG',
        'gzip': True,
        'autoreload': True,
        'autoescape': None
    }
    application = rest.RestService(modules, **settings)

    application.add_handlers(r".*", handlers)

    server = HTTPServer(application)

    LOG.debug('--service start---')
    server.bind(8888)
    server.start()

    IOLoop.instance().start()

except KeyboardInterrupt:
    print  # 特意保留一个空行，以便和之前的输出区分
    print "Stop the easted service..."
    LOG.debug('--service stopped---')
    IOLoop.instance().stop()
    sys.exit(-1)

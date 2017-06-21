import logging
from tornado import gen

from core.rest import get, RestHandler

__author__ = 'cuigang@easted.com.cn'

LOG = logging.getLogger('system')


class Service(RestHandler):
    @gen.coroutine
    @get(_path="/test")
    def test(self):
        LOG.debug('call test ...')
        raise gen.Return('test ...')

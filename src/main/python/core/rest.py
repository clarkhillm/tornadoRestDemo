# coding=utf-8
import abc
import inspect
import json
import logging
import re
import types

import tornado.web
from tornado import gen
from common import trace

__author__ = 'cuigang@easted.com.cn'

"""
说明
---

此模块负责解析请求的path，并把请求分发给添加对应装饰器的方法。

所有请求的body必须符合json格式。

1. 去除了_required 项。需要方法自己检查参数。或者自己写filter实现。
2. 不再把body作为最后一个参数传递给处理请求的方法。需要从方法的**kwargs参数中获取body。或者
   自己通过self.request.body获取。
3. 提供request filter chain。filter是一个参数为request对象的方法，可以是协程。

被装饰的方法返回值
---
返回一个元组，元组中有两个元素，一个是list类型，一个是整数类型；分别对应响应的data和total。
顺序是无所谓的。

其他形式将作为data直接响应给前台，total设置为1.

"""

__all__ = [
    'get',
    'put',
    'post',
    'delete',
    'RestService',
    'RestHandler'
]

LOG = logging.getLogger('system')

_filter = []
_prepares = []


def add_filter(func):
    assert isinstance(func, types.FunctionType)
    _filter.append(func)


def add_prepare(func):
    assert isinstance(func, types.FunctionType)
    _prepares.append(func)


def config(func, method, **kwparams):
    path = None
    required = None

    if len(kwparams):
        path = kwparams['_path']

    def operation(*args, **kwargs):
        return func(*args, **kwargs)

    operation.func_name = func.__name__
    operation._func_params = inspect.getargspec(func).args[1:]
    operation._service_params = re.findall(r"(?<={)\w+", path)
    operation._service_name = re.findall(r"(?<=/)\w+", path)
    operation._query_params = re.findall(r"(?<=<)\w+", path)
    operation._required = required
    operation._method = method
    operation._path = path

    return operation


def get(*params, **kwparams):
    def method(f):
        return config(f, 'GET', **kwparams)

    return method


def post(*params, **kwparams):
    def method(f):
        return config(f, 'POST', **kwparams)

    return method


def put(*params, **kwparams):
    def method(f):
        return config(f, 'PUT', **kwparams)

    return method


def delete(*params, **kwparams):
    def method(f):
        return config(f, 'DELETE', **kwparams)

    return method


class RestHandler(tornado.web.RequestHandler):
    __metaclass__ = abc.ABCMeta

    def prepare(self):
        for f in _prepares:
            f(self.request)

    @gen.coroutine
    def get(self):
        """ Executes get method """
        yield self._exe('GET')

    @gen.coroutine
    def post(self):
        """ Executes post method """
        yield self._exe('POST')

    @gen.coroutine
    def put(self):
        """ Executes put method"""
        yield self._exe('PUT')

    @gen.coroutine
    def delete(self):
        """ Executes put method"""
        yield self._exe('DELETE')

    @gen.coroutine
    def _exe(self, method):

        res = {
            "success": True,
            "msg": "",
            "result": [],
            "total": 0
        }

        """ Executes the python function for the Rest Service """
        request_path = self.request.path
        path = request_path.split('/')
        services_and_params = list(filter(lambda x: x != '', path))

        # Get all function names configured in the class RestHandler
        functions = list(filter(
            lambda op: hasattr(
                getattr(self, op),
                '_service_name'
            ) is True and inspect.ismethod(
                getattr(self, op)
            ) is True, dir(self)))
        # Get all http methods configured in the class RestHandler
        http_methods = list(
            map(lambda op: getattr(getattr(self, op), '_method'), functions))

        if method not in http_methods:
            raise tornado.web.HTTPError(
                405, 'The service not have %s verb' % method
            )

        for operation in list(map(lambda op: getattr(self, op), functions)):
            service_name = getattr(operation, "_service_name")
            service_params = getattr(operation, "_service_params")

            # If the _types is not specified, assumes str types for the params
            services_from_request = list(
                filter(lambda x: x in path, service_name))

            op_m_eq_req_m = operation._method == self.request.method
            s_name_eq_s_req = service_name == services_from_request
            len_eq = len(service_params) + len(service_name) == len(
                services_and_params)

            if op_m_eq_req_m and s_name_eq_s_req and len_eq:
                try:
                    for f in _filter:
                        yield f(self.request)
                    params_values = self._find_params_value_of_url(
                        service_name,
                        request_path
                    ) + self._find_params_value_of_arguments(operation)

                    p_values = params_values

                    kwargs = {}
                    if self.request.body:
                        if 'application/json' in self.request.headers.get_list(
                                'content-type'):
                            kwargs['body'] = json.loads(self.request.body)

                    rs = yield operation(*p_values, **kwargs)

                    self.response_decorate(rs, res)

                    self.set_header("Content-Type", 'application/json')
                    if not self._finished:
                        self.write(json.dumps(res))
                    else:
                        # 有些情况下需要先finish，这时候应该不需要write，比如下载的时候。
                        LOG.warn('Cannot write() after finish(). boyd:\n %s',
                                 json.dumps(res, indent=4))

                except Exception as detail:
                    self.set_header("Content-Type", 'application/json')
                    LOG.debug("rest frame detail=%s" % detail)
                    LOG.error(trace())
                    res['success'] = False
                    res['msg'] = '%s' % detail
                    self.write(json.dumps(res))
                finally:
                    self.finish()
        self.send_error(404)

    @staticmethod
    def response_decorate(rs, res):
        if rs is None or rs == '':
            res['result'] = []
            res['total'] = 0
        else:
            if is_standard_rs(rs):
                for data in rs:
                    if isinstance(data, types.ListType):
                        res['result'] = data
                    else:
                        res['total'] = data
            elif isinstance(rs, types.ListType):
                res['result'] = rs
                res['total'] = len(rs)
            else:
                res['result'] = [rs]
                res['total'] = 1

    def _find_params_value_of_url(self, services, url):
        """ Find the values of path params """
        values_of_query = list()
        i = 0
        url_split = url.split("/")
        values = [item for item in url_split if
                  item not in services and item != '']
        for v in values:
            if v is not None:
                values_of_query.append(v)
                i += 1
        return values_of_query

    def _find_params_value_of_arguments(self, operation):
        values = []
        if len(self.request.arguments) > 0:
            a = operation._service_params
            b = operation._func_params
            params = [item for item in b if item not in a]
            for p in params:
                if p in self.request.arguments.keys():
                    v = self.request.arguments[p]
                    values.append(v[0])
                else:
                    values.append(None)
        elif len(self.request.arguments) == 0 and len(
                operation._query_params) > 0:
            values = [None] * (
                len(operation._func_params) - len(operation._service_params))
        return values

    def gen_http_error(self, status, msg):
        """ Generates the custom HTTP error """
        self.clear()
        self.set_status(status)
        self.write("<html><body>" + str(msg) + "</body></html>")
        self.finish()

    @classmethod
    def get_services(cls):
        """ Generates the resources (uri) to deploy the Rest Services """
        services = []
        for f in dir(cls):
            o = getattr(cls, f)
            if callable(o) and hasattr(o, '_service_name'):
                services.append(getattr(o, '_service_name'))
        return services

    @classmethod
    def get_paths(cls):
        """
        Generates the resources from path (uri) to deploy the Rest Services
        """
        paths = []
        for f in dir(cls):
            o = getattr(cls, f)
            if callable(o) and hasattr(o, '_path'):
                paths.append(getattr(o, '_path'))
        return paths

    @classmethod
    def get_handlers(cls):
        """ Gets a list with (path, handler) """
        svs = []
        paths = cls.get_paths()
        for p in paths:
            s = re.sub(r"(?<={)\w+}", ".*", p).replace("{", "")
            o = re.sub(
                r"(?<=<)\w+", "", s
            ).replace(
                "<", "").replace(
                ">", "").replace(
                "&", "").replace(
                "?", "")
            svs.append((o, cls))

        return svs


class RestService(tornado.web.Application):
    """ Class to create Rest services in tornado web server """
    resource = None

    def __init__(self, rest_handlers, resource=None, handlers=None,
                 default_host="", transforms=None, **settings):
        restservices = []
        self.resource = resource
        for r in rest_handlers:
            svs = self._generate_rest_services(r)
            restservices += svs
        if handlers is not None:
            restservices += handlers
        tornado.web.Application.__init__(self, restservices, default_host,
                                         transforms, **settings)

    def _generate_rest_services(self, rest):
        svs = []
        paths = rest.get_paths()
        for p in paths:
            s = re.sub(r"(?<={)\w+}", ".*", p).replace("{", "")
            o = re.sub(
                r"(?<=<)\w+", "", s
            ).replace(
                "<", ""
            ).replace(
                ">", ""
            ).replace(
                "&", ""
            ).replace(
                "?", ""
            )
            svs.append((o, rest, self.resource))

        return svs


def is_standard_rs(rs):
    is_tuple = isinstance(rs, types.TupleType)
    is_two_item = len(rs) == 2
    if is_tuple and is_two_item:
        h_li = isinstance(rs[0], types.ListType) or isinstance(rs[1],
                                                               types.ListType)
        h_nu = isinstance(rs[0], types.IntType) or isinstance(rs[1],
                                                              types.IntType)
    else:
        return False
    return is_tuple and is_two_item and h_li and h_nu

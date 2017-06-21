# coding=utf-8
"""
说明
---

此模块提供mysql数据库支持，以及redis数据库支持。

"""
import logging
import re

from tornado import gen
from tornado.ioloop import IOLoop
from tornado_mysql import pools
from tornado_mysql.cursors import DictCursor

from core.common import trace

__author__ = 'cuigang@easted.com.cn'

__CONN_TEMPLATE = (
    'mysql://(?P<user>\w+):(?P<passwd>\w+)@(?P<host>.+):'
    '(?P<port>\d+)/(?P<db>\w+)'
)

__pools = {}

LOG = logging.getLogger('system')


def get_conn(conn):
    connect_kwargs = __reverse_format(__CONN_TEMPLATE, conn)
    connect_kwargs['port'] = int(connect_kwargs['port'])
    connect_kwargs['charset'] = 'utf8'
    connect_kwargs['cursorclass'] = DictCursor

    return connect_kwargs


def __reverse_format(temp, res):
    m = re.match(temp, res)
    if m:
        return m.groupdict()
    return False


def get_pool(url,
             max_idle_connections=1,
             max_recycle_sec=3600):
    """
    获取数据库连接池 
    为每一个URL分配一个连接池，这个连接池是全局的。
    需要配合配置文件工作，配置文件中应该包含如下内容：
    
    ```
    [database]
    max_idle_connections = 1
    max_recycle_sec = 3600
    ```
    
    如果无此配置，则需传递`max_idle_connections`和`max_recycle_sec`参数。
    
    :param int max_idle_connections: Max number of keeping connections.
    :param int max_recycle_sec: How long connections are recycled.
    :param url: 数据库的url，形如：` mysql://root:password@10.10.3.111:3306/ecloud` 
    :return: 数据库连接池实例
    """
    if url not in __pools:
        __pools[url] = pools.Pool(
            get_conn(url),
            max_idle_connections=max_idle_connections,
            max_recycle_sec=max_recycle_sec
        )
    return __pools[url]


class DBUtil(object):
    """
    使用上下文管理协议实现的数据库访问工具，用法：
    
    ```python 
    with DBUtil(dbpools.LOCAL_DB) as db:
        yield self.update_remark(self.body['remark'], db, self.id)
        yield self.update_admin(db, self.id)
        yield self.update_time(db, self.id)
    ```
    
    with ... as ...:下（缩进中）所有的操作，都会被认为是一个事务。
    

    需要配合配置文件工作，配置文件中应该包含如下内容：
    
    ```
    [database]
    max_idle_connections = 1
    max_recycle_sec = 3600
    ```
    
    """

    def __init__(self, url):
        self.db = get_pool(url)
        self.tx = None
        self.curs = []

    @gen.coroutine
    def execute(self, sql, *args):
        if self.tx is None:
            LOG.info('%s %s', sql, args)
            tx = yield self.db.begin()
            self.tx = tx
        cur = yield self.tx.execute(sql, args)
        self.curs.append(cur)
        raise gen.Return(len(cur.fetchall()))

    @gen.coroutine
    def query(self, sql, *args):
        LOG.info('%s %s', sql, args)
        cur = yield self.db.execute(sql, args)
        rs = cur.fetchall()
        if len(rs) > 0:
            raise gen.Return(rs)
        else:
            raise gen.Return([])

    @gen.coroutine
    def q_one(self, sql, *args):
        LOG.info('%s %s', sql, args)
        cur = yield self.db.execute(sql, args)
        raise gen.Return(cur.fetchone())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        def cb(fut):
            try:
                for cur in self.curs:
                    cur.close()
            except BaseException as e:
                LOG.error(str(e))
                LOG.error(trace())
            if fut.exception():
                self.tx._close()
                raise fut.exception()

        if exc_tb is None:
            if self.tx:
                IOLoop.current().add_future(self.tx.commit(), cb)
        else:
            if self.tx:
                IOLoop.current().add_future(self.tx.rollback(), cb)
            raise exc_value

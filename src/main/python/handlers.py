from tornado import web

web_root = '../web'
handlers = [
    (r"/web/(.*)", web.StaticFileHandler, {"path": web_root}),
    (r"/", web.RedirectHandler, dict(url=r"/web/login.html")),
]

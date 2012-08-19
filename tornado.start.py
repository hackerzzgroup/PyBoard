#!/usr/bin/env python
import tornado.ioloop
import tornado.httpserver
import tornado.wsgi
import PyBoard
import sys
import os
def main():
    app = PyBoard.PyBoard()
    container = tornado.wsgi.WSGIContainer(app)
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        logfile = open("application.log", "a+")
        sys.stdout = sys.stderr = logfile
        pid = os.fork()
        if pid != 0:
            sys.__stdout__.write("Successfully forked into the background... PID: {0}\n".format(pid))
            os._exit(0)
    try:
        http_server_a = tornado.httpserver.HTTPServer(container)
        http_server_a.listen(8080, "::1")
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
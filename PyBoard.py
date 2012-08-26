# This file is a part of PyBoard.
# Copyright (c) 2011 - 2012 The Hackerzz Group, Inc.
# All rights reserved.
from __future__ import print_function
import atexit
import imp
import mimetypes
import os
import re
import sys
import threading
import time
import traceback
import urllib
import warnings
from collections import OrderedDict
import PyBoardObjects
import PyBoardFunctions
import PyBoardPages

class PyBoard(object):
    def __init__(self):
        if os.name == "nt":
            self.log("error: Running on a Windows system. Windows is not supported (yet?)", self.LOGLEV_ERROR)
            sys.exit(1)
        t = time.clock()
        if not sys.path[0]:
            sys.path[0] = os.getcwd()
        self.conf = PyBoardObjects.Configuration()
        self.lang = PyBoardObjects.Language(self.conf["Language"])
        self._loggerLock = threading.Lock()
        self.log(self.lang["PB_STARTUP"].format(v=self.conf["__version"]))
        self.set_paths()
        self.func = PyBoardFunctions.Functions(self)
        self.modViews = OrderedDict()
        self.scheduler = PyBoardObjects.TaskScheduler(self).start()
        self.bp = PyBoardPages.BasePages(self)
        self.ap = PyBoardPages.Admin(self)
        self.Extensions, self._extm = [], []
        self.handlers = {}
        self._dbmods = {}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.load_extensions()
        self.load_database()
        self.boards = self.masterDB.get_boards()
        self.modSessions = {}
        if os.path.isfile("{0}/.pbsession".format(self.workd)) and self.conf["SessionPersistence"]:
            try:
                self._loadModSessions()
            except (ValueError, IndexError):
                pass
        mimetypes.init()
        t = time.clock() - t
        atexit.register(self.__del__)
        self.raise_event(PyBoardObjects.Event("PBApplicationLady", cancellable=False))
        self.raise_event(PyBoardObjects.Event("PBApplicationReady", cancellable=False))
        self.log(self.lang["PB_DONE"].format(t="{:03.2f}".format(t)))

    def _loadModSessions(self):
        with open("{0}/.pbsession".format(self.workd), "r") as mf:
            lines = [i.strip() for i in mf.readlines()]
        os.remove("{0}/.pbsession".format(self.workd))
        lines.reverse()
        if lines.pop() != "__pfsessionfile{0}__".format(self.conf["__version"]):
            return
        else:
            while lines:
                recs = lines.pop()
                if recs == "__end__":
                    return
                else:
                    recs = recs.split("\xFF")
                    for session in recs:
                        session = session.split(":")
                        self.modSessions[session[0]] = [session[1], int(session[2]), session[3]]

    def get_module(self, name, identifier):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mod = imp.load_source(identifier, "{0}/lib/{1}.py".format(self.datad, name))
                return mod
        except Exception:
            for line in traceback.format_exc().split("\n"):
                if line.strip():
                    self.log(line, self.LOGLEV_ERROR)
            return 0

    def raise_event(self, event):
        """Generate events for extensions to hook into."""
        if event.name in self.handlers:
            for c in self.handlers[event.name]:
                try:
                    state = self.handlers[event.name][c](event)
                    if not state and event._cancellable:
                        event.cancelled = True
                except event.Cancel as e:
                    if event._cancellable:
                        event.cancelMessage = e
                        return event
                except Exception as e:
                    self.log(self.lang["ERR_IN_EVENT"].format(handler=self.handlers[event.name][c], name=event.name))
                    for line in traceback.format_exc().split("\n"):
                        if line.strip():
                            self.log(line, self.LOGLEV_ERROR)
        return event

    def load_database(self):
        if not self._dbmods:
            self.log(self.lang["ERR_NO_DATABASE"])
            sys.exit(1)
        for ext in self._dbmods:
            for engine in self._dbmods[ext]:
                if engine == self.conf["DatabaseEngine"]:
                    self._databaseImplementor = self._dbmods[ext][engine]
                    self.masterDB = self._databaseImplementor.Global(self)
                    self.log("- Database loaded.")
                    return
        self.log(self.lang["ERR_NO_DATABASE"])
        sys.exit(1)

    def reload_database(self):
        extid = self._databaseImplementor
        del self.boards
        del self.masterDB
        del self._databaseImplementor
        self.load_database()
        self.boards = self.masterDB.get_boards()

    LOGLEV_INFO = 0
    LOGLEV_WARN = 1
    LOGLEV_ERROR = 2

    def log(self, message, loglev=0):
        with self._loggerLock:
            if loglev == 1:
                print(time.strftime("[%H:%M:%S] \033[33;1m[pyboard] {0}\033[0m".format(str(message))), file=sys.stderr)
            elif loglev == 2:
                print(time.strftime("[%H:%M:%S] \033[31;1m[pyboard] {0}\033[0m".format(str(message))), file=sys.stderr)
            elif loglev == 52346:
                print(time.strftime("[%H:%M:%S] \033[32m[pyboard]\033[0m \033[33m{0}\033[0m".format(str(message))))
            else:
                print(time.strftime("[%H:%M:%S] \033[32m[pyboard]\033[0m {0}".format(str(message))))

    def log_except(self, thread_name, t, v, b):
        self.log("*** [SERVER ERROR] ***********************", self.LOGLEV_ERROR)
        self.log("Exception in thread '{0}':".format(thread_name), self.LOGLEV_ERROR)
        for line in traceback.format_tb(b):
            for l in line.split("\n"):
                if l.strip():
                    self.log(l, self.LOGLEV_ERROR)
        self.log(traceback.format_exception_only(t, v)[0].strip(), self.LOGLEV_ERROR)
        self.log("******************************************", self.LOGLEV_ERROR)

    def load_extensions(self):
        self.log(self.lang["PB_EXTENSION_LOAD_START"])
        for i in os.listdir(self.workd+"/extensions"):
            if i.split(".")[-1] == "py" and i not in self.conf["ExtensionBlacklist"]:
                self.load_extension(i)
        self.log(self.lang["PB_EXTENSION_LOAD_DONE"].format(n=len(self.Extensions), s="s" if len(self.Extensions) > 1 or not self.Extensions else ""))

    def load_extension(self, i):
        self.log(self.lang["PB_IMPORTING_EXTENSION"].format(file=i))
        try:
            self._extm.append(imp.load_source("extensions.{0}".format("-".join(i.split(".")[:-1])), self.workd+"/extensions/{0}".format(i)))
        except Exception as e:
            self.log(self.lang["PB_INVALID_EXTENSION"].format(f=i, m=str(e)), self.LOGLEV_ERROR)
            for line in traceback.format_exc().split("\n"):
                if line.strip():
                    self.log(line, self.LOGLEV_ERROR)
            return 0
        try:
            if not self._extm[-1].main.IDENTIFIER or self._extm[-1].main.IDENTIFIER == "net.pyboard.BaseExtension":
                del self._extm[-1]
                self.log(self.lang["PB_MISSING_IDENTIFIER"].format(e=i), self.LOGLEV_ERROR)
            elif self._extm[-1].main.IDENTIFIER in self.ext_identifiers:
                del self._extm[-1]
                self.log(self.lang["PB_IDENTIFIER_CONFLICT"].format(i=self._extm[-1].main.IDENTIFIER), self.LOGLEV_ERROR)
            else:
                self.log(self.lang["PB_INIT_EXTENSION_CLASS"].format(id=self._extm[-1].main.IDENTIFIER))
                try:
                    self.Extensions.append(self._extm[-1].main(self))
                except:
                    self.log("Error encountered while loading {id}'s main class:".format(id=self._extm[-1].main.IDENTIFIER), self.LOGLEV_ERROR)
                    for line in traceback.format_exc().split("\n"):
                        if line.strip():
                            self.log(line, self.LOGLEV_ERROR)
        except Exception as e:
            del self._extm[-1]
            self.log(self.lang["PB_INVALID_EXTENSION"].format(f=i, m=str(e)), self.LOGLEV_ERROR)
            for line in traceback.format_exc().split("\n"):
                if line.strip():
                    self.log(line, self.LOGLEV_ERROR)

    def _reload_core_pages(self):
        global PyBoardPages
        self.log(self.lang["PB_RELOAD_CORE_PAGES"], self.LOGLEV_WARN)
        del sys.modules["PyBoardPages"]
        PyBoardPages = __import__("PyBoardPages")
        del self.Pages["net.pyboard"]
        del self.Pages["net.pyboard.admin"]
        del self.bp
        self.bp = PyBoardPages.BasePages(self)
        del self.ap
        self.ap = PyBoardPages.Admin(self)

    def unload_extension(self, identifier):
        for h in self.handlers:
            if identifier in self.handlers[h]:
                del self.handlers[h][identifier]
        if identifier in self.Pages:
            del self.Pages[identifier]
        self.log(self.lang["PB_UNLOAD_MODULE"].format(id=identifier), self.LOGLEV_WARN)
        self.extension_by_id(identifier).__unload__()
        self.Extensions[:] = [x for x in self.Extensions if x.IDENTIFIER != identifier]
        self._extm[:] = [x for x in self._extm if x.main.IDENTIFIER != identifier]

    @property
    def ext_identifiers(self):
        return [i.IDENTIFIER for i in self.Extensions] + ["net.pyboard", "net.pyboard.admin"]

    def extension_by_id(self, name):
        if name == "net.pyboard":
            return self.bp
        elif name == "net.pyboard.admin":
            return self.ap
        elif name in self.ext_identifiers:
            for e in self.Extensions:
                if e.IDENTIFIER == name:
                    return e
                else:
                    continue
        else:
            raise Exception("No extension found.")

    def set_paths(self):
        """Set up our working, serving, and remote directories, plus make sure that our dirs are all there"""
        self.workd = sys.path[0].rstrip("/")
        self.datad = sys.path[0].rstrip("/") + "/data"
        self.log(self.lang["PB_GOT_CWD"].format(d=self.workd))
        self.docroot = "{0}/{1}".format(self.workd, self.conf["DocumentRoot"])
        if not os.path.isdir(self.docroot):
            os.mkdir(self.docroot)
        for x in "extensions", "data/extdata", "data/boards", "tmp":
            if not os.path.isdir("{0}/{1}".format(self.workd, x)):
                self.log(self.lang["PB_FOLDER_NONEXISTENT"].format(f=x), self.LOGLEV_WARN)
                os.mkdir("{0}/{1}".format(self.workd, x))
        self.remote = "/" + self.conf["Subfolder"].strip("/") or "/"
        self.log(self.lang["PB_MAP_DIR"].format(loc=self.docroot, rem=self.remote))

    def wsgize(self, hdict):
        """Convert a dictionary of HTTP headers to the correct tuple-list WSGI format"""
        l = []
        for k, v in hdict.items():
            l.append((str(k), str(v)))
        return l

    def __del__(self):
        for i in self.ext_identifiers:
            if i not in ["net.pyboard", "net.pyboard.admin"]:
                self.unload_extension(i)
        if self.conf["SessionPersistence"]:
            with open("{0}/.pbsession".format(self.workd), "w+") as mf:
                mf.write("__pfsessionfile{0}__\n".format(self.conf["__version"]))
                if self.modSessions:
                    for i in self.modSessions:
                        mf.write("{0}:{1}:{2}:{3}\xFF".format(i, *self.modSessions[i]))
                    mf.write("\n")
                mf.write("__end__")

    def __call__(self, environ, start_response):
        """Main request handler."""
        StatusCode = "200 OK"
        Headers = {
            "Server": "PyBoard/{0}".format(self.conf["__version"]),
            "Date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time()))
        }
        t = time.clock()
        if environ["PATH_INFO"] != "/":
            requested_resource = re.sub(r"(/){2,}", "/", urllib.unquote(environ["PATH_INFO"]).rstrip("/") + ("/" if environ["PATH_INFO"].endswith("/") else ""))
        else:
            requested_resource = environ["PATH_INFO"]
        if self.conf["Subfolder"]:
            if not requested_resource.startswith("/"+self.conf["Subfolder"].strip("/")):
                e = self.bp.generateError("404 Not Found", etext="The requested page was not found on this server.")
                Headers = dict(Headers.items() + e["headers"].items())
                start_response(e["status"], self.wsgize(Headers))
                self.log("Request: {0} | Took {1} secs".format(environ["PATH_INFO"], time.clock() - t))
                return e["rdata"]
            else:
                environ["PATH_INFO"] = requested_resource = requested_resource.replace("/"+self.conf["Subfolder"].strip("/"), "", 1)
        _proto, _origin = None, None
        if self.conf["RealIPHeader"] and "HTTP_" + self.conf["RealIPHeader"].upper().replace("-", "_") in environ:
            _origin = environ["HTTP_" + self.conf["RealIPHeader"].upper().replace("-", "_")]
        if self.conf["ProtocolHeader"] and "HTTP_" + self.conf["ProtocolHeader"].upper().replace("-", "_") in environ:
            _proto = environ["HTTP_" + self.conf["ProtocolHeader"].upper().replace("-", "_")].lower()
        request = PyBoardObjects.Request(self, environ, _proto, _origin)
        self.raise_event(PyBoardObjects.Event("PBRequestStart", cancellable=False, request=request))
        try:
            for e in self.Pages:
                if requested_resource in self.Pages[e]:
                    response = self.Pages[e][requested_resource](self.extension_by_id(e))(request)
                    Headers["Cache-Control"] = "no-cache; max-age=0"
                    break
            else:
                response = self.bp.serveFromFilesystem(request)
            if response is None:
                response = self.bp.generateError("200 OK", etext=self.lang["ERR_HANDLER_RETURNED_NONE"])
        except Exception as e:
            self.log("*** [SERVER ERROR] ***********************", self.LOGLEV_ERROR)
            for line in traceback.format_exc().split("\n"):
                if line.strip():
                    self.log(line, self.LOGLEV_ERROR)
            self.log("******************************************", self.LOGLEV_ERROR)
            if self.conf["ShowErrorTraceback"]:
                response = self.bp.generateError("500 Internal Server Error", etext="<h3 class='trace_head'>{0}</h3><pre class='trace'>{1}</pre>".format(self.lang["ERR_UNHANDLED"].format(type=type(e).__name__, msg=str(e)), traceback.format_exc().replace(self.workd, "*")))
            else:
                response = self.bp.serveFromFilesystem(request, "{0}/{1}".format(self.docroot, self.conf["GenericErrorFile"].strip("/")))
        Headers = dict(Headers.items() + response["headers"].items())
        start_response(response["status"] or StatusCode, self.wsgize(Headers))
        self.log("Request: {0} | Took {1} secs".format(environ["PATH_INFO"], time.clock() - t))
        return response["rdata"]

if __name__ == '__main__':
    application = PyBoard()
    application.log("OK.")

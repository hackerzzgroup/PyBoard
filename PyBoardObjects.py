# This file is a part of PyBoard.
# Copyright (c) 2011 - 2012 The Hackerzz Group, Inc.
# All rights reserved.
import cgi
import imp
import os
import re
import sys
import time
import types
import urllib

class Configuration(object):
    """Stores PyBoard's configuration values."""
    version = "1.5-dev"

    def __init__(self, fp="config.py", ext=None):
        print("-- Config: Reading {0}/{1}.".format(ext or "net.pyboard", fp))
        self.path = fp
        self.ext = ext
        sys.dont_write_bytecode = True
        if not ext:
            try:
                self._config = imp.load_source("data.config.by-file.{0}".format(fp), "{0}/data/{1}".format(sys.path[0], fp))
            except IOError:
                f = open("{0}/data/{1}".format(sys.path[0], fp), "w+")
                f.close()
                self._config = imp.load_source("data.config.by-file.{0}".format(fp), "{0}/data/{1}".format(sys.path[0], fp))
            if fp == "config.py":
                self._default = imp.load_source("data.defaultcfg", sys.path[0]+"/data/config.default.py")
            else:
                self._default = None
        else:
            try:
                self._config = imp.load_source("extdata.{0}.config".format(ext), "{0}/data/extdata/{1}/{2}".format(sys.path[0], ext, fp))
            except IOError:
                f = open("{0}/data/extdata/{1}/{2}".format(sys.path[0], ext, fp), "w+")
                f.close()
                self._config = imp.load_source("extdata.{0}.config".format(ext), "{0}/data/extdata/{1}/{2}".format(sys.path[0], ext, fp))
        sys.dont_write_bytecode = False

    def reload(self):
        """Re-imports the configuration."""
        del self._config
        self.__init__(fp=self.path, ext=self.ext)

    def get(self, item, default):
        try:
            return self[item]
        except KeyError:
            return default

    def __getitem__(self, item):
        if isinstance(item, int):
            raise TypeError("Nope!")
        elif item == "__version":
            return self.version
        elif item.startswith("__"):
            return getattr(self._default, item[2:])
        else:
            try:
                return getattr(self._config, item)
            except:
                if self._default:
                    return getattr(self._default, item)
                else:
                     raise KeyError(item)

    def __setitem__(self, item, value):
        setattr(self._config, item, value)

class Language(object):
    """
    <+lilytastic> i don't want to play with neku, he's a faggot
    """
    def __init__(self, code):
        if not isinstance(code, basestring):
            raise TypeError("Nope!")
        if "/" in code or "\\" in code:
            raise NameError("Nope!")
        self.code = code
        self._lang = imp.load_source("data.lang."+code, "{1}/data/lang/{0}.py".format(code, sys.path[0]))
        del self._lang.__builtins__

    def reload(self):
        """Re-imports the configuration."""
        del self._lang
        self.__init__(self.code)

    @property
    def getDict(self):
        return self._lang.__dict__

    def __getitem__(self, item):
        if isinstance(item, int):
            raise TypeError("Nope!")
        else:
            try:
                return getattr(self._lang, item)
            except:
                return item

class Event(object):
    def __init__(self, eventName, cancellable=True, **kwargs):
        for i in kwargs:
            if i not in ["cancel", "Cancel", "name", "cancelled", "cancelMessage"]:
                setattr(self, i, kwargs[i])
            else:
                raise AttributeError("This is a reserved name. Stop breaking events.")
        self.name = eventName
        self._cancellable = cancellable
        self.cancelled = False
        self.cancelMessage = ""

    def __repr__(self):
        return "<{0} event; cancelled = {1}; cancellable = {2}>".format(self.name, self.cancelled, self._cancellable)

    def cancel(self, message=""):
        if self.cancellable:
            self.cancelled = True
            self.cancelMessage = message

    class Cancel(Exception):
        def __init__(self, message):
            super(Event.Cancel, self).__init__(message)
            self.cancelMessage = message

class Extension(object):
    IDENTIFIER = "net.pyboard.BaseExtension"
    REQUIRES_DATA_FOLDER = False
    REQUIRES_CONFIG_FILE = False
    LOGLEV_INFO = 0
    LOGLEV_WARN = 1
    LOGLEV_ERROR = 2
    def __init__(self, PyBoard):
        self.instance = PyBoard
        if self.REQUIRES_DATA_FOLDER:
            self._prepareDataFolder()
        if self.REQUIRES_CONFIG_FILE:
            try:
                self.dataFolder
            except AttributeError:
                self._prepareDataFolder()
            if not os.path.exists(self.dataFolder + "/config.py"):
                with open(self.dataFolder + "/config.py", "w+") as cf:
                    cf.write("")
            self.config = Configuration(ext=self.IDENTIFIER, fp="config.py")

    def _prepareDataFolder(self):
        if not os.path.exists(self.instance.workd + "/data/extdata/"):
            os.mkdir(self.instance.workd + "/data/extdata/")
        self.dataFolder = self.instance.workd + "/data/extdata/" + self.IDENTIFIER
        if not os.path.exists(self.dataFolder):
            os.mkdir(self.dataFolder)

    def __str__(self):
        return "<PBExtension {0}>".format(self.IDENTIFIER)

    __repr__ = __str__

    def getConfig(self, filename):
        if not os.path.exists(self.dataFolder + "/{0}".format(filename)):
            with open(self.dataFolder + "/{0}".format(filename), "w+") as cf:
                cf.write("")
        return Configuration(ext=self.IDENTIFIER, fp=filename)

    def hook(self, hook_id, callable):
        try:
            if hook_id in self.instance.handlers:
                self.instance.handlers[hook_id][self.IDENTIFIER] = callable
            else:
                self.instance.handlers[hook_id] = {self.IDENTIFIER: callable}
        except:
            self.log(self.instance.lang["PB_COULDNT_HOOK_EVENT"].format(id=self.IDENTIFIER, func=callable), self.LOGLEV_ERROR)

    def addPage(self, uri, handler):
        print handler
        try:
            self.instance.Pages
        except AttributeError:
            self.instance.Pages = {}
        if uri in self.instance.Pages:
            self.log(self.instance.lang["PB_FUNC_ALREADY_BOUND_URI"], self.LOGLEV_ERROR)
        else:
            if self.IDENTIFIER not in self.instance.Pages:
                self.instance.Pages[self.IDENTIFIER] = {}
            if not isinstance(handler, type):
                a = type("{0}/{1}".format(self.IDENTIFIER, handler.func_name), (self.RequestHandler,), {
                    "get": handler,
                    "post": handler,
                    "head": handler,
                })
                handler = a
            self.instance.Pages[self.IDENTIFIER][uri] = handler
            #self.log(self.instance.lang["PB_BOUND_PAGE"].format(func=function, uri=uri))

    def addModView(self, name, locname, call):
        if name == "login":
            raise AttributeError("This is a reserved name.")
        if name in self.instance.modViews and self.instance.modViews[name]["origin"] != self.IDENTIFIER:
            self.log(self.instance.lang["PB_FUNC_ALREADY_BOUND_URI"], self.LOGLEV_ERROR)
            return
        self.instance.modViews[name] = {
            "name": locname,
            "call": call,
            "origin": self.IDENTIFIER
        }

    def provideDatabase(self, name, classes, metadata):
        if self.IDENTIFIER not in self.instance._dbmods:
            self.instance._dbmods[self.IDENTIFIER] = {name: self.DatabaseControllerObject(*(classes + (metadata,)))}
        else:
            self.instance._dbmods[self.IDENTIFIER][name] = self.DatabaseControllerObject(*(classes + (metadata,)))
        self.log("provides database: {0} (version {1})".format(metadata["name"], metadata["version"]))

    def log(self, message, loglev=0):
        if loglev == 1:
            print(time.strftime("[%H:%M:%S] \033[33;1m[{0}] {1}\033[0m".format(self.IDENTIFIER, str(message))))
        elif loglev == 2:
            print(time.strftime("[%H:%M:%S] \033[31;1m[{0}] {1}\033[0m".format(self.IDENTIFIER, str(message))))
        else:
            print(time.strftime("[%H:%M:%S] [{0}] {1}".format(self.IDENTIFIER, str(message))))

    def redirect(self, location, headers=None):
        if not headers:
            headers = {}
        return Response(s="303 See Other", h=dict(headers.items() + [("Location", location), ("Content-Length", "0")]), r="")

    def generateError(self, status="500 Internal Server Error", heading="Error", return_to=None, etext="An unspecified error occurred.", httpheaders=None):
        if httpheaders == None:
            httpheaders = {}
        error = {
            "header": unicode(heading),
            "message": unicode(etext),
            "location": unicode((self.instance.func.TemplateConstants["root"] + "/") if return_to == None else return_to)
        }
        r = Response(s=status, h=dict({"Content-Type": "text/html"}.items() + httpheaders.items()), r=self.instance.func.page_format(v=error, template="error.pyb"))
        if status.startswith("404 ") and self.instance.conf["GenericNotFoundFile"]:
            path = os.path.abspath("{0}/{1}".format(self.instance.docroot, self.instance.conf["GenericNotFoundFile"].strip("/")))
            if os.path.exists(path): # must avoid infinite loops
                f = open(path, "rb")
                f.seek(0, 2)
                size = f.tell()
                f.seek(0, 0)
                r.rdata = self.instance.func.read_faster(f)
                r.headers["Content-Length"] = size
        return r

    class DatabaseControllerObject(object):
        def __init__(self, Global, Board, metadata):
            self.Global = Global
            self.Board = Board
            for k, v in metadata.items():
                setattr(self, k, v)

    class RequestHandler(object):
        def __init__(self, ext):
            self.ext = ext

        def __getattr__(self, item):
            try:
                return object.__getattr__(self, item)
            except AttributeError:
                return getattr(self.ext, item)

        def __call__(self, request):
            if request.method.lower() == "get":
                return self.get(request)
            elif request.method.lower() == "post":
                return self.post(request)
            elif request.method.lower() == "head":
                return self.head(request)

        def get(self, request):
            return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_CANT_GET"])

        def post(self, request):
            return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_CANT_POST"])

        def head(self, request):
            return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_CANT_HEAD"])

class Request(object):
    def __init__(self, instance, environ, protocol=None, origin=None):
        self.instance = instance
        self.environ = environ;
        self._authenticated, self._user = None, None
        self.url = urllib.unquote(environ["PATH_INFO"]);
        self.query = environ["QUERY_STRING"];
        self.query_dict = {}
        if self.query:
            for i in self.query.split("&"):
                if i:
                    if "=" in i:
                        ib = i.split("=")
                        self.query_dict[urllib.unquote(ib[0])] = urllib.unquote(ib[1])
                    else:
                        self.query_dict[urllib.unquote(i)] = True
        self.origin = origin or environ["REMOTE_ADDR"]
        self.proto = protocol or "http"
        self.method = environ["REQUEST_METHOD"].lower()
        if environ["REQUEST_METHOD"] == "POST":
            self.form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
        self.cookies = {};
        self.has_cookies = False;
        if "HTTP_COOKIE" in environ and environ["HTTP_COOKIE"]:
            c = environ["HTTP_COOKIE"].split(';')
            try:
                for cookie in c:
                    this = cookie.split('=')
                    if len(this) == 2:
                        self.cookies[this[0].strip()] = urllib.unquote(this[1])
            except IndexError:
                pass;
            if len(self.cookies) > 0:
                self.has_cookies = True

    @property
    def authenticated(self):
        if self._authenticated == None:
            self.__performAuth__()
        return self._authenticated

    @property
    def user(self):
        if self._user == None:
            self.__performAuth__()
        return self._user

    def __performAuth__(self):
        if "pfAuthToken" in self.cookies:
            self._authenticated = self.instance.func.verifyLogin(self.cookies["pfAuthToken"], self.origin)
            if self._authenticated:
                self._user = self.instance.modSessions[self.cookies["pfAuthToken"].split("|")[0]][0]
        else:
            self._authenticated, self._user = 0, ""

    def contains(self, item):
        return "HTTP_"+item.upper().replace("-", "_") in self.environ

    __contains__ = contains

    def __getitem__(self, item):
        try:
            return self.environ["HTTP_"+item.upper().replace("-", "_")]
        except KeyError:
            raise KeyError(item)

    def __repr__(self):
        return "<PyBoardRequest from {0}>".format(self.origin)

class Response(object):
    """
    <Diath> tfw you will never be in a homo relationship with any cute loli ;-;
    """
    def __init__(self, s="200 OK", h=None, r=""):
        self._rdata = ""
        self.status = s
        self.headers = h or {}
        self.rdata = r

    @property
    def rdata(self):
        return self._rdata

    @rdata.setter
    def rdata(self, val):
        self._rdata = val
        if isinstance(val, basestring):
            self.headers["Content-Length"] = len(val)

    def __getitem__(self, key):
        if key == 0 or key == "status":
            return self.status
        if key == 1 or key == "headers":
            return self.headers
        if key == 2 or key == "rdata":
            return self.rdata

    def __repr__(self):
        return "<PyBoardResponse: {0}, {1} headers>".format(self.status, len(self.headers))

    __str__ = __repr__

# <+viracocha> oh this is an old version too; so mines missing the last 2 methods
# <+viracocha> im not incompetent; i swear

class Thread(object):
    """Represents a thread."""
    def __init__(self, instance, bid, posts):
        self.instance = instance
        self.board = bid
        posts = sorted(posts, key=lambda x: x["id"])
        self.container = []
        for struct in posts:
            self.container.append(Post(instance, bid, struct))
        self.tid = posts[0]["id"]
        self.attrs = {
            "locked": posts[0]["locked"],
            "stuck": posts[0]["sticky"],
            "bumped": posts[0]["lastbump"],
            "autosaged": posts[0]["autosage"],
        }

    def __getitem__(self, item):
        if isinstance(item, int) or isinstance(item, slice):
            return self.container[item]
        elif isinstance(item, basestring):
            for i in self.container:
                if str(i.pid) == item:
                    return i
            else:
                raise KeyError(item)

    def __iter__(self):
        return self.container.__iter__()

    def sync(self):
        new = self.instance.boards[self.board].dbGetThread(self.op.pid)
        self.__init__(self.instance, self.board, new)

    @property
    def op(self):
        return self.container[0]

    @property
    def replies_with_images(self):
        if len(self) <= 1:
            return 0
        count = 0
        for i in self.container[1:]:
            if i.image["location"]:
                count += 1
        return count

    @property
    def reply_count(self):
        return len(self) - 1

    def __str__(self):
        return "PyBoardThread containing posts: " + ", ".join(sorted(self.postnums.values()))

    def __len__(self):
        return len(self.container)

    def makeCitelinks(self, l, mod):
        links = []
        dc = {}
        for k, v in l:
            if not k:
                k = self.board
                v = "*{0}".format(v)
            if not v and k in self.instance.boards:
                links.append((
                    "&gt;&gt;&gt;/{0}/".format(k),
                    "<a class='citelink' href='/{0}/index.html{1}'>&gt;&gt;&gt;/{0}/</a>".format(
                        k, "?mod" if mod.has_permission("boards.{0}.modview".format(k)) else ""
                    )
                ))
            else:
                dc.setdefault(k, []).append(v)
        for b in dc:
            if b in self.instance.boards:
                mapping = dict(self.instance.boards[b].dbGetPostAndThreadIDs())
                for p in dc[b]:
                    if p.startswith("*"):
                        fmt = 0
                        p = p[1:]
                    else:
                        fmt = 1
                    if int(p) in mapping:
                        if fmt:
                            links.append((
                                "&gt;&gt;&gt;/{0}/{1}".format(b, p),
                                "<a class='citelink' href='/{0}/res/{2}.html{1}#{3}'>&gt;&gt;&gt;/{0}/{3}</a>".format(
                                    b, "?mod" if mod.has_permission("boards.{0}.modview".format(b)) else "", mapping[int(p)] or p, p
                                )
                            ))
                        else:
                            links.append((
                                "&gt;&gt;{0}".format(p),
                                "<a class='citelink' href='/{0}/res/{2}.html{1}#{3}'>&gt;&gt;{3}</a>".format(
                                    b, "?mod" if mod.has_permission("boards.{0}.modview".format(b)) else "", mapping[int(p)] or p, p
                                )
                            ))
        return links

    def renderThread(self, index=False, mod=None, live=False):
        """Create an HTML representation of this thread."""
        t = time.clock()
        if self.attrs["stuck"]:
            num_replies = self.instance.boards[self.board].conf["StickyIndexMaxReplies"] if index else self.reply_count
        else:
            num_replies = self.instance.boards[self.board].conf["IndexMaxReplies"] if index else self.reply_count
        if mod:
            user_obj = self.instance.masterDB.users[mod]
        else:
            user_obj = self.instance.masterDB.users.Dummy()
        replies = []
        if self.reply_count:
            if index:
                cl_cache = self.makeCitelinks(list(set([i for l2 in [a.scan_citelinks() for a in self[1:][-num_replies:]] for i in l2])), user_obj)
                replies = [p.renderPost(index=index, mod=user_obj, cl_cache=cl_cache) for p in self[1:][-num_replies:]]
            else:
                cl_cache = self.makeCitelinks(list(set([i for l2 in [a.scan_citelinks() for a in self[1:]] for i in l2])), user_obj)
                replies = [p.renderPost(index=index, mod=user_obj, cl_cache=cl_cache) for p in self[1:]]
        skel = {
            "tid": self.tid,
            "board": self.instance.boards[self.board].md,
            "replies": replies,
            "attrs": self.attrs,
            "mod": mod != None,
            "op": self.op.renderPost(index=False, mod=mod)
        }
        if not index:
            skel["form"] = self.instance.func.generateForm(board=self.instance.boards[self.board], thread=self.tid, mod=mod)
        else:
            renderedReplies = len(replies)
            renderedImages = len([None for p in self[1:][-num_replies:] if p.image["location"]])
            omittedReplies = self.reply_count - renderedReplies
            omittedImages = self.replies_with_images - renderedImages
            if omittedReplies:
                if omittedImages:
                    omit = self.instance.lang["OMIT_IMAGES"].format(n=omittedReplies, i=omittedImages, s="s" if omittedReplies != 1 else "", s2="s" if omittedImages != 1 else "")
                else:
                    omit = self.instance.lang["OMIT"].format(n=omittedReplies, s="s" if omittedReplies != 1 else "")
            else:
                omit = None
            skel["omit"] = omit
        skel["d"] = int(time.time())
        if not index:
            if live:
                skel["topbar"] = self.instance.masterDB.getTopbar(forceRebuild=True, mod=user_obj)
                self.instance.log("ThreadBuildTime: {}".format(time.clock() - t))
                return self.instance.func.page_format(v=skel, template="thread.pyb")
            else:
                tempname = "{0}/tmp/thread_{1}{2}_{3}".format(self.instance.workd, self.board, self.tid, int(time.time()))
                with open(tempname, "w+") as tmpfile:
                    tmpfile.write(self.instance.func.page_format(v=skel, template="thread.pyb"))
                os.rename(tempname, "{0}/{1}/res/{2}.html".format(self.instance.docroot, self.board, self.tid))
                self.instance.log("ThreadBuildTime: {}".format(time.clock() - t))
        else:
            self.instance.log("ThreadBuildTime: {}".format(time.clock() - t))
            return skel

class Post(object):
    """Represents a post."""
    def __init__(self, instance, bid, struct):
        """Prepare datas and stuff"""
        self.instance = instance
        self._processed_post = None
        self.poster = {
            "name": struct["poster.name"],
            "email": struct["poster.email"],
            "tripcode": struct["poster.tripcode"] or "",
            "ip": struct["poster.ip"],
            "capcode": struct["poster.capcode"],
        }
        if not self.poster["name"] and not self.poster["tripcode"]:
            self.poster["name"] = self.instance.lang["ANONYMOUS"]
        self.subject = struct["subject"]
        self._body = struct["body"]
        self.body_hash = struct["hash"]
        self.image = {
            "location": struct["image.url"],
            "filename": struct["image.filename"],
        }
        self.attrs = {
            "bid": bid,
            "pid": struct["id"],
            "tid": struct["thread"],
            "post_time": struct["timestamp"],
            "spoiler_image": struct["spoilerimage"],
            "raw_html": struct["rawhtml"],
            "ban_message": struct["banmessage"],
            "show_ban": struct["showban"],
        }

    def scan_citelinks(self):
        """This returns a list of all unique citelinks in the body"""
        return list(set([x for x in re.findall(r"(?:^|\s)>>(?:>/([a-zA-Z0-9]+)?/)?([0-9]+)?(?:$|\s)", self._body, flags=re.M)]))

    def _runWordfilter(self, line):
        if re.match(r'^(&gt;|\>){1}', line) is not None:
            line = '<span class="ishygddt">{0}</span>'.format(line)
        for i in self.instance.conf["Wordfilters"] + self.instance.boards[self.attrs["bid"]].conf.get("Wordfilters", []):
            line = re.sub(i[0], i[1], line)
        return line

    def body(self, index=False, mod=False, cl_cache=None):
        t = time.clock()
        if not cl_cache:
            cl_cache = []
        if self._processed_post != None:
            return self._processed_post
        else:
            b = [line.strip("\r\n") for line in self._body.strip("\r\n").split('\n')]
            if index:
                cc = 0
                new = []
                for line in b:
                    new.append(line)
                    cc += len(line)
                    if cc > 1000 or len(new) >= 8:
                        break
                if new != b:
                    wasTrunc = True
                else:
                    wasTrunc = False
                b = new
            post = cgi.escape("\n".join(b))
            if not self.attrs["raw_html"]:
                for i in cl_cache:
                    post = re.sub("(^|\\s){0}($|\\s)".format(re.escape(i[0])), "\\1{0}\\2".format(i[1]), post, flags=re.M)
                post = [self._runWordfilter(line) for line in post.split("\n")]
            if self.attrs["show_ban"]:
                post.append("<br><h4 class='banned'>{0}</h4>".format(self.attrs["ban_message"] or self.instance.lang["WAS_BANNED"]))
            if index and wasTrunc:
                post.append("<br><span class='omit'>{0}</span>".format(self.instance.lang["POST_TRUNCATED"]))
            self.instance.log("PostBuildTime: {}".format(time.clock() - t))
            return "<br>".join(post)

    def renderPost(self, index=False, mod=False, cl_cache=None):
        v = {
            "time": time.strftime("%d/%m/%y (%a) %H:%M:%S", time.localtime(self.attrs["post_time"])),
            "name": self.poster["name"],
            "email": self.poster["email"] or None,
            "tripcode": self.poster["tripcode"] or None,
            "body": self.body(index, mod, cl_cache or []),
            "capcode": self.poster["capcode"] or None,
            "subject": self.subject or None,
            "addr": self.poster["ip"],
            "postid": self.attrs["pid"],
        }
        return dict(v.items() + self.instance.func.image(self.attrs["bid"], self.image, self.attrs["spoiler_image"]).items())

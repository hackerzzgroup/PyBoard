# This file is a part of PyBoard.
# Copyright (c) 2011 - 2012 The Hackerzz Group, Inc.
# All rights reserved.
import email.utils
import hashlib
import mimetypes
import os
import random
import re
import sys
import time
from collections import deque, OrderedDict
import PyBoardObjects
mimetypes.init()

class BasePages(PyBoardObjects.Extension):
    """Base web functionality for PyBoard."""
    IDENTIFIER = "net.pyboard"
    def __init__(self, PyBoard):
        PyBoardObjects.Extension.__init__(self, PyBoard)
        self.addPage("/post", self.post)
        self.addPage("/delete", self.delete)
        self.addPage("/banner", self.serveBanner)
        self.addPage("/banned", self.banned)

    def serveBanner(self, request):
        blist = [x for x in os.listdir("{0}/static/banners".format(self.instance.docroot)) if x.split(".")[-1] in ["png", "gif", "jpg", "jpeg"]]
        return PyBoardObjects.Response("303 See Other", {"Location": "{0}/banners/{1}".format(self.instance.conf["StaticDomain"].strip("/") or "/static", random.choice(blist))}, "")

    def banned(self, request):
        if request.origin in self.instance.masterDB.bans:
            return self.generateBan(self.instance.masterDB.bans[request.origin])
        for i in self.instance.boards:
            if request.origin in self.instance.boards[i].bans:
                return self.generateBan(self.instance.boards[i].bans[request.origin])
        else:
            return self.redirect("/")
    
    def generateBan(self, info):
        info["relative"] = self.instance.func.getRelativeTime(info["expires"] - int(time.time()))
        if info["relative"]:
            info["has_rel"] = True
        info["started"] = time.strftime("%x @%X", time.localtime(info["started"]))
        info["expires"] = time.strftime("%x @%X", time.localtime(info["expires"]))
        info["global"] = info["board"] == "*"
        return self.instance.func.page_format(template="ban.pyb", v=info)

    class delete(PyBoardObjects.Extension.RequestHandler):
        def post(self, request):
            for i in ["bid", "rmpost", "delpost"]:
                if i in request.form:
                    if isinstance(request.form[i], list):
                        if i != "delpost":
                            return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_NOACTION"])
                        for j in request.form[i]:
                            if j.filename:
                                return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_NOACTION"])
                else:
                    return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_NOACTION"])
            uobj = self.instance.masterDB.users[request.user]
            del_file = request.form["rmpost"].value.decode("utf-8").strip() == self.instance.lang["FILE"]
            board = request.form["bid"].value
            if board not in self.instance.boards:
                return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_NONEXISTENT_BOARD"])
            out = self.instance.boards[request.form["bid"].value].posts.all()
            if out:
                ids = [x[0] for x in out]
            else:
                return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_NOACTION"])
            try:
                if (uobj.has_permission("boards.{0}.delete".format(request.form["bid"].value))):
                    posts = [int(x) for x in request.form.getlist("delpost") if x.isdigit() and int(x) in ids]
                else:
                    posts = [int(x) for x in request.form.getlist("delpost") if x.isdigit() and int(x) in ids and
                             self.instance.boards[board].posts[int(x)].poster["ip"] == request.origin]
            except self.instance.boards[board].PostNotFoundError:
                pass
            if len(posts) > 0:
                for i in posts:
                    try:
                        del self.instance.boards[board].posts[str(i) + ("@file" if del_file else "")]
                    except self.instance.boards[board].PostNotFoundError:
                        pass
            if "Referer" in request and request["Referer"].split("?")[-1] == "mod" and uobj.has_permission("boards.{0}.modview".format(request.form["bid"].value)):
                return self.redirect("/{0}/index.html?mod".format(request.form["bid"].value))
            else:
                return self.redirect("/{0}/index.html".format(request.form["bid"].value))

    class post(PyBoardObjects.Extension.RequestHandler):
        def _doReferrerCheck(self, request, modQuery):
            if "Referer" in request and "Host" in request:
                if "tid" not in request.form:
                    if not re.match(r"(http(s)?://){1}/{0}(/index\.html)?".format(re.escape(request.form["bid"].value), re.escape(request["Host"])), request["Referer"]):
                        return (False, self.generateError("400 Bad Request", etext=self.instance.lang["ERR_REFERRERS_PLS"], return_to="/{0}/index.html{1}".format(request.form["bid"].value, modQuery)))
                else:
                    if not re.match(r"(http(s)?://){2}/{0}/res/({1})(\.html)?".format(re.escape(request.form["bid"].value), re.escape(request.form["tid"].value), re.escape(request["Host"])), request["Referer"]):
                        return (False, self.generateError("400 Bad Request", etext=self.instance.lang["ERR_REFERRERS_PLS"], return_to="/{0}/index.html{1}".format(request.form["bid"].value, modQuery)))
            else:
                return (False, self.generateError("400 Bad Request", etext=self.instance.lang["ERR_REFERRERS_PLS"], return_to="/{0}/index.html{1}".format(request.form["bid"].value, modQuery)))
        
        def _doUnprivilegedChecks(self, request):
            if not request.form["ts"].value.isdigit():
                return (False, self.generateError("400 Bad Request", etext=self.instance.lang["ERR_BAD_FORM"], return_to="/{0}/index.html".format(request.form["bid"].value)))
            else:
                tid = int(request.form["tid"].value)
                try:
                    if tid:
                        eq = sorted([os.path.getmtime("{0}/{1}/res/{2}.html".format(self.instance.docroot, request.form["bid"].value, request.form["tid"].value)), int(request.form["ts"].value)])
                    else:
                        eq = sorted([os.path.getmtime("{0}/{1}/index.html".format(self.instance.docroot, request.form["bid"].value)), int(request.form["ts"].value)])
                except OSError:
                    return (False, self.generateError("400 Bad Request", etext=self.instance.lang["ERR_BAD_FORM"], return_to="/{0}/index.html".format(request.form["bid"].value)))
                if (eq[1] - eq[0]) > 10800:
                    return (False, self.generateError("400 Bad Request", etext=self.instance.lang["ERR_FORM_EXPIRED"], return_to="/{0}/index.html".format(request.form["bid"].value)))
                if not self.instance.func.verifyForm(request.form):
                    return (False, self.generateError("400 Bad Request", etext=self.instance.lang["ERR_SPAM"], return_to="/{0}/index.html".format(request.form["bid"].value)))
            dnsbl = self.instance.func.dnsblCheck(request.origin)
            if dnsbl:
                return (False, self.generateError("400 Bad Request", etext=self.instance.lang["ERR_TRIPPED_DNSBL"].format(dnsbl), return_to="/{0}/index.html".format(request.form["bid"].value)))
            if request.form["bid"].value in self.instance.conf["AdminBoards"]:
                return (False, self.generateError('401 Unauthorized', etext=self.instance.lang["ERR_POST_PERMISSION_DENIED"], return_to="/admin?login"))
            if request.origin in self.instance.masterDB.bans:
                return (False, PyBoardObjects.Response(s="400 Bad Request", h={}, r=self.generateBan(self.instance.masterDB.bans[request.origin])))
            if request.origin in self.instance.boards[request.form["bid"].value].bans:
                return (False, PyBoardObjects.Response(s="400 Bad Request", h={}, r=self.generateBan(self.instance.boards[request.form["bid"].value].bans[request.origin])))
            lastPost = self.instance.boards[request.form["bid"].value].posts.by_address(request.origin, start=0, limit=1)
            if lastPost and time.time() - lastPost[0].attrs["post_time"] < self.instance.conf["TimeBetweenPosts"]:
                return (False, self.generateError("400 Bad Request", etext=self.instance.lang["ERR_WAIT_DAMMIT"], return_to="/{0}/index.html".format(request.form["bid"].value)))
            if lastPost and lastPost[0].body_hash == hashlib.md5(request.form["body"].value.decode("utf-8")).hexdigest() and (time.time() - lastPost[0].attrs["post_time"]) < 10:
                return (False, self.generateError("400 Bad Request", etext=self.instance.lang["ERR_FLOOD_DETECTED"], return_to="/{0}/index.html".format(request.form["bid"].value)))
            event = self.instance.raise_event(PyBoardObjects.Event("PBUnprivilegedPostCheck", cancellable=True, request=request))
            if event.cancelled:
                return (False, self.generateError("400 Bad Request", etext=event.cancelMessage, return_to="/{0}/index.html".format(request.form["bid"].value)))
            return (True, "")
        
        def post(self, request):
            modQuery = ""
            currentTime = int(time.time())
            if request.authenticated and ("Referer" in request) and (request["Referer"].split("?")[-1] == "mod"):
                modQuery = "?mod"
            # Basic verification
            for x in ["bid", "name", "email", "subject", "body", "ts", "tid", "key"]:
                if x not in request.form or isinstance(request.form[x], list) or request.form[x].filename:
                    return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_BAD_FORM"], return_to="/{0}/index.html{1}".format(request.form["bid"].value, modQuery))
            if request.form["bid"].value not in self.instance.boards:
                return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_NONEXISTENT_BOARD"])
            else:
                bid = request.form["bid"].value
            if request.form["tid"].value.isdigit():
                tid = int(request.form["tid"].value)
                if tid == 0:
                    tid = None
                elif tid not in self.instance.boards[bid].threads:
                    return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_NONEXISTENT_THREAD"])
                elif self.instance.boards[bid].threads[tid].attrs["locked"]:
                    if not request.authenticated:
                        return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_THREAD_LOCKED"])
            else:
                return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_BAD_FORM"], return_to="/{0}/index.html{1}".format(request.form["bid"].value, modQuery))
            # Mods bypass these.
            if not request.authenticated:
                passed, err = self._doUnprivilegedChecks(request)
                if not passed:
                    return err
            # Check referrer
            if self.instance.conf["ReferrerCheck"]:
                passed, err = self._doReferrerCheck(request, modQuery)
                if not passed:
                    return err
            # Split the name field
            name, trip, cap = re.findall(r"^([^#]+)?(?:((?:##[^\s]|#[^#\s]).+?))?(?:\s+)?(?:## (.+))?$", request.form["name"].value.decode("utf-8"))[0]
            trip = re.findall(r"((?:#|##)(?:[^#]+))", trip)
            if len(trip) >= 2 and self.instance.boards[bid].conf["DoubleTrips"] and not any(((trip[0].startswith("#") and trip[1].startswith("#")), (trip[0].startswith("##") and trip[1].startswith("##")))):
                trip[1] = "".join(trip[1:])
                tripcode = self.instance.func.make_tripcode(trip[0].lstrip("#"), secure=trip[0].startswith("##")) + self.instance.func.mktripcode(trip[1].lstrip("#"), secure=trip[1].startswith("##"))
            else:
                trip = "".join(trip)
                tripcode = self.instance.func.make_tripcode(trip.lstrip("#"), secure=trip.startswith("##"))
            noBump, returnToThread = False, self.instance.boards[bid].conf["AutoNoko"]
            email = request.form["email"].value.decode("utf-8").strip()[:128]
            if email == "noko":
                returnToThread = True
                email = ""
            if email == "sage":
                noBump = True
                if self.instance.boards[bid].conf["HideSage"]:
                    email = ""
            if email == "nokosage":
                noBump = returnToThread = True
                email = ""
            struct_post = {
                "id": None,
                "thread": tid,
                "timestamp": currentTime,
                "poster.ip": request.origin,
                "poster.name": name.strip()[:64],
                "poster.email": email,
                "poster.tripcode": tripcode,
                "poster.capcode": None,
                "subject": request.form["subject"].value.decode("utf-8").strip()[:100],
                "body": request.form["body"].value.decode("utf-8").replace("\r\n", "\n"),
                "image.url": None,
                "image.filename": None,
                "lastbump": currentTime if not tid else None,
                "locked": 0,
                "sticky": 0,
                "spoilerimage": False,
                "rawhtml": 0,
                "banmessage": None,
                "showban": 0,
                "autosage": 0,
                "hash": None,
            }
            if request.authenticated:
                uobj = self.instance.masterDB.users[request.user]
                if uobj.has_permission("capcode.{0}.use".format(cap.strip())):
                    struct_post["poster.capcode"] = self.instance.func.make_capcode(cap.strip())
                if "sticky" in request.form and request.form["sticky"].value == "on" and uobj.has_permission("boards.{0}.sticky".format(bid)):
                    struct_post["sticky"] = 1
                if "lock" in request.form and request.form["lock"].value == "on" and uobj.has_permission("boards.{0}.lock".format(bid)):
                    struct_post["locked"] = 1
                if "bumplock" in request.form and request.form["bumplock"].value == "on" and uobj.has_permission("boards.{0}.autosage".format(bid)):
                    struct_post["autosage"] = 1
                if "raw_html" in request.form and request.form["raw_html"].value == "on" and uobj.has_permission("boards.{0}.raw_html".format(bid)):
                    struct_post["rawhtml"] = 1
            filename, duplicate = None, None
            if "file" in request.form and request.form["file"].filename and request.form["file"].done >= 0:
                try:
                    filename, duplicate = self.instance.func.processImage(request.form["file"], bid)
                except self.instance.func.ImageError as e:
                    return self.generateError("400 Bad Request", etext=e, return_to="/{0}/index.html{1}".format(bid, modQuery))
                struct_post["image.url"] = filename
                struct_post["image.filename"] = request.form["file"].filename.decode("utf-8")
                if "spoiler" in request.form and request.form["spoiler"].value == "on" and self.instance.boards[bid].conf["SpoilerImages"]:
                    struct_post["spoilerimage"] = True
            elif not tid:
                return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_IMAGE_REQUIRED"], return_to="/{0}/index.html{1}".format(bid, modQuery))
            try:
                self.instance.func.runPostProcess(struct_post, bid, bool(request.authenticated))
            except self.instance.func.PostError as e:
                if struct_post["image.filename"] and not duplicate:
                    if os.path.exists("{0}/{1}/img/{2}".format(self.instance.docroot, bid, filename)):
                        os.remove("{0}/{1}/img/{2}".format(self.instance.docroot, bid, filename))
                    if os.path.exists("{0}/{1}/img/s{2}".format(self.instance.docroot, bid, filename)):
                        os.remove("{0}/{1}/img/s{2}".format(self.instance.docroot, bid, filename))
                return self.generateError("400 Bad Request", etext=str(e), return_to="/{0}/index.html{1}".format(bid, modQuery))
            struct_post["hash"] = hashlib.md5(request.form["body"].value).hexdigest()
            pid, tid = self.instance.boards[bid].make_post(struct_post, noBump)
            if returnToThread:
                url = "{0}/{1}/res/{2}.html{3}#{4}".format(self.instance.func.TemplateConstants["root"], bid, tid, modQuery, pid)
            else:
                url = "{0}/{1}/index.html{2}".format(self.instance.func.TemplateConstants["root"], bid, modQuery)
            return self.redirect(url)

        def get(self, request):
            return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_NO_POST"])

    def serveFromFilesystem(self, request, override=None):
        Headers = {}
        if request.url.lstrip("/").split("/", 1)[0] in self.instance.conf["AdminBoards"] and not request.authenticated:
            return self.generateError('401 Unauthorized', etext=self.instance.lang["ERR_403"], return_to="/admin?login")
        filepath = self.instance.docroot + "/" + request.url.lstrip("/")
        if not os.path.abspath(filepath).startswith(self.instance.docroot):
            return self.generateError('403 Forbidden', etext="Nope!")
        if override:
            filepath = override
        if os.path.isdir(filepath):
            if not filepath.endswith("/"):
                return self.redirect(location=request.url + "/{0}".format("?" + request.environ["QUERY_STRING"] if request.query else ""))
            else:
                filepath += "index.html"
        if request.query == "mod":
            if request.authenticated:
                a = re.findall(r"{0}/({1})/(?:res/([0-9]+)|(index|[0-9]+))\.html".format(re.escape(self.instance.docroot), "|".join([re.escape(x) for x in self.instance.boards])), filepath)
                if len(a) == 1:
                    a = a[0]
                    target = a[1:]
                    if len(target) == 2 and a[0] in self.instance.boards and self.instance.masterDB.users[request.user].has_permission("boards.{0}.modview".format(a[0])):
                        if target[0]:
                            try:
                                view = PyBoardObjects.Response("200 OK", {
                                    "Content-Type": "text/html",
                                    "Cache-Control": "no-cache; max-age=0",
                                }, self.instance.boards[a[0]].threads[target[0]].renderThread(index=False, mod=request.user, live=True))
                            except self.instance._databaseImplementor.Board.DatabaseError:
                                return self.generateError('404 Not Found', etext=self.instance.lang["ERR_404"])
                            else:
                                return view
                        elif target[1]:
                            return PyBoardObjects.Response("200 OK", {
                                "Content-Type": "text/html",
                                "Cache-Control": "no-cache; max-age=0",
                            }, self.instance.boards[a[0]].build_index(live=True, mod=True, page=int(target[1]) if target[1].isdigit() else 0, user=request.user))
                    else:
                        return PyBoardObjects.Response("303 See Other", {"Location": "/admin?login"}, "")
            else:
                return PyBoardObjects.Response("303 See Other", {"Location": "/admin?login"}, "")
        if os.path.isfile(filepath):
            if os.access(filepath, os.R_OK):
                moddate = time.gmtime(os.path.getmtime(filepath))
                if request.contains("If-Modified-Since") and not filepath.endswith('.html'):
                    sincets = time.mktime(email.utils.parsedate(request['If-Modified-Since']))
                    if sincets >= time.mktime(moddate):
                        return PyBoardObjects.Response("304 Not Modified", Headers, "")
                res = open(filepath, 'rb')
                Headers["Content-Type"] = mimetypes.guess_type(filepath)[0] or "text/plain"
                Headers["Content-Length"] = os.stat(filepath).st_size
                if filepath.endswith('.html'):
                    # don't cache html
                    Headers["Cache-Control"] = "no-cache; max-age=0"
                else:
                    Headers["Last-Modified"] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", moddate)
                return PyBoardObjects.Response("200 OK", Headers, self.instance.func.read_faster(res))
            else:
                return self.generateError('403 Forbidden', etext=self.instance.lang["ERR_403"])
        else:
            return self.generateError('404 Not Found', etext=self.instance.lang["ERR_404"])

class Admin(PyBoardObjects.Extension):
    """Class stub"""
    IDENTIFIER = "net.pyboard.admin"
    def __init__(self, *args):
        PyBoardObjects.Extension.__init__(self, *args)
        self.failedPasswords = {}
        self.instance.modViews.update(OrderedDict(
            [("boards", {
                "call": self.fBoardList,
                "name": "Boards",
                "origin": "net.pyboard.admin"
            }),
            ("bans", {
                "call": self.fBanList,
                "name": "Bans",
                "origin": "net.pyboard.admin"
            }),
            ("tools", {
                "call": self.fAdvanced,
                "name": "Tools",
                "origin": "net.pyboard.admin"
            })]
        ))
        self.addPage("/mod_action", self.fAction)
        self.addPage("/admin", self.fMain)
        self.addPage("/login", self.login)
        self.addPage("/logout", self.logout)

    def fBoardList(self, request):
        uobj = self.instance.masterDB.users[request.user]
        if "&" in request.query and request.query.split("&")[1] == "create":
            if uobj.has_permission("boards.create"):
                return self.instance.func.page_format(template="f/newboard.pyb", v={})
            else:
                return self.redirect("/admin?boards")
        b = []
        for board in self.instance.boards:
            a = self.instance.boards[board].md.items()
            if uobj.has_permission("boards.{0}.modview".format(board)):
                a.append(("can_mod", True))
            if uobj.has_permission("boards.{0}.config".format(board)):
                a.append(("can_setup", True))
            b.append(dict(a))
        return self.instance.func.page_format(template="f/boards.pyb", v={"boards": b,
            "has_boards": bool(b),
            "has_create": uobj.has_permission("boards.create"),
            "has_delete": uobj.has_permission("boards.delete"),
        })
    
    def fBanList(self, request):
        start = 0
        if "&" in request.query:
            if request.query.split("&")[1] == "new":
                return self.instance.func.page_format(template="f/newban.pyb", v={})
            try:
                start = int(request.query_dict.get("pos", 0))
            except ValueError:
                pass
        b = self.instance.masterDB.bans.get_list()
        for i in self.instance.boards:
            b += self.instance.boards[i].bans.get_list()
        b = sorted(b, key=lambda x: x["started"])[start:start + 50]
        if len(b) - (start + 50) >= 1:
            more = True
        else:
            more = False
        for d in b:
            if d["board"] == "*":
                d["global"] = True
            d["started_str"] = time.strftime("%x @%X", time.localtime(d["started"]))
            d["expires_str"] = time.strftime("%x @%X", time.localtime(d["expires"]))
        return self.instance.func.page_format(template="f/bans.pyb", v={
            "bans": b,
            "has_bans": bool(b),
            "has_more": more,
            "has_less": start != 0,
            "next_pos": start + 50,
        })
    
    def fUserList(self, request):
        uobj = self.instance.masterDB.users[request.user]
        start = 0
        if "&" in request.query:
            if request.query.split("&")[1] == "new":
                return self.instance.func.page_format(template="f/newuser.pyb", v={})
            start = request.query_dict.get("pos", 0)
        l = [u.struct for u in self.instance.masterDB.users.list(start=start, limit=50)]
        if len(self.instance.masterDB.users - start) >= 1:
            more = True
        else:
            more = False
        for i in l:
            if uobj.has_permission("users.modify.{0}".format(i["groups"][0])):
                i["can_modify"] = True
            if uobj.has_permission("users.view.{0}".format(i["groups"][0])):
                i["can_view"] = True
            i.update({
                "group_count": len(i["groups"]),
                "permission_count": len(i["permissions"]),
                "primary_group": i["groups"][0],
                "is_root": i["groups"][0] == "__root__",
            })
        return self.instance.func.page_format(template="f/users.pyb", v={
            "users": l,
            "has_more": more,
            "has_less": start != 0,
            "next_pos": start + 50,
        })
    
    def fAdvanced(self, request):
        uobj = self.instance.masterDB.users[request.user]
        if "&" in request.query:
            if "close_session" in request.query_dict:
                k = request.query_dict.get("close_session", "")
                if k in self.instance.modSessions:
                    if uobj.has_permission("users.close_session.{0}".format(self.instance.modSessions[k][0])):
                        del self.instance.modSessions[k]
                        return self.generateError("200 OK", heading=self.instance.lang["NOTICE"], etext=self.instance.lang["SESSION_CLOSED"], return_to="/admin?tools&sessions")
                    else:
                        return self.generateError("403 Forbidden", etext=self.instance.lang["ERR_PERMISSION_DENIED"], return_to="/admin?tools&sessions")
                else:
                    return self.generateError("200 OK", etext=self.instance.lang["SESSION_NOT_FOUND"], return_to="/admin?tools&sessions")
            elif request.query.split("&")[1] == "sessions":
                sess = [{
                    "sid": i,
                    "user": v[0],
                    "self": v[0] == request.user,
                    "can_close": uobj.has_permission("users.close_session.{0}".format(v[0])),
                    "last": time.strftime("%d/%m/%y (%a) %H:%M:%S", time.localtime(v[1])),
                } for i, v in self.instance.modSessions.items()]
                return self.instance.func.page_format(template="f/sessions.pyb", v={"sessions": sess})
        return self.instance.func.page_format(template="f/tests.pyb", v={
            "can_reloadconfig": uobj.has_permission("debug.reload_config"),
            "can_flushcache": uobj.has_permission("debug.flush_cache"),
            "can_reloaddb": uobj.has_permission("debug.reload_db"),
            "can_rebuild": uobj.has_permission("debug.rebuild_all"),
            "can_relang": uobj.has_permission("debug.reload_lang"),
            "can_repages": uobj.has_permission("debug.reload_core"),
            "can_view_sessions": uobj.has_permission("users.view_sessions"),
        })

    class fMain(PyBoardObjects.Extension.RequestHandler):
        def get(self, request):
            if not request.authenticated:
                if request.query == "login" or not request.query:
                    return PyBoardObjects.Response(s="200 OK", h={"Content-Type": "text/html"}, r=self.instance.func.page_format(template="f/login.pyb", v={}))
                else:
                    return self.generateError("401 Unauthorized", etext=self.instance.lang["ERR_403"], return_to="/admin?login")
            else:
                qstart = request.query.split("&")[0]
                if qstart in self.instance.modViews:
                    uobj = self.instance.masterDB.users[request.user]
                    if self.instance.masterDB.users[request.user].has_permission("admin.section.{0}".format(qstart)):
                        cnt = self.instance.modViews[qstart]["call"](request)
                        if isinstance(cnt, PyBoardObjects.Response):
                            return cnt
                        else:
                            return PyBoardObjects.Response(s="200 OK", h={"Content-Type": "text/html"}, r=self.instance.func.page_format(template="f/base.pyb", v={"sections": [
                                {"location": x, "name": self.instance.modViews[x]["name"], "selected": x == qstart} for x in self.instance.modViews if uobj.has_permission("admin.section.{0}".format(x))
                            ], "content": cnt}))
                    else:
                        return self.generateError("401 Unauthorized", etext=self.instance.lang["ERR_403"], return_to="/admin")
                else:
                    uobj = self.instance.masterDB.users[request.user]
                    return PyBoardObjects.Response(s="200 OK", h={"Content-Type": "text/html"}, r=self.instance.func.page_format(template="f/base.pyb", v={"sections": [
                        {"location": x, "name": self.instance.modViews[x]["name"]} for x in self.instance.modViews if uobj.has_permission("admin.section.{0}".format(x))
                    ], "content": "<img src='/static/img/pf.png'>"}))

    class login(PyBoardObjects.Extension.RequestHandler):
        def get(self, request):
            if request.authenticated:
                return self.redirect("/admin")
            else:
                return self.redirect("/admin?login")

        def post(self, request):
            if request.authenticated:
                return self.redirect("/admin")
            for x in ["user", "password"]:
                if x not in request.form:
                    return self.generateError("400 Bad Request", etext=":s", return_to="/admin?login")
            if request.origin not in self.failedPasswords:
                self.failedPasswords[request.origin] = [0, time.time()]
            elif (self.failedPasswords[request.origin][0] >= self.instance.conf["MaxLoginAttempts"]) and (time.time() - self.failedPasswords[request.origin][1] < 300):
                return self.generateError("400 Bad Request", etext="Too many login attempts!", return_to="/admin?login", httpheaders={"Set-Cookie": "pfAuthToken=; max-age=0"})
            user = self.instance.masterDB.users[request.form["user"].value.decode("utf-8")]
            if not user.exists:
                return self.generateError("400 Bad Request", etext="Invalid username/password combination.", return_to="/admin?login", httpheaders={"Set-Cookie": "pfAuthToken=; max-age=0"})
            hashed = self.instance.func.hashPassword(request.form["password"].value.decode("utf-8"), user.password[1])[0]
            if not user or hashed != user.password[0]:
                self.log("Denied login from {0} (user: {1})".format(request.origin, request.form["user"].value.decode("utf-8")), self.LOGLEV_WARN)
                self.failedPasswords[request.origin][0] += 1
                self.failedPasswords[request.origin][1] = time.time()
                return self.generateError("400 Bad Request", etext="Invalid username/password combination.", return_to="/admin?login", httpheaders={"Set-Cookie": "pfAuthToken=; max-age=0"})
            elif hashed == user.password[0]:
                self.log("Login accepted for user {1}, from {0}.".format(request.origin, request.form["user"].value.decode("utf-8")))
                del self.failedPasswords[request.origin]
                authToken = self.instance.func.genAuthToken(user, request.origin)
                return PyBoardObjects.Response(s="303 See Other", h={"Set-Cookie": "pfAuthToken={0}; max-age=86400".format(authToken), "Location": "/admin"}, r="")

    def logout(self, request):
        if request.authenticated:
            sid = request.cookies["pfAuthToken"].split("|")[0]
            try:
                del self.instance.modSessions[sid]
            except KeyError:
                pass
            self.log("User {0} logged out.".format(request.user), self.LOGLEV_WARN)
            self.instance.raise_event(PyBoardObjects.Event("PBUserLogout", cancellable=False))
            return PyBoardObjects.Response("303 See Other", {"Location": "/admin?login", "Set-Cookie": "pfAuthToken=; Max-Age=0"}, "")
        else:
            return PyBoardObjects.Response("303 See Other", {"Location": "/admin?login"}, "")

    def modViewActionDelegate(self, request):
        if request.query_dict["a"] == "delete_post":
            for i in ["bid", "post"]:
                if i not in request.query_dict:
                    return self.generateError("200 OK", etext=self.instance.lang["ERR_NOACTION"], return_to="/admin")
            if self.instance.masterDB.users[request.user].has_permission("boards.{0}.delete".format(request.query_dict["bid"])) and request.query_dict["bid"] in self.instance.boards and request.query_dict["post"].isdigit():
                try:
                    self.instance.boards[request.query_dict["bid"]].getPostById(int(request.query_dict["post"]))
                    self.instance.boards[request.query_dict["bid"]].deletePostsById(int(request.query_dict["post"]), rebuild=True, fileOnly="file" in request.query_dict)
                except AttributeError:
                    return self.generateError("200 OK", etext="This post doesn't exist!", return_to="/admin")
                return PyBoardObjects.Response("303 See Other", {"Location": "/{0}/index.html?mod".format(request.query_dict["bid"])}, "")
        elif request.query_dict["a"] == "delete_by_poster":
            if "ip" not in request.query_dict:
                return self.generateError("200 OK", etext=self.instance.lang["ERR_NOACTION"], return_to="/admin")
            if "bid" in request.query_dict:
                board = request.query_dict["bid"]
            else:
                board = False
            if board:
                self.instance.boards[board].deletePostsByPosterIP(request.query_dict["ip"])
                return PyBoardObjects.Response("303 See Other", {"Location": "/{0}/index.html?mod".format(request.query_dict["bid"])}, "")
            else:
                for b in self.instance.boards:
                    self.instance.boards[b].deletePostsByPosterIP(request.query_dict["ip"])
                return PyBoardObjects.Response("303 See Other", {"Location": request["Referer"] if request.contains("Referer") else "/admin"}, "")
        elif request.query_dict["a"] == "ban_poster":
            if "bid" in request.query_dict and request.query_dict["bid"] in self.instance.boards and self.instance.masterDB.users[request.user].has_permission("boards.{0}.ban"):
                return PyBoardObjects.Response("200 OK", {"Content-Type": "text/html"}, self.instance.func.page_format(template="f/banview.pyb", v=request.query_dict))
            elif self.instance.masterDB.users[request.user].has_permission("global.ban"):
                return PyBoardObjects.Response("200 OK", {"Content-Type": "text/html"}, self.instance.func.page_format(template="f/banview.pyb", v=request.query_dict))
        elif request.query_dict["a"] == "stick_thread":
            if "bid" in request.query_dict and request.query_dict["bid"] in self.instance.boards:
                if "post" in request.query_dict and request.query_dict["post"].isdigit():
                    if self.instance.masterDB.users[request.user].has_permission("boards.{0}.stick"):
                        res = self.instance.boards[request.query_dict["bid"]].toggleSticky(request.query_dict["post"])
                        if res == None:
                            return self.generateError("400 Bad Request", etext="No such thread.")
                        else:
                            self.instance.boards[request.query_dict["bid"]].getThreadById(request.query_dict["post"]).renderThread(True)
                            self.instance.boards[request.query_dict["bid"]].mkIndex(self.instance.conf["MaxPages"])
                            return PyBoardObjects.Response("303 See Other", {"Location": "/{0}/index.html?mod".format(request.query_dict["bid"])}, "")
                    else:
                        return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_PERMISSION_DENIED"])
                else:
                    return self.generateError("400 Bad Request", etext="Invalid thread ID.")
            else:
                return self.generateError("400 Bad Request", etext="No such board.")
        elif request.query_dict["a"] == "lock_thread":
            if "bid" in request.query_dict and request.query_dict["bid"] in self.instance.boards:
                if "post" in request.query_dict and request.query_dict["post"].isdigit():
                    if self.instance.masterDB.users[request.user].has_permission("boards.{0}.lock"):
                        res = self.instance.boards[request.query_dict["bid"]].toggleLock(request.query_dict["post"])
                        if res == None:
                            return self.generateError("400 Bad Request", etext="No such thread.")
                        else:
                            self.instance.boards[request.query_dict["bid"]].getThreadById(request.query_dict["post"]).renderThread(True)
                            self.instance.boards[request.query_dict["bid"]].mkIndex(self.instance.conf["MaxPages"])
                            return PyBoardObjects.Response("303 See Other", {"Location": "/{0}/index.html?mod".format(request.query_dict["bid"])}, "")
                    else:
                        return self.generateError("400 Bad Request", etext=self.instance.lang["ERR_PERMISSION_DENIED"])
                else:
                    return self.generateError("400 Bad Request", etext="Invalid thread ID.")
            else:
                return self.generateError("400 Bad Request", etext="No such board.")

    class fAction(PyBoardObjects.Extension.RequestHandler):
        def get(self, request):
            if request.authenticated:
                if request.query == "rebuild_all":
                    if self.instance.masterDB.users[request.user].has_permission("debug.rebuild_all"):
                        for b in self.instance.boards:
                            self.instance.boards[b].rebuild_all()
                        return self.generateError("200 OK", heading="OK", etext="Done.", return_to="/admin?tests")
                    else:
                        return self.generateError("403 Forbidden", etext=self.instance.lang["ERR_PERMISSION_DENIED"], return_to="/admin")
                if request.query == "reload_db":
                    if self.instance.masterDB.users[request.user].has_permission("debug.reload_db"):
                        self.instance.reload_database()
                        return self.generateError("200 OK", heading="OK", etext="Done.", return_to="/admin?tests")
                    else:
                        return self.generateError("403 Forbidden", etext=self.instance.lang["ERR_PERMISSION_DENIED"], return_to="/admin")
                if request.query == "reload_exts":
                    if self.instance.masterDB.users[request.user].has_permission("debug.reload_exts"):
                        for i in self.instance.ext_identifiers:
                            f = sys.modules[self.instance.extension_by_id(i).__module__].__file__
                            print f
                            self.instance.unload_extension(i)
                        return self.generateError("200 OK", heading="OK", etext="Reloaded ", return_to="/admin?tests")
                    else:
                        return self.generateError("403 Forbidden", etext=self.instance.lang["ERR_PERMISSION_DENIED"], return_to="/admin")
                if request.query == "flush_cache":
                    if self.instance.masterDB.users[request.user].has_permission("debug.flush_cache"):
                        self.instance.func.TemplateCache = deque()
                        return self.generateError("200 OK", heading="OK", etext="Flushed the template cache.", return_to="/admin?tests")
                    else:
                        return self.generateError("403 Forbidden", etext=self.instance.lang["ERR_PERMISSION_DENIED"], return_to="/admin")
                if request.query == "reload_config":
                    if self.instance.masterDB.users[request.user].has_permission("debug.reload_config"):
                        self.log("Reloading configuration. Don't interrupt me!", self.LOGLEV_WARN)
                        self.instance.conf.reload()
                        self.log("Refreshing topbar.", self.LOGLEV_WARN)
                        self.instance.masterDB.getTopbar(forceRebuild=True)
                        self.log("Refreshing constants.", self.LOGLEV_WARN)
                        self.instance.func._refreshConstants()
                        self.log("Done reloading configuration.", self.LOGLEV_WARN)
                        return self.generateError("200 OK", heading="OK", etext="Reloaded configuration.", return_to="/admin?tests")
                    else:
                        return self.generateError("403 Forbidden", etext=self.instance.lang["ERR_PERMISSION_DENIED"], return_to="/admin")
                if request.query == "reload_lang":
                    if self.instance.masterDB.users[request.user].has_permission("debug.reload_lang"):
                        self.instance.lang.reload()
                        return self.generateError("200 OK", heading="OK", etext="Reloaded language.", return_to="/admin?tests")
                    else:
                        return self.generateError("403 Forbidden", etext=self.instance.lang["ERR_PERMISSION_DENIED"], return_to="/admin")
                if request.query == "reload_core":
                    if self.instance.masterDB.users[request.user].has_permission("debug.reload_core"):
                        self.instance._reload_core_pages()
                        return self.generateError("200 OK", heading="OK", etext="Reloaded core pages.", return_to="/admin?tests")
                    else:
                        return self.generateError("403 Forbidden", etext=self.instance.lang["ERR_PERMISSION_DENIED"], return_to="/admin")
                if "a" in request.query_dict:
                    return self.modViewActionDelegate(request)
            else:
                return self.generateError("401 Unauthorized", etext=self.instance.lang["ERR_PERMISSION_DENIED"], return_to="/admin")
            return self.generateError("200 OK", etext=self.instance.lang["ERR_NOACTION"], return_to="/admin")

        def post(self, request):
            if not request.authenticated:
                return self.generateError("401 Unauthorized", etext=self.instance.lang["ERR_PERMISSION_DENIED"], return_to="/admin?login")
            elif "action" not in request.form:
                return self.generateError("200 OK", etext=self.instance.lang["ERR_NOACTION"], return_to="/admin")
            elif request.form["action"].value == "add_board":
                if not self.instance.masterDB.users[request.user].has_permission("boards.add"):
                    return self.generateError("403 Forbidden", etext=self.instance.lang["ERR_PERMISSION_DENIED"], return_to="/admin?boards")
                for i in ["id", "name"]:
                    if i not in request.form:
                        return self.generateError("200 OK", etext="You must fill out the form.", return_to="/admin?boards")
                newid = request.form["id"].value.decode("utf-8").strip("/")
                if not re.match(r"^[A-Za-z0-9]+$", newid):
                    return self.generateError("200 OK", etext="Invalid ID.", return_to="/admin?boards")
                name = request.form["name"].value.decode("utf-8").strip()
                if "sub" in request.form:
                    sub = request.form["sub"].value.decode("utf-8")
                else:
                    sub = ""
                if not self.instance.masterDB.addBoard(newid, name, sub):
                    return self.generateError("200 OK", etext="This board already exists!", return_to="/admin?boards")
                else:
                    return PyBoardObjects.Response("303 See Other", {"Location": "/admin?boards"}, "")
            elif request.form["action"].value == "del_board":
                uobj = self.instance.masterDB.users[request.user]
                try:
                    if not isinstance(request.form["delete"], list):
                        boardsToDelete = request.form["delete"].value if not request.form["delete"].filename else []
                    else:
                        boardsToDelete = [x.value for x in request.form["delete"] if not x.filename and x.value in self.instance.boards]
                except KeyError:
                    return self.redirect("/admin?boards")
                if isinstance(boardsToDelete, basestring):
                    boardsToDelete = [boardsToDelete]
                for x in boardsToDelete:
                    self.instance.masterDB.deleteBoard(x)
                return self.redirect("/admin?boards")
            elif request.form["action"].value == "ban_poster":
                pass
            else:
                return self.generateError("200 OK", etext="Invalid action.", return_to="/admin") 

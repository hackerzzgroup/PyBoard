# This file is a part of PyBoard.
# Copyright (c) 2011 - 2012 The Hackerzz Group, Inc.
# All rights reserved.
import fnmatch
import os
import re
import shutil
import time
from pystache import Renderer
import PyBoardObjects

DB_ENGINE = "NoDatabase"
DB_VERSION = "0"
DB_AUTHOR = "NoAuthor"
DB_IDENTIFIER = "net.pyboard.db"

class CFWrapper(object):
    def __init__(self, cf, fallback):
        self.conf = cf
        self.fallback = fallback

    def __getitem__(self, key):
        try:
            return self.conf[key]
        except KeyError:
            return self.fallback[key]

    def get(self, item, default):
        try:
            return self[item]
        except:
            return default

    def __setitem__(self, key, value):
        self.conf[key] = value

class Global(object):
    """Global database class."""
    def __init__(self, PyBoard):
        self.instance = PyBoard
        self.instance.log(self.instance.lang["DB_LOADING_BOARDS"])
        self._topbar = None
        self.users = self._UsersObject(self)
        self.groups = self._GroupsObject(self)
        self.bans = self._BansObject(self)
        self.dbInit()
        if len(self.users) == 0:
            u, p = self.instance.func.firstRun()
            if u is None or p is None:
                return
            else:
                self.users.add(u, p, ["__root__"])
                self.instance.log(self.instance.lang["FR_USER_CREATED"], 52346)

    def get_boards(self):
        b = {}
        for i in self.dbGetBoards():
            b[i["id"]] = self.instance._databaseImplementor.Board(self.instance, i["id"], i["name"], i["sub"], config=CFWrapper(cf=PyBoardObjects.Configuration(fp="boards/{0}.config.py".format(i["id"])), fallback=self.instance.conf))
        return b

    @property
    def topbar(self):
        """Delegate to getTopbar()"""
        return self.getTopbar()

    def getTopbar(self, forceRebuild=0, mod=None):
        """We assume setup has already been done here."""
        if not isinstance(mod, self.instance._databaseImplementor.Global._UsersObject.User):
            mod = self.users[mod]
        if not self._topbar or forceRebuild:
            bl = []
            for group in self.instance.conf["TopbarGroups"]:
                gs = {
                    "items": [],
                }
                for board in group:
                    if board in self.instance.boards:
                        if mod:
                            gs["items"].append(dict(
                                self.instance.boards[board].md.items() + [("mod", mod.has_permission("boards.{0}.modview"))]
                            ))
                        else:
                            gs["items"].append(self.instance.boards[board].md)
                if gs["items"]:
                    bl.append(gs)
            with open("{0}/templates/{1}/topbar.pyb".format(self.instance.workd, self.instance.conf["TemplateSet"])) as a:
                temp = a.read()
            result = Renderer().render(temp, {
                "groups": bl,
                "rb_items": [{
                    "name": v[0],
                    "loc": v[1],
                } for v in self.instance.conf["TopbarExternal"]]
            })
            if not mod:
                self.instance.log(self.instance.lang["DB_UPDATING_TOPBAR"])
                self._topbar = result # We don't want to cache a mod topbar!
            else:
                return result
        return self._topbar

    def addBoard(self, bid, name, sub):
        if bid in self.instance.boards:
            self.instance.log(self.instance.lang["WARN_BOARD_ALREADY_EXISTS"].format(bid), self.instance.LOGLEV_WARN)
            return None
        else:
            self.instance.log(self.instance.lang["DB_CREATE_NEW_BOARD"].format(bid))
            self.instance.boards[bid] = self.instance._databaseImplementor.Board(self.instance, bid=bid, bname=name, bsub=sub, config=CFWrapper(cf=PyBoardObjects.Configuration(fp="boards/{0}.config.py".format(bid)), fallback=self.instance.conf))
            self.dbAddBoard(bid, name, sub)
            self.instance.log(self.instance.lang["DB_PREPARING_DIRS"])
            os.mkdir(self.instance.workd + "/siteroot/{0}".format(bid))
            os.mkdir(self.instance.workd + "/siteroot/{0}/res".format(bid))
            os.mkdir(self.instance.workd + "/siteroot/{0}/img".format(bid))
            self.getTopbar(forceRebuild=True)
            self.instance.boards[bid].build_index()
            return True
    
    def deleteBoard(self, bid):
        if bid not in self.instance.boards:
            return
        else:
            del self.instance.boards[bid]
            self.dbDeleteBoard(bid)
            try:
                shutil.rmtree("{0}/{1}/".format(self.instance.docroot, bid))
                self.getTopbar(forceRebuild=True)
            except OSError:
                pass
            self.instance.log(self.instance.lang["DB_DELETED_BOARD"].format(bid))
            return bid

    # Method stubs #

    def dbInit(self):
        raise NotImplementedError("unhelpful exception message")

    def dbGetBoards(self):
        raise NotImplementedError("unhelpful exception message")

    def dbAddBoard(self, bid, name, sub):
        raise NotImplementedError("unhelpful exception message")

    def dbDeleteBoard(self, bid):
        raise NotImplementedError("unhelpful exception message")

    def dbGetUserCount(self):
        raise NotImplementedError("unhelpful exception message")

    def dbGetUserList(self):
        raise NotImplementedError("unhelpful exception message")

    def dbGetUser(self, name):
        raise NotImplementedError("unhelpful exception message")

    def dbAddUser(self, struct):
        raise NotImplementedError("unhelpful exception message")

    def dbDeleteUser(self, name):
        raise NotImplementedError("unhelpful exception message")

    def dbAddPermission(self, name, permission):
        raise NotImplementedError("unhelpful exception message")

    def dbRemovePermission(self, name, permission):
        raise NotImplementedError("unhelpful exception message")

    def dbAddGroupToUser(self, name, group):
        raise NotImplementedError("unhelpful exception message")

    def dbRemoveGroupFromUser(self, name, group):
        raise NotImplementedError("unhelpful exception message")

    def dbCheckBan(self, address):
        raise NotImplementedError("unhelpful exception message")

    def dbGetBans(self, address):
        raise NotImplementedError("unhelpful exception message")

    def dbSetBan(self, struct):
        raise NotImplementedError("unhelpful exception message")

    def dbDeleteBansAffecting(self, addr):
        raise NotImplementedError("unhelpful exception message")

    def dbDeleteBanById(self, banid):
        raise NotImplementedError("unhelpful exception message")

    def dbGetBanList(self, start, limit=0):
        raise NotImplementedError("unhelpful exception message")

    # API objects #

    class _GroupsObject(object):
        def __init__(self, parent):
            self.parent = parent

        def __len__(self):
            return len(self.parent.instance.conf["Groups"])

        def __contains__(self, item):
            if item in self.parent.instance.conf["Groups"]:
                return True
            return False

        def __getitem__(self, item):
            if item in self.parent.instance.conf["Groups"]:
                return self.Group(self.parent, item, self.parent.instance.conf["Groups"][item])

        class Group(object):
            def __init__(self, db, name, permissions):
                self.parent = db
                self.permissions = permissions
                self.name = name

            def __contains__(self, user):
                try:
                    u = self.parent.dbGetUser(user)
                except self.parent.DatabaseError:
                    return False
                if self.name in u["groups"]:
                    return True
                return False

    class _UsersObject(object):
        # stalNote: sqlite || concats text
        def __init__(self, parent):
            self.parent = parent

        def __contains__(self, item):
            try:
                self.parent.dbGetUser(item)
            except self.parent.DatabaseError:
                return False
            return True

        def __len__(self):
            return self.parent.dbGetUserCount()

        def __getitem__(self, item):
            try:
                u = self.parent.dbGetUser(item)
            except self.parent.DatabaseError:
                return self.Dummy()
            return self.User(self.parent.instance, u)

        def list(self):
            return [self.User(struct) for user in self.dbGetUserList()]

        def add(self, name, password, group=None, permissions=None):
            if name in self:
                raise self.parent.DatabaseError("User by that name already exists")
            p, s = self.parent.instance.func.hashPassword(password)
            self.parent.dbAddUser({
                "id": None,
                "name": name,
                "pass": p,
                "salt": s,
                "groups": group or [],
                "permissions": permissions or []
            })

        def __delitem__(self, item):
            if item in self:
                self.parent.dbRemoveUser(item)
            else:
                return

        class Dummy(object):
            group = 0
            name = 0
            permissions = []
            exists = False

            def has_permission(self, *args):
                return False

        class User(object):
            exists = True
            def __init__(self, instance, struct):
                self.instance = instance
                self.groups = struct["groups"]
                self.name = struct["name"]
                self.userperms = struct["permissions"]
                self.password = (struct["pass"], struct["salt"])
                self.id = struct["id"]

            @property
            def struct(self):
                return {
                    "id": self.id,
                    "name": self.name,
                    "pass": self.password[0],
                    "salt": self.password[1],
                    "groups": self.groups,
                    "permissions": self.userperms,
                }

            @property
            def all_permissions(self):
                grouplist = []
                for group in self.groups:
                    grouplist.extend(self.instance.masterDB.groups[group].permissions)
                grouplist.extend(self.userperms)
                return grouplist

            def add_permission(self, permission):
                if not re.match(r"^[a-zA-Z0-9\?\[\]\*\.]+$", permission):
                    raise ValueError("Invalid permission string...")
                self.userperms.append(permission)
                self.instance.masterDB.dbAddPermission(self.name, permission)

            def remove_permission(self, permission):
                if not re.match(r"^[a-zA-Z0-9\?\[\]\*\.]+$", permission):
                    raise ValueError("Invalid permission string...")
                if permission not in self.userperms:
                    return
                self.userperms.remove(permission)
                self.instance.masterDB.dbRemovePermission(self.name, permission)

            def add_group(self, group):
                if group in self.groups:
                    return
                self.groups.append(group)
                self.instance.masterDB.dbAddGroupToUser(self.name, group)

            def remove_group(self, group):
                if group not in self.groups:
                    return
                self.groups.remove(group)
                self.instance.masterDB.dbRemoveGroupFromUser(self.name, group)

            def has_permission(self, permission):
                t = time.clock()
                if "__root__" in self.groups:
                    return True
                has_exact = [None, None]
                has_wild = [None, None]
                has_minus_exact = [None, None]
                has_minus_wild = [None, None]
                # check group permissions
                grouplist = []
                for group in self.groups:
                    grouplist.extend(self.instance.masterDB.groups[group].permissions)
                for mask in grouplist:
                    if mask.startswith("-"):
                        if fnmatch.fnmatch(permission, mask):
                            has_minus_wild[0] = 1
                        if mask[1:] == permission:
                            has_minus_exact[0] = 1
                    else:
                        if fnmatch.fnmatch(permission, mask):
                            has_wild[0] = 1
                        if mask == permission:
                            has_exact[0] = 1
                for mask in grouplist:
                    if mask.startswith("-"):
                        if fnmatch.fnmatch(permission, mask):
                            has_minus_wild[1] = 1
                        if mask[1:] == permission:
                            has_minus_exact[1] = 1
                    else:
                        if fnmatch.fnmatch(permission, mask):
                            has_wild[1] = 1
                        if mask == permission:
                            return True
                # -exact overrules +wild AND +exact
                # -wild overrules +wild only
                # +exact overrules -wild
                self.instance.log("PermissionCheckTime " + str(time.clock() - t))
                if has_minus_exact[1]: # x0xxx1xx
                    return False
                elif has_minus_wild[1]: # x0xxx0x1
                    return False
                elif has_wild[1]: # x0x1x0x0
                    return True
                elif has_minus_exact[0]: # x0x100x0
                    return False
                elif has_exact[0]: # 10x000x0
                    return True
                elif has_minus_wild[0]: # 00x00010
                    return False
                elif has_wild[0]: # 00100000
                    return True

    class _BansObject(object):
        def __init__(self, parent):
            self.parent = parent
    
        def __contains__(self, item):
            if self.parent.dbCheckBan(item):
                return True
            else:
                return False
    
        def new(self, ipmask, expires=None, name=None, reason="-"):
            if expires > time.time():
                struct = {
                    "board": "*",
                    "id": None,
                    "address": ipmask,
                    "name": name,
                    "reason": reason,
                    "started": time.time(),
                    "expires": expires
                }
                return self.parent.dbSetBan(struct)
            else:
                return False
    
        def delete(self, par):
            if isinstance(par, basestring):
                self.parent.dbDeleteBansAffecting(par)
            elif isinstance(par, int):
                self.parent.dbDeleteBanById(par)
    
        def get_list(self, start=0, limit=0):
            return self.parent.dbGetBanList(start, limit)
    
        def __getitem__(self, item):
            item = str(item)
            try:
                structs = self.parent.dbGetBans(item)
                for ban in structs:
                    if ban["expires"] > time.time():
                        return ban
            except self.parent.DatabaseError:
                return False
            else:
                if not structs:
                    return False
            return False
    
    class DatabaseError(Exception):
        pass

class Board(object):
    """Board database class. Instantiated once for each board."""
    LOCK       = 2
    STICKY     = 3
    SHOWBAN    = 4
    BUMP       = 5
    SPOILER    = 6
    RAWHTML    = 7
    BANMESSAGE = 8
    NOBUMP     = 9
    
    DESC       = 0
    ASC        = 1
    
    def __init__(self, PyBoard, bid, bname, bsub, config=None):
        self.instance = PyBoard
        self.master = PyBoard.masterDB
        self.md = {
            "id": bid,
            "name": bname,
            "sub": bsub,
        }
        self.conf = CFWrapper(config, self.instance.conf)
        self.posts = self._PostsObject(self)
        self.threads = self._ThreadsObject(self)
        self.bans = self._BansObject(self)
        self.dbInit()
        self.update_counts()

    def make_post(self, struct, sage=False):
        thread = not struct["thread"]
        if not thread:
            if struct["thread"] not in self.threads:
                raise self.PostError(self.instance.lang["ERR_NONEXISTENT_THREAD"])
            if struct["sticky"]:
                self.dbSetAttribute(self.STICKY, struct["thread"], True)
            struct["sticky"] = None
            if struct["locked"]:
                self.dbSetAttribute(self.LOCK, struct["thread"], True)
            struct["locked"] = None
            if struct["autosage"]:
                self.dbSetAttribute(self.NOBUMP, struct["autosage"], True)
            struct["autosage"] = None
        struct["id"] = self.dbGetNextPostNumber()
        self.dbInsertPost(struct)
        if not thread:
            self.threads[struct["thread"]].renderThread(index=False)
        else:
            self.threads[struct["id"]].renderThread(index=False)
        if not sage and not thread:
            t = self.threads[struct["thread"]]
            if len(t) >= self.conf["BumpLimit"] and not t.attrs["autosaged"]:
                self.dbSetAttribute(self.NOBUMP, struct["thread"], 1)
            elif not t.attrs["autosaged"]:
                self.dbSetAttribute(self.BUMP, struct["thread"], struct["timestamp"])
        self.update_counts()
        self.build_index()
        return struct["id"], struct["thread"] or struct["id"]

    def build_index(self, tids=None, live=False, mod=None, page=0, user=None):
        if tids is None:
            tids = self.dbGetStickyIDs() + self.dbGetThreadIDs()
        ipages = [tids[i:i + self.conf["MaxPages"]] for i in range(0, len(tids), self.conf["MaxPages"])] or [[]]
        current_page = 0 if not live else page
        builtPages = []
        x = time.time()
        skel = {
            "board": self.md,
            "form": self.instance.func.generateForm(self, thread=0, mod=user),
            "mod": mod != None,
        }
        for page in ipages[current_page:self.conf["MaxPages"]]:
            fl = {
                "threads": [self.threads[thread].renderThread(True, user) for thread in page],
                "previous": [{"id": str(num), "location": num if num > 0 else "index"} for num in range(current_page)],
                "thispage": current_page or 0,
            }
            if len(ipages) > 1:
                fl["next"] = [{"id": x + current_page + 1} for x in range(len(ipages) - (current_page + 1))]
            v = dict(skel.items() + fl.items() + [("d", x)])
            tempfile = "{0}/tmp/index_{1}{2}".format(self.instance.workd, self.md["id"], int(x))
            if not live:
                with open(tempfile, "w+") as tmpfile:
                    tmpfile.write(self.instance.func.page_format(v=v, template="index.pyb"))
                os.rename(tempfile, "{0}/{1}/{2}.html".format(self.instance.docroot, self.md["id"], current_page or "index"))
                builtPages.append("{0}.html".format(current_page or "index"))
                current_page += 1
            else:
                v["topbar"] = self.instance.masterDB.getTopbar(forceRebuild=True, mod=user)
                return self.instance.func.page_format(v=v, template="index.pyb")
        for y in ipages[self.conf["MaxPages"]:]:
            for x in y:
                del self.threads[y]
        for f in os.listdir("{0}/{1}".format(self.instance.docroot, self.md["id"])):
            if os.path.isfile("{0}/{1}/{2}".format(self.instance.docroot, self.md["id"], f)) and f not in builtPages:
                os.remove("{0}/{1}/{2}".format(self.instance.docroot, self.md["id"], f))

    def update_counts(self):
        self.md["post_count"], self.md["thread_count"] = self.dbGetActivePostCounts()

    def save_image(self, md5, filename):
        self.dbSaveImage(md5, filename)

    def get_image(self, filename):
        return self.dbGetImage(filename)

    def check_image(self, md5):
        return self.dbCheckImage(md5)

    def get_attribute(self, attr, pid):
        if attr in [2, 3, 5, 9] and pid not in self.threads:
            raise self.DatabaseError("This is a thread-only attribute.")
        else:
            return self.dbGetAttribute(attr, pid)

    def set_attribute(self, attr, pid, state):
        if attr in [2, 3, 5, 9] and pid not in self.threads:
            raise self.DatabaseError("This is a thread-only attribute.")
        else:
            return self.dbSetAttribute(attr, pid, state)

    def rebuild_all(self):
        tids = self.dbGetStickyIDs() + self.dbGetThreadIDs()
        for tid in tids:
            try:
                self.threads[tid].renderThread(index=False)
            except self.DatabaseError:
                pass
        self.build_index()

    # Database method prototypes #

    def dbInit(self):
        raise NotImplementedError("unhelpful exception message")

    def dbGetStickyIDs(self):
        raise NotImplementedError("unhelpful exception message")

    def dbGetThreadIDs(self):
        raise NotImplementedError("unhelpful exception message")

    def dbGetPostIDs(self, start=0, limit=0, order=DESC):
        raise NotImplementedError("unhelpful exception message")

    def dbGetPostAndThreadIDs(self):
        raise NotImplementedError("unhelpful exception message")

    def dbSetAttribute(self, attr, pid, state):
        raise NotImplementedError("unhelpful exception message")

    def dbGetAttribute(self, attr, pid):
        raise NotImplementedError("unhelpful exception message")

    def dbGetPost(self, pid):
        raise NotImplementedError("unhelpful exception message")

    def dbGetPostsByAddress(self, address, start=0, limit=0):
        raise NotImplementedError("unhelpful exception message")

    def dbGetThread(self, tid):
        raise NotImplementedError("unhelpful exception message")

    def dbGetThreadsByAddress(self, address, start=0, limit=0):
        raise NotImplementedError("unhelpful exception message")

    def dbDeletePost(self, pid):
        raise NotImplementedError("unhelpful exception message")

    def dbGetNextPostNumber(self):
        raise NotImplementedError("unhelpful exception message")

    def dbInsertPost(self, struct):
        raise NotImplementedError("unhelpful exception message")

    def dbGetActivePostCounts(self):
        raise NotImplementedError("unhelpful exception message")

    def dbCheckBan(self, address):
        raise NotImplementedError("unhelpful exception message")

    def dbGetBans(self, address):
        raise NotImplementedError("unhelpful exception message")

    def dbSetBan(self, struct):
        raise NotImplementedError("unhelpful exception message")

    def dbDeleteBansAffecting(self, addr):
        raise NotImplementedError("unhelpful exception message")

    def dbDeleteBanById(self, banid):
        raise NotImplementedError("unhelpful exception message")

    def dbGetBanList(self, start, limit=0):
        raise NotImplementedError("unhelpful exception message")

    def dbCheckImage(self, md5):
        raise NotImplementedError("unhelpful exception message")

    def dbGetImage(self, filename):
        raise NotImplementedError("unhelpful exception message")

    def dbSaveImage(self, md5, filename):
        raise NotImplementedError("unhelpful exception message")

    def dbRemoveImage(self, filename):
        raise NotImplementedError("unhelpful exception message")

    # Post getter/deleter objects #

    class _PostsObject(object):
        def __init__(self, parent):
            self.parent = parent

        def by_address(self, addr, start, limit=0):
            try:
                structs = self.parent.dbGetPostsByAddress(addr, start, limit)
                if not structs:
                    return []
                return [PyBoardObjects.Post(self.parent.instance, self.parent.md["id"], x) for x in structs]
            except self.parent.PostNotFoundError:
                return None

        def all(self):
            return self.parent.dbGetPostIDs()

        def pop(self, item, fileOnly=False):
            if isinstance(item, basestring) and not item.isdigit():
                raise self.parent.DatabaseError("Invalid post ID.")
            struct = self.parent.dbGetPost(int(item))
            if not struct["thread"]:
                if fileOnly:
                    self.parent.dbDeletePost(int(item), fileOnly)
                    return PyBoardObjects.Post(self.parent.instance, self.parent.md["id"], struct)
                return self.parent.threads.pop(item) # delegate to _ThreadsObject
            else:
                if not self.parent.instance.raise_event(PyBoardObjects.Event("PBPostDelete", post=PyBoardObjects.Post(self.parent.instance, self.parent.md["id"], struct))).cancelled:
                    self.parent.dbDeletePost(int(item), fileOnly)
                    if struct["image.url"] != "*" and struct["image.url"] != None:
                        if not self.parent.dbGetImage(struct["image.url"]):
                            self.parent.dbRemoveImage(struct["image.url"])
                            try:
                                os.remove("{0}/{1}/img/{2}".format(self.parent.instance.docroot, self.parent.md["id"], struct["image.url"]))
                                os.remove("{0}/{1}/img/s{2}".format(self.parent.instance.docroot, self.parent.md["id"], struct["image.url"]))
                            except IOError:
                                raise self.parent.DatabaseWarning("Couldn't delete {1}/{0} for some reason.".format(struct["image.url"], self.parent.md["id"]))
                    self.parent.threads[struct["thread"]].renderThread(False)
                    self.parent.instance.raise_event(PyBoardObjects.Event("PBThreadBuilt", False, board=self.parent.md["id"], thread=struct["thread"]))
                    self.parent.build_index()
                    self.parent.instance.raise_event(PyBoardObjects.Event("PBIndexBuilt", False, board=self.parent.md["id"]))
                return PyBoardObjects.Post(self.parent.instance, self.parent.md["id"], struct)

        def __contains__(self, item):
            try:
                self.parent.dbGetPost(int(item))
                return True
            except self.parent.PostNotFoundError:
                return False

        def __delitem__(self, item):
            if isinstance(item, basestring) and item.endswith("@file"):
                self.pop(item.split("@")[0], fileOnly=True)
            else:
                self.pop(item)

        def __getitem__(self, item):
            if isinstance(item, basestring) and not item.isdigit():
                raise self.parent.DatabaseError("Invalid post ID.")
            struct = self.parent.dbGetPost(int(item))
            if not struct["thread"]:
                return self.parent.threads[item].op
            return PyBoardObjects.Post(self.parent.instance, self.parent.md["id"], struct)

    class _ThreadsObject(object):
        def __init__(self, parent):
            self.parent = parent

        def by_address(self, addr, start=0, limit=0):
            try:
                structs = self.parent.dbGetThreadsByAddress(addr, start, limit)
                return [PyBoardObjects.Thread(self.parent.instance, self.parent.md["id"], x) for x in structs]
            except self.parent.PostNotFoundError:
                return None

        def pop(self, item):
            if isinstance(item, basestring) and not item.isdigit():
                raise self.parent.DatabaseError("Invalid post ID.")
            structs = self.parent.dbGetThread(int(item))
            if not self.parent.instance.raise_event(PyBoardObjects.Event("PBThreadDelete", thread=PyBoardObjects.Thread(self.parent.instance, self.parent.md["id"], structs))).cancelled:
                post = None # make pylint shut up
                for post in structs:
                    self.parent.dbDeletePost(post["id"])
                    if post["image.url"] != "*" and post["image.url"] != None:
                        if not self.parent.dbGetImage(post["image.url"]):
                            self.parent.dbRemoveImage(post["image.url"])
                            try:
                                os.remove("{0}/{1}/img/{2}".format(self.parent.instance.docroot, self.parent.md["id"], post["image.url"]))
                                os.remove("{0}/{1}/img/s{2}".format(self.parent.instance.docroot, self.parent.md["id"], post["image.url"]))
                            except OSError:
                                raise self.parent.DatabaseWarning("Couldn't delete /{1}/img/{0} for some reason.".format(post["image.url"], self.parent.md["id"]))
                try:
                    os.remove("{0}/{1}/res/{2}.html".format(self.parent.instance.docroot, self.parent.md["id"], item))
                except IOError:
                    raise self.parent.DatabaseWarning("Couldn't delete /{1}/res/{0}.html for some reason.".format(post["image.url"], item))
                self.parent.build_index()
                self.parent.instance.raise_event(PyBoardObjects.Event("PBIndexRebuilt", False, board=self.parent.md["id"]))
            return PyBoardObjects.Thread(self.parent.instance, self.parent.md["id"], structs)

        def all(self):
            return self.parent.dbGetStickyIDs() + self.parent.dbGetThreadIDs()

        def __contains__(self, item):
            try:
                self.parent.dbGetThread(int(item))
                return True
            except self.parent.PostNotFoundError:
                return False

        def __delitem__(self, item):
            self.pop(item)

        def __getitem__(self, item):
            if isinstance(item, basestring) and not item.isdigit():
                raise self.parent.DatabaseError("Invalid thread ID.")
            struct = self.parent.dbGetThread(int(item))
            return PyBoardObjects.Thread(self.parent.instance, self.parent.md["id"], struct)

    class _BansObject(object):
        def __init__(self, parent):
            self.parent = parent

        def __contains__(self, item):
            if self.parent.dbCheckBan(item):
                return True
            else:
                return False

        def new(self, ipmask, expires=None, name=None, reason="-"):
            if expires > time.time():
                struct = {
                    "board": self.parent.md["id"],
                    "id": None,
                    "address": ipmask,
                    "name": name,
                    "reason": reason,
                    "started": time.time(),
                    "expires": expires
                }
                return self.parent.dbSetBan(struct)
            else:
                return False

        def delete(self, par):
            if isinstance(par, basestring):
                self.parent.dbDeleteBansAffecting(par)
            elif isinstance(par, int):
                self.parent.dbDeleteBanById(par)

        def get_list(self, start=0, limit=0):
            return self.parent.dbGetBanList(start, limit)

        def __getitem__(self, item):
            item = str(item)
            try:
                structs = self.parent.dbGetBans(item)
                for ban in structs:
                    if ban["expires"] > time.time():
                        return ban
            except self.parent.DatabaseError:
                return False
            else:
                if not structs:
                    return False
            return False

    # Database warnings and errors #

    class PostError(Exception):
        pass

    class DatabaseWarning(Warning):
        pass

    class DatabaseError(Exception):
        pass

    class PostNotFoundError(DatabaseError):
        def __init__(self, pid=None, m=None, address=None):
            if m is None and pid:
                m = "Post #{0} not found.".format(pid)
            elif m is None and address:
                m = "No posts by {0}.".format(address)
            super(Board.PostNotFoundError, self).__init__(m)

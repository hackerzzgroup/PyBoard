# SQLite3 backend for PyBoard.
# This code is copyright (c) 2011 - 2012 by the PyBoard Dev Team <stal@pyboard.net>
# All rights reserved.
import sqlite3
import PyBoardDatabase
import PyBoardObjects
import os
import threading
import time

class main(PyBoardObjects.Extension):
    DB_ENGINE = "SQLite3"
    DB_VERSION = "1.0"
    IDENTIFIER = "net.pyboard.db.sqlite3"

    def __init__(self, PyBoard):
        super(main, self).__init__(PyBoard)
        self.provideDatabase(self.DB_ENGINE, (Global, Board), {
            "name": self.DB_ENGINE,
            "version": self.DB_VERSION,
        })

class Global(PyBoardDatabase.Global):
    def dbInit(self):
        self._dbLock = threading.Lock()
        willInit = 0
        if not os.path.isfile("{0}/global.sqlite3".format(self.instance.datad)):
            willInit = 1
        self._dbHandle = sqlite3.connect("{0}/global.sqlite3".format(self.instance.datad))
        if willInit:
            with self._dbLock:
                self._dbHandle.execute("CREATE TABLE boards (id TEXT, name TEXT, sub TEXT)")
                self._dbHandle.execute("CREATE TABLE bans (id INTEGER PRIMARY KEY AUTOINCREMENT, ip TEXT, name TEXT, reason TEXT, started INT, expires INT)")
                self._dbHandle.execute("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, password TEXT, salt TEXT, groups TEXT, permissions TEXT)")
                self._dbHandle.execute("CREATE TABLE md (key TEXT, value TEXT)")
                self._dbHandle.execute("INSERT INTO md VALUES ('version',?)", (self.instance.conf["__version"],))
                self._dbHandle.commit()
            self.instance.log("Initialized database.")
        self.instance.log(self.instance.lang["DB_CONNECTED"].format(fn="{0}/global.sqlite3".format(self.instance.datad)))

    def userStruct(self, row):
        """Convert a SQLite row to a user_struct"""
        return {
            "id": row[0],
            "name": row[1],
            "pass": row[2],
            "salt": row[3],
            "groups": [x.replace("\r\n", ":") for x in row[4].replace("\\:", "\r\n").split(":")],
            "permissions": row[5].split(":"),
        }

    def dbGetBoards(self):
        cur = self._dbHandle.execute("SELECT id, name, sub FROM boards")
        res = cur.fetchall()
        if res:
            return [{
                "id": x[0],
                "name": x[1],
                "sub": x[2],
            } for x in res]
        else:
            return []

    def dbAddBoard(self, bid, name, sub):
        with self._dbLock:
            self._dbHandle.execute("INSERT INTO boards VALUES (?, ?, ?)", (bid, name, sub))
            self._dbHandle.commit()

    def dbDeleteBoard(self, bid):
        with self._dbLock:
            self._dbHandle.execute("DELETE FROM boards WHERE id = ?", (bid,))
            self._dbHandle.commit()
        os.remove("{0}/boards/{1}.sqlite3".format(self.instance.datad, bid))

    def dbGetUserCount(self):
        cur = self._dbHandle.execute("SELECT COUNT(0) FROM users")
        res = cur.fetchone()
        return res[0]

    def dbGetUserList(self, start=0, limit=0):
        if limit:
            cur = self._dbHandle.execute("SELECT * FROM users LIMIT ?, ?")
        else:
            cur = self._dbHandle.execute("SELECT * FROM users")
        res = cur.fetchall()
        return [self.userStruct(i) for i in res]

    def dbGetUser(self, name):
        cur = self._dbHandle.execute("SELECT * FROM users WHERE name = ?", (name,))
        res = cur.fetchone()
        if not res:
            raise self.DatabaseError("User not found")
        return self.userStruct(res)

    def dbAddUser(self, struct):
        with self._dbLock:
            tup = (struct["name"], struct["pass"], struct["salt"], ":".join([x.replace(":", r"\:") for x in struct["groups"]]), ":".join(struct["permissions"]))
            self._dbHandle.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, ?, ?)", tup)
            self._dbHandle.commit()

    def dbDeleteUser(self, name):
        with self._dbLock:
            self._dbHandle.execute("DELETE FROM users WHERE name = ?", (name,))
            self._dbHandle.commit()

    def dbAddPermission(self, name, permission):
        with self._dbLock:
            self._dbHandle.execute("UPDATE users SET permissions = (permissions || ?) WHERE name = ?", (permission, name))
            self._dbHandle.commit()

    def dbRemovePermission(self, name, permission):
        with self._dbLock:
            u = self.dbGetUser(name)
            u["permissions"].remove(permission)
            self._dbHandle.execute("UPDATE users SET permissions = ? WHERE name = ?", (":".join(u["permissions"]), name))
            self._dbHandle.commit()

    def dbAddGroupToUser(self, name, group):
        with self._dbLock:
            self._dbHandle.execute("UPDATE users SET groups = (groups || ?) WHERE name = ?", (group.replace(":", r"\:"), name))
            self._dbHandle.commit()

    def dbRemoveGroupFromUser(self, name, group):
        with self._dbLock:
            u = self.dbGetUser(name)
            u["groups"].remove(group)
            self._dbHandle.execute("UPDATE users SET groups = ? WHERE name = ?", (":".join([x.replace(":", r"\:") for x in u["groups"]]), name))
            self._dbHandle.commit()

    def dbCheckBan(self, address):
        with self._dbLock:
            self._dbHandle.execute("DELETE FROM bans WHERE expires < ?", (int(time.time()),))
            self._dbHandle.commit()
        cur = self._dbHandle.execute("SELECT * FROM bans WHERE (? LIKE REPLACE(REPLACE(ip, '\?', '_'), '*', '%')) AND expires > ? ORDER BY started DESC", (address, int(time.time())))
        res = cur.fetchone()
        if res:
            return True
        else:
            return False
    
    def dbGetBans(self, address):
        cur = self._dbHandle.execute("SELECT * FROM bans WHERE (? LIKE REPLACE(REPLACE(ip, '\?', '_'), '*', '%')) AND expires > ?", (address, int(time.time())))
        res = cur.fetchall()
        return [{
            "board": "*",
            "id": ban[0],
            "address": ban[1],
            "name": ban[2],
            "reason": ban[3],
            "started": ban[4],
            "expires": ban[5]
        } for ban in res]
    
    def dbSetBan(self, struct):
        with self._dbLock:
            tup = (struct["address"], struct["name"], struct["reason"], struct["started"], struct["expires"])
            self._dbHandle.execute("INSERT INTO bans VALUES (NULL,?,?,?,?,?)", tup)
            self._dbHandle.commit()
    
    def dbDeleteBansAffecting(self, addr):
        with self._dbLock:
            self._dbHandle.execute("DELETE FROM bans WHERE (? LIKE REPLACE(REPLACE(ip, '\?', '_'), '*', '%'))", (addr,))
            self._dbHandle.commit()
    
    def dbDeleteBanById(self, banid):
        with self._dbLock:
            self._dbHandle.execute("DELETE FROM bans WHERE id = ?", (banid,))
            self._dbHandle.commit()
    
    def dbGetBanList(self, start=0, limit=0):
        if limit:
            cur = self._dbHandle.execute("SELECT * FROM bans WHERE expires > ? ORDER BY started DESC LIMIT ?, ?", (int(time.time()), start, limit))
        else:
            cur = self._dbHandle.execute("SELECT * FROM bans WHERE expires > ? ORDER BY started DESC", (int(time.time()),))
        res = cur.fetchall()
        return [{
            "board": "*",
            "id": ban[0],
            "address": ban[1],
            "name": ban[2],
            "reason": ban[3],
            "started": ban[4],
            "expires": ban[5]
        } for ban in res]

class Board(PyBoardDatabase.Board):
    def dbInit(self):
        self._dbLock = threading.RLock()
        willInit = 0
        if not os.path.isfile("{0}/boards/{1}.sqlite3".format(self.instance.datad, self.md["id"])):
            willInit = 1
        self._dbHandle = sqlite3.connect("{0}/boards/{1}.sqlite3".format(self.instance.datad, self.md["id"]))
        if willInit:
            with self._dbLock:
                self._dbHandle.execute("CREATE TABLE md (key TEXT, value TEXT)")
                self._dbHandle.execute("CREATE TABLE bans (id INTEGER PRIMARY KEY AUTOINCREMENT, ip TEXT, name TEXT, reason TEXT, started INT, expires INT)")
                self._dbHandle.execute("CREATE TABLE posts (pid INTEGER PRIMARY KEY AUTOINCREMENT, tid INT, timestamp INT, poster_ip TEXT, poster_name TEXT,\
                                        poster_email TEXT, poster_trip TEXT, poster_capcode TEXT, post_subject TEXT, post_content TEXT, image_ref TEXT,\
                                        image_name TEXT, last_bump INT, locked INT, stuck INT, spoiler_image INT, raw_html INT, ban_message TEXT,\
                                        show_banned INT, autosage INT, hash TEXT)")
                self._dbHandle.execute("CREATE TABLE images (filename TEXT, md5 TEXT)")
                self._dbHandle.execute("INSERT INTO md VALUES ('bid',?)", (self.md["id"],))
                self._dbHandle.execute("INSERT INTO md VALUES ('name',?)", (self.md["name"],))
                self._dbHandle.execute("INSERT INTO md VALUES ('sub',?)", (self.md["sub"],))
                self._dbHandle.execute("INSERT INTO md VALUES ('version',?)", (self.instance.conf["__version"],))
                self._dbHandle.commit()
            self.instance.log("Initialized database.")
        self.instance.log(self.instance.lang["DB_CONNECTED"].format(fn="{0}/boards/{1}.sqlite3".format(self.instance.datad, self.md["id"])))

    _attrTables = [None, None, "locked", "stuck", "show_banned", "last_bump", "spoiler_image", "raw_html", "ban_message", "autosage"]

    @staticmethod
    def _makeStruct(p):
        """Creates a post_struct from a SQLite row"""
        return {
            "id": p[0],
            "thread": p[1],
            "timestamp": p[2],
            "poster.ip": p[3],
            "poster.name": p[4],
            "poster.email": p[5],
            "poster.tripcode": p[6],
            "poster.capcode": p[7],
            "subject": p[8],
            "body": p[9],
            "image.url": p[10],
            "image.filename": p[11],
            "lastbump": p[12],
            "locked": p[13],
            "sticky": p[14],
            "spoilerimage": p[15],
            "rawhtml": p[16],
            "banmessage": p[17],
            "showban": p[18],
            "autosage": p[19],
            "hash": p[20],
        }

    def dbGetStickyIDs(self):
        cur = self._dbHandle.execute("SELECT pid FROM posts WHERE tid IS NULL AND stuck = 1 ORDER BY last_bump DESC")
        return [x[0] for x in cur.fetchall()]

    def dbGetThreadIDs(self):
        cur = self._dbHandle.execute("SELECT pid FROM posts WHERE tid IS NULL AND stuck = 0 ORDER BY last_bump DESC")
        return [x[0] for x in cur.fetchall()]

    def dbGetPostIDs(self, start=0, limit=0, order=PyBoardDatabase.Board.DESC):
        if order:
            order = "ASC"
        else:
            order = "DESC"
        if limit:
            cur = self._dbHandle.execute("SELECT pid, timestamp FROM posts ORDER BY timestamp {0} LIMIT ?, ?".format(order), (start, limit))
        else:
            cur = self._dbHandle.execute("SELECT pid, timestamp FROM posts ORDER BY timestamp {0}".format(order))
        return cur.fetchall()

    def dbGetPostAndThreadIDs(self):
        cur = self._dbHandle.execute("SELECT pid, tid FROM posts ORDER BY timestamp DESC")
        return cur.fetchall()

    def dbSetAttribute(self, attr, pid, state):
        with self._dbLock:
            try:
                table = self._attrTables[attr]
            except IndexError:
                raise self.DatabaseWarning("Unrecognized attribute passed to dbSetAttrbute.")
            else:
                if not table:
                    raise self.DatabaseWarning("Unrecognized attribute passed to dbSetAttrbute.")
            self._dbHandle.execute("UPDATE posts SET {0} = ? WHERE pid = ?".format(table), (state, pid))
            self._dbHandle.commit()

    def dbGetAttribute(self, attr, pid):
        try:
            table = self._attrTables[attr]
        except IndexError:
            raise self.DatabaseError("No such attribute: {0}".format(attr))
        else:
            if not table:
                raise self.DatabaseError("No such attribute: {0}".format(attr))
        cur = self._dbHandle.execute("SELECT {0} FROM posts WHERE pid = ?".format(table), (pid))
        res = cur.fetchone()
        return res[0]

    def dbGetPost(self, pid):
        cur = self._dbHandle.execute("SELECT * FROM posts WHERE pid = ?", (pid,))
        res = cur.fetchone()
        if not res:
            raise self.PostNotFoundError(pid)
        else:
            return self._makeStruct(res)

    def dbGetPostsByAddress(self, address, start=0, limit=0):
        if limit:
            cur = self._dbHandle.execute("SELECT * FROM posts WHERE poster_ip = ? ORDER BY timestamp DESC LIMIT ?, ?", (address, start, limit))
        else:
            cur = self._dbHandle.execute("SELECT * FROM posts WHERE poster_ip = ? ORDER BY timestamp DESC", (address,))
        res = cur.fetchall()
        if not res:
            raise self.PostNotFoundError(address=address)
        else:
            return [self._makeStruct(x) for x in res]

    def dbGetThread(self, tid):
        cur = self._dbHandle.execute("SELECT * FROM posts WHERE pid = ? OR tid = ? ORDER BY pid", (tid, tid))
        res = cur.fetchall()
        if not res:
            raise self.PostNotFoundError(tid)
        else:
            return [self._makeStruct(x) for x in res]

    def dbGetThreadsByAddress(self, address, start=0, limit=0):
        if limit:
            cur = self._dbHandle.execute("SELECT pid FROM posts WHERE poster_ip = ? AND tid IS NULL ORDER BY timestamp DESC LIMIT ?, ?", (address, start, limit))
        else:
            cur = self._dbHandle.execute("SELECT pid FROM posts WHERE poster_ip = ? AND tid IS NULL ORDER BY timestamp DESC", (address,))
        res = cur.fetchall()
        if not res:
            raise self.PostNotFoundError(address=address)
        else:
            return [self.dbGetThread(x[0]) for x in res]

    def dbDeletePost(self, pid, fileOnly=False):
        with self._dbLock:
            if fileOnly:
                self._dbHandle.execute("UPDATE posts SET image_ref = '*', image_name = '*' WHERE pid = ?", (pid,))
                self._dbHandle.commit()
            else:
                self._dbHandle.execute("DELETE FROM posts WHERE pid = ?", (pid,))
                self._dbHandle.commit()

    def dbGetNextPostNumber(self):
        with self._dbLock:
            cur = self._dbHandle.execute("SELECT seq FROM sqlite_sequence WHERE name = 'posts'")
            res = cur.fetchone()
            if res:
                return res[0] + 1
            else:
                return 1

    def dbInsertPost(self, struct):
        with self._dbLock:
            tup = (struct["thread"], struct["timestamp"], struct["poster.ip"], struct["poster.name"], struct["poster.email"],
                   struct["poster.tripcode"], struct["poster.capcode"], struct["subject"], struct["body"], struct["image.url"],
                   struct["image.filename"], struct["lastbump"], struct["locked"], struct["sticky"], struct["spoilerimage"], struct["rawhtml"],
                   struct["banmessage"], struct["showban"], struct["autosage"], struct["hash"])
            self._dbHandle.execute("INSERT INTO posts VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", tup)
            self._dbHandle.commit()

    def dbGetActivePostCounts(self):
        with self._dbLock:
            cur = self._dbHandle.execute("SELECT COUNT(0) FROM posts")
            postcount = cur.fetchone()[0]
            cur = self._dbHandle.execute("SELECT COUNT(0) FROM posts WHERE tid IS NULL")
            threadcount = cur.fetchone()[0]
            return (postcount, threadcount)

    def dbCheckBan(self, address):
        with self._dbLock:
            self._dbHandle.execute("DELETE FROM bans WHERE expires < ?", (int(time.time()),))
            self._dbHandle.commit()
        cur = self._dbHandle.execute("SELECT * FROM bans WHERE (? LIKE REPLACE(REPLACE(ip, '\?', '_'), '*', '%')) AND expires > ? ORDER BY started DESC", (address, int(time.time())))
        res = cur.fetchone()
        if res:
            return True
        else:
            return False

    def dbGetBans(self, address):
        cur = self._dbHandle.execute("SELECT * FROM bans WHERE (? LIKE REPLACE(REPLACE(ip, '\?', '_'), '*', '%')) AND expires > ?", (address, int(time.time())))
        res = cur.fetchall()
        return [{
            "board": self.md["id"],
            "id": ban[0],
            "address": ban[1],
            "name": ban[2],
            "reason": ban[3],
            "started": ban[4],
            "expires": ban[5]
        } for ban in res]

    def dbSetBan(self, struct):
        with self._dbLock:
            tup = (struct["address"], struct["name"], struct["reason"], struct["started"], struct["expires"])
            self._dbHandle.execute("INSERT INTO bans VALUES (NULL,?,?,?,?,?)", tup)
            self._dbHandle.commit()

    def dbDeleteBansAffecting(self, addr):
        with self._dbLock:
            self._dbHandle.execute("DELETE FROM bans WHERE (? LIKE REPLACE(REPLACE(ip, '\?', '_'), '*', '%'))", (addr,))
            self._dbHandle.commit()

    def dbDeleteBanById(self, banid):
        with self._dbLock:
            self._dbHandle.execute("DELETE FROM bans WHERE id = ?", (banid,))
            self._dbHandle.commit()

    def dbGetBanList(self, start=0, limit=0):
        if limit:
            cur = self._dbHandle.execute("SELECT * FROM bans WHERE expires > ? ORDER BY started DESC LIMIT ?, ?", (int(time.time()), start, limit))
        else:
            cur = self._dbHandle.execute("SELECT * FROM bans WHERE expires > ? ORDER BY started DESC", (int(time.time()),))
        res = cur.fetchall()
        return [{
            "board": self.md["id"],
            "id": ban[0],
            "address": ban[1],
            "name": ban[2],
            "reason": ban[3],
            "started": ban[4],
            "expires": ban[5]
        } for ban in res]

    def dbCheckImage(self, md5):
        cur = self._dbHandle.execute("SELECT filename FROM images WHERE md5 = ?", (md5,))
        res = cur.fetchone()
        return res[0] if res else False

    def dbGetImage(self, filename):
        cur = self._dbHandle.execute("SELECT md5 FROM images WHERE filename = ?", (filename,))
        res = cur.fetchone()
        return res[0] if res else False

    def dbSaveImage(self, md5, filename):
        with self._dbLock:
            self._dbHandle.execute("INSERT INTO images VALUES (?, ?)", (filename, md5))
            self._dbHandle.commit()

    def dbRemoveImage(self, filename):
        with self._dbLock:
            self._dbHandle.execute("DELETE FROM images WHERE filename = ?", (filename,))
            self._dbHandle.commit()

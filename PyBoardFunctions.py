# This file is a part of PyBoard.
# Copyright (c) 2011 - 2012 The Hackerzz Group, Inc.
# All rights reserved.
from __future__ import division
import cgi
import crypt
import datetime
import hashlib
import math
import os
import pystache
import random
import re
import socket
import string
import subprocess
import sys
import threading
import time
from collections import deque
from string import ascii_letters, digits
import PyBoardObjects

allchars = ascii_letters + digits

if __name__ == "__main__":
    sys.exit("Nope!")

class Functions(object):
    """
    Documentation is for losers
    """
    iformats = {"jpeg": "jpg"}
    antispamfieldts = [
        '<input type="hidden" name="{0}" value="{1}">',
        '<div style="display:none;"><input type="hidden" name="{0}" value="{1}"></div>',
        '<input type="password" style="display:none;" name="{0}" value="{1}">',
        '<input type="text" style="display:none;" name="{0}" value="{1}">',
        '<input type="text" style="position:absolute;top:-1000px;left:-1000px" name="{0}" value="{1}">',
        '<input type="password" style="position:absolute;top:-1000px;left:-1000px" name="{0}" value="{1}">',
        '<input type="radio" style="position:absolute;top:-1000px;left:-1000px" name="{0}" value="{1}" checked="checked">',
        '<p style="display:none"><input type="checkbox" style="display:none;" name="{0}" value="{1}" checked="checked"></p>']

    def __init__(self, PyBoard):
        self.instance = PyBoard
        self.TemplateCache = deque()
        self.Image = Image()
        self.TemplateConstants = None
        self._refreshConstants()
        self.file_locks = {};

    def runPostProcess(self, post, bid, mod):
        if len("".join(post["body"].replace("\n", "").split())) > 4096 or len(post["body"].split("\n")) >= 50:
            raise self.PostError(self.instance.lang["ERR_POST_TOO_LONG"])
        elif len("".join(post["body"].replace("\n", "").split())) <= 0 and not post["image.url"]:
            raise self.PostError(self.instance.lang["ERR_POST_TOO_SHORT"])
        event = self.instance.raise_event(PyBoardObjects.Event("PBPostProcess", True, post=post, mod=mod, board=bid))              
        if event.cancelled:
            if event.cancelMessage:
                raise self.PostError(event.cancelMessage)
            else:
                raise self.PostError(self.instance.lang["ERR_UNKNOWN"])
        return event.post

    def dnsblCheck(self, ip):
        if ip.startswith("127.") or ip.startswith("192.168."):
            return False
        if self.instance.conf["DNSBLServers"]:
            self.instance.log("Looking up {0} in DNSBLs...".format(ip))
            a = ip.split(".")
            a.reverse()
            rip = ".".join(a)
            for x in self.instance.conf["DNSBLServers"]:
                try:
                    s = socket.gethostbyname("{0}.{1}".format(rip, x[0]))
                    stat = s.split(".")[-1]
                    if isinstance(x[1], int):
                        x[1] = [x[1]]
                    if int(stat) in x[1]:
                        return x[0]
                except socket.gaierror:
                    pass
            return False
        else:
            return False

    @staticmethod
    def file_size(filename, bytes=None):
        if not bytes:
            try:
                bytes = os.path.getsize(filename)
            except OSError:
                return "nonexistent"
        kb = bytes / 1024
        if kb > 1000:
            mb = kb / 1024
            return "{:03.2f} MB".format(mb)
        else:
            return "{:03.2f} KB".format(kb)

    def firstRun(self):
        self.instance.log("Looks like this is your first time running PyBoard.", 52346)
        self.instance.log("Would you like to create a new root user? [Y/n]", 52346)
        res = raw_input(">>> ")
        if not res.lower().startswith("y"):
            self.instance.log("Okay.", 52346)
            return (None, None)
        self.instance.log("Pick a username. [root]", 52346)
        uname = raw_input(">>> ").strip() or "root"
        password = None
        while not password:
            self.instance.log("Please pick a password for {0}.".format(uname), 52346)
            _pass = __import__("getpass").getpass(">>> ").strip()
            if len(_pass) > 4:
                self.instance.log("Retype the password to confirm.", 52346)
                _pass2 = __import__("getpass").getpass(">>> ").strip()
                if _pass == _pass2:
                    password = _pass
                    break
                else:
                    self.instance.log("Passwords did not match.".format(uname), 52346)
            else:
                self.instance.log("Password is too short.".format(uname), 52346)
        self.instance.log("Creating user...", 52346)
        return (uname, password)

    def generateForm(self, board, thread=0, mod=None):
        ts = int(time.time())
        if mod:
            uobj = self.instance.masterDB.users[mod]
        toolbox = [
            '<div class="text ft pm">',
            '<input class="inputfile" type="file" name="file">',
        ]
        if board.conf["SpoilerImages"]:
            toolbox.append("<p class='input-container'><input type='checkbox' tabindex='4' name='spoiler'> {0}</p>".format(self.instance.lang["SPOILER"]))
        if mod:
            if uobj.has_permission("boards.{0}.raw_html"):
                toolbox.append("<p class='input-container'><input type='checkbox' tabindex='4' name='raw_html'> {0}</p>".format(self.instance.lang["RAW_HTML"]))
            if uobj.has_permission("boards.{0}.sticky"):
                toolbox.append("<p class='input-container'><input type='checkbox' tabindex='4' name='sticky'> {0}</p>".format(self.instance.lang["STICK"]))
            if uobj.has_permission("boards.{0}.lock"):
                toolbox.append("<p class='input-container'><input type='checkbox' tabindex='4' name='lock'> {0}</p>".format(self.instance.lang["LOCK"]))
            if uobj.has_permission("boards.{0}.bump_lock"):
                toolbox.append("<p class='input-container'><input type='checkbox' tabindex='4' name='autosage'> {0}</p>".format(self.instance.lang["BUMP_LOCK"]))
        toolbox.append("</div><br>")
        if len(toolbox) > 3:
            toolbox[1] = '<input class="inputfile m" type="file" name="file">'
        fields = [
            {"field": '<input type="hidden" name="bid" value="{0}">'.format(board.md["id"])},
            {"field": '<input type="hidden" name="tid" value="{0}">'.format(thread)},
            {"field": '<input type="hidden" name="ts" value="{0}">'.format(ts)},
            {"field": '<input class="text" type="text" name="name" tabindex="2" placeholder="{0}"><br>'.format(self.instance.lang["ANONYMOUS"])},
            {"field": '<input class="text" type="text" name="email" tabindex="3" placeholder="{0}"><br>'.format(self.instance.lang["EMAIL"])},
            {"field": "".join(toolbox)},
            {"field": '<input class="text stext" type="text" name="subject" tabindex="5" placeholder="{0}"><input class="b" type="submit" value="{1}"><br>'.format(self.instance.lang["SUBJECT"], self.instance.lang["POST"])},
            {"field": '<textarea class="text area" placeholder="{0}" name="body" tabindex="1"></textarea><br>'.format(self.instance.lang["COMMENT"])},
        ]
        asfields, key = self.generateFields(ts)
        for n, v in asfields:
            fields.insert(random.randint(1, len(fields)), {"field": random.choice(self.antispamfieldts).format(n, v)})
        fields.insert(random.randint(1, len(fields)), {"field": '<input type="hidden" name="key" value="{0}">'.format(key)})
        return fields

    def generateFields(self, ts, maxin=8):
        num = random.randint(2, maxin)
        serverkey = self.instance.conf["AntiSpamSalt"]
        pairs = []
        key = "@" + str(ts)
        for x in xrange(num):
            pairs.append((self.make_string(random.randint(5, 18)), self.make_string(random.randint(7, 34))))
        pairs.sort(key=lambda x: x[0])
        for n, v in pairs:
            key += self.interweave(n * 2, v)
        key += serverkey
        hashed = hashlib.sha1(key).hexdigest()
        return (pairs, hashed)

    def genAuthToken(self, user, origin):
        usessions = sorted([x for x in self.instance.modSessions if x[0] == user], key=lambda x: x[1])
        usessions.reverse()
        while len(usessions) > self.instance.conf["SessionLimit"] - 1:
            self.instance.modSessions.remove(usessions.pop())
        while True:
            sid = self.make_string(5)
            if sid not in self.instance.modSessions:
                break
        times = int(math.floor(time.time()))
        r = self.make_string(8)
        token = hashlib.sha1(user.name + origin + self.instance.conf["ModLoginSalt"] + r).hexdigest()
        self.instance.modSessions[sid] = [user.name, times, r]
        for x, v in self.instance.modSessions.items():
            if times - v[1] >= 86400:
                del self.instance.modSessions[x]
        return "|".join([sid, token])

    @staticmethod
    def getRelativeTime(delta):
        base = " from now"
        if delta < 60: # 1 minute
            return "{0} second{1}".format(delta, "s" if delta > 1 else "") + base
        elif delta < 3600: # 1 hour
            minutes = delta // 60
            return "{0} minute{1}".format(minutes, "s" if minutes > 1 else "") + base
        elif delta < 86400: # 24 hours
            hours = (delta // 60) // 60
            minutes = (delta // 60) % 60
            return "{0} hour{2} and {1} minute{3}".format(hours, minutes, "s" if hours > 1 else "", "s" if minutes > 1 else "") + base
        elif delta < 604800: # 1 week
            days = ((delta // 60) // 60) // 24
            hours = ((delta // 60) // 60) % 60
            return "{0} day{2} and {1} hour{3}".format(days, hours, "s" if days > 1 else "", "s" if hours > 1 else "") + base
        elif delta < 2678400: # 1 month
            months = (((delta // 60) // 60) // 24) // 30
            days = (((delta // 60) // 60) // 24) % 30
            return "{0} month{2} and {1} day{3}".format(months, days, "s" if months > 1 else "", "s" if days > 1 else "") + base

    def get_time_offset(self, timestring):
        if re.match(r"^p(erma(nent)?)?|never$", timestring):
            return None # permaban
        l = re.findall(r"([0-9]+)(?:\s+?)?([A-z]+)", timestring, flags=re.I)
        d, s = 0, 0
        _cm = datetime.datetime.now().month - 1
        for num, token in l:
            if re.match(r"^y(ear(s)?)?$", token, flags=re.I):
                d += (int(num) * 365)
            elif re.match(r"^mo(nth(s)?)?$", token, flags=re.I):
                for i in xrange(int(num)):
                    d += self.months[(i + _cm) % 12]
            elif re.match(r"^w(eek(s)?)?$", token, flags=re.I):
                d += (int(num) * 7)
            elif re.match(r"^d(ay(s)?)?$", token, flags=re.I):
                d += int(num)
            elif re.match(r"^h(our(s)?)?$", token, flags=re.I):
                s += (int(num) * (60 * 60))
            elif re.match(r"^m(in(ute)?(s)?)?$", token, flags=re.I):
                s += (int(num) * 60)
            elif re.match(r"^s(ec(ond)?(s)?)$", token, flags=re.I):
                s += int(num)
        delta = datetime.timedelta(seconds=s, days=d)
        date = datetime.datetime.now() + delta
        return time.mktime(date.timetuple())

    def hashPassword(self, password, salt=None):
        if salt is None:
            salt = self.make_string(len(password))
        elif salt == "":
            hashed = hashlib.sha512(password).hexdigest()
            return (hashed, "")
        else:
            salt = str(salt)
        saltedPass = self.interweave(password, salt)
        hashed = hashlib.sha512(saltedPass).hexdigest()
        return (hashed, salt)

    def image(self, bid, struct, spoiler=False):
        if not struct["location"]:
            return {"has_image": False}
        elif struct["location"] == "*":
            return {"has_image": True, "image": False}
        else:
            return {
                "has_image": True,
                "image": True,
                "image_link": "{2}/{0}/img/{1}".format(bid, struct["location"], self.TemplateConstants["root"]),
                "image_filename": cgi.escape(struct["filename"]),
                "image_trunc_filename": (cgi.escape(struct["filename"][0:51]) + "...") if len(struct["filename"]) > 51 else (cgi.escape(struct["filename"])),
                "image_thumbnail": "{2}/{0}/img/s{1}".format(bid, struct["location"], self.TemplateConstants["root"]),
                "image_size": self.file_size(self.instance.docroot + "/{0}/img/{1}".format(bid, struct["location"])),
                "spoiler": spoiler,
            }

    @property
    @staticmethod
    def months():
        y = datetime.date.today().year
        if not y % 400:
            feb = 29
        elif not y % 100:
            feb = 28
        elif not y % 4:
            feb = 29
        else:
            feb = 28
        return [31, feb, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    def processImage(self, idata, bid):
        """Verify an image. Returns filename if successful, else raises an exception"""
        if len(idata.value) > self.instance.conf["MaxImageFileSize"]:
            raise self.ImageError(self.instance.lang["ERR_IMAGE_TOO_LARGE"].format(BYTES=self.instance.conf["MaxImageFileSize"]))
        ihash = hashlib.md5(idata.value).hexdigest()
        istat = self.instance.boards[bid].check_image(ihash)
        if not istat:
            try:
                i = self.Image.identify(imageData=idata.value)
            except Image.ImageError as e:
                raise self.ImageError(str(e))
            format = i["type"].lower()
            if format not in self.instance.conf["AllowedImageFormats"]:
                raise self.ImageError(self.instance.lang["ERR_IMAGE_FORMAT_INVALID"])
            if (i["width"] > self.instance.conf["MaxImagePixelSize"][0]) or (i["height"] > self.instance.conf["MaxImagePixelSize"][1]):
                raise self.ImageError(self.instance.lang["ERR_IMAGE_TOO_LARGE_PIXELS"].format(s=self.instance.conf["MaxImagePixelSize"]))
            nfn = "{0}{1}.{2}".format(int(math.floor(time.time())), str(int(ihash, 16))[0:3], self.iformats[format] if format in self.iformats else format)
            try:
                with open("{0}/{1}/img/".format(self.instance.docroot, bid) + nfn, "w+") as f:
                    for chunk in self.read_faster(idata.file, False):
                        f.write(chunk)
                self.Image.thumbnail(imageData=idata.value, maxSize=self.instance.conf["ThumbnailSize"], outputFile="{0}/{1}/img/s{2}".format(self.instance.docroot, bid, nfn))
                self.instance.boards[bid].save_image(ihash, nfn)
                idata.file.close()
                del idata
                return nfn, 0
            except Exception:
                if os.path.exists("{0}/{1}/img/".format(self.instance.docroot, bid) + nfn):
                    os.remove("{0}/{1}/img/".format(self.instance.docroot, bid) + nfn)
                if os.path.exists("{0}/{1}/img/s".format(self.instance.docroot, bid) + nfn):
                    os.remove("{0}/{1}/img/s".format(self.instance.docroot, bid) + nfn)
                raise
        else:
            return istat, 1

    def make_string(self, length):
        s = ""
        for x in xrange(length):
            s += random.choice(allchars)
        return s
    
    @staticmethod
    def interweave(s1, s2):
        while len(s1) != len(s2): # lengths must be same or the lambda will throw errors
            if len(s1) > len(s2):
                s2 += "@"
            else:
                s1 += "@"
            if len(s1) == len(s2):
                break
        return "".join(map(lambda x, y: x + y, s1, s2))

    def make_tripcode(self, inputstr, secure=False):
        if not self.instance.conf["TripcodeSalt"]:
            secure = False
        if not inputstr:
            return None
        elif secure:
            idex = len(inputstr) // 2
            mode = len(inputstr) % 2
            part1, part2 = inputstr[:idex], inputstr[idex:]
            if mode:
                part2 = part2[::-1]
            else:
                part1 = part1[::-1]
            salt = self.instance.conf["TripcodeSalt"]
            while salt < len(inputstr):
                salt += self.instance.conf["TripcodeSalt"]
            return "!!" + crypt.crypt(self.interweave("".join([part1, part2]), self.instance.conf["SecureTripSalt"]), )[-10:]
        else:
            inputstr = inputstr.decode('utf-8')
            inputstr = inputstr.encode("sjis", "ignore")
            inputstr = inputstr.replace('"', "&quot;").replace("'", "'").replace("<", "&lt;").replace(">", "&gt;")
            salt = re.sub(r"[^\.-z]", ".", (inputstr + "H..")[1:3])
            salt = salt.translate(string.maketrans(":;=?@[\\]^_`", "ABDFGabcdef"))
            return '!' + crypt.crypt(inputstr, salt)[-10:]

    def make_capcode(self, cc):
        if cc in self.instance.conf["Capcodes"]:
            return "<span class='capcode' style='color:{0}'>## {1}</span>".format(self.instance.conf["Capcodes"][cc], cc)

    def page_format(self, v={}, template=None, template_string="", tset=None):
        temp = None
        if template != None:
            if len(self.TemplateCache) >= 5:
                self.TemplateCache.popleft()
            for item in self.TemplateCache:
                if item[0] == template:
                    if not os.path.getmtime(self.instance.workd + "/templates/{0}/{1}".format(tset or self.instance.conf["TemplateSet"], template)) > item[2]:
                        temp = item[1]
                    break
            if not temp:
                if template not in self.file_locks:
                    self.file_locks[template] = threading.RLock()
                self.file_locks[template].acquire()
                try:
                    with open(self.instance.workd + "/templates/{0}/{1}".format(tset or self.instance.conf["TemplateSet"], template), "r") as plate:
                        temp = plate.read()
                    self.TemplateCache.append((template, temp, time.time()))
                    self.file_locks[template].release()
                except IOError:
                    if template in self.file_locks:
                        self.file_locks[template].release()
                        del self.file_locks[template]
                    return ""
        elif template_string != "":
            temp = template_string
        else:
            return ""
        if "topbar" not in v:
            v["topbar"] = self.instance.masterDB.topbar
        for x in v:
            if isinstance(v[x], basestring):
                v[x] = v[x]
                try:
                    v[x] = v[x].decode("utf-8")
                except:
                    pass
        v["constant"] = self.TemplateConstants
        formatted = pystache.render(temp, dict(self.instance.lang.getDict.items() + v.items())).replace("\t", "")
        return formatted.encode("utf-8");

    def read_faster(self, file, close=True):
        while True:
            c = file.read(16 * 4096)
            if c:
                yield c
            else:
                break
        if close:
            file.close()
        return

    def _refreshConstants(self):
        self.TemplateConstants = {
            "version": self.instance.conf["__version"],
            "static": self.instance.conf["StaticDomain"].strip("/") or ("/" + self.instance.conf["Subfolder"].strip("/") + "/static") if self.instance.conf["Subfolder"] else "/static",
            "eyecatch": self.instance.conf["EyecatchString"],
            "theme": self.instance.conf["DefaultStyle"],
            "root": ("/" + self.instance.conf["Subfolder"].strip("/")) if self.instance.conf["Subfolder"].strip("/") else ""
        }

    def verifyLogin(self, crumb, origin):
        pair = crumb.split('|')
        if pair[0] not in self.instance.modSessions:
            return False
        elif hashlib.sha1(self.instance.modSessions[pair[0]][0] + origin + self.instance.conf["ModLoginSalt"] + self.instance.modSessions[pair[0]][2]).hexdigest() == pair[1]:
            s = int(math.floor(time.time()))
            if s - self.instance.modSessions[pair[0]][1] >= 86400:
                del self.instance.modSessions[pair[0]]
                return False
            self.instance.modSessions[pair[0]][1] = s
            return True
        else:
            return False

    def verifyForm(self, fieldStorage):
        key = fieldStorage["key"].value
        af = self.instance.conf["__AllowedFields"] + self.instance.conf["AllowedFields"]
        n = sorted([k for k in fieldStorage if k not in af])
        f = [self.interweave(k * 2, fieldStorage[k].value) for k in n]
        k = "@" + fieldStorage["ts"].value + "".join(f) + self.instance.conf["AntiSpamSalt"]
        hashed = hashlib.sha1(k).hexdigest()
        if hashed == key:
            return True
        else:
            return False

    class ImageError(Exception):
        pass

    class PostError(Exception):
        pass

class Image(object):
    RETURN = 1337

    def __init__(self, **kwargs):
        if os.name == "nt":
            raise WindowsError("YES\n\nTHIS IS WINDOWS")
        self.toolnames = {}
        for toolname in ["identify", "convert"]:
            if toolname + "_path" in kwargs:
                self.toolnames[toolname] = kwargs[toolname + "_path"]
            else:
                for path in os.getenv("PATH").split(":"):
                    try:
                        if toolname in os.listdir(path):
                            self.toolnames[toolname] = os.path.abspath("{0}/{1}".format(path, toolname))
                            break
                    except OSError:
                        pass # don't break on dirs in PATH i can't access
                if toolname not in self.toolnames:
                    raise RuntimeError("Can't find `{0}`... is a recent version of ImageMagick installed?".format(toolname))

    def identify(self, imageFilename=None, imageData=None):
        if (not imageFilename) and (not imageData):
            raise self.ImageError("No input.")
        else:
            if imageData:
                pipe = subprocess.Popen(args=[self.toolnames["identify"], "-format", "width:%w|height:%h|type:%m|colorspace:%[colorspace]", "-"], stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                _out = pipe.communicate(imageData)
            elif imageFilename:
                pipe = subprocess.Popen(args=[self.toolnames["identify"], "-format", "width:%w|height:%h|type:%m|colorspace:%[colorspace]", os.path.abspath(imageFilename)], stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                _out = pipe.communicate()
            if pipe.returncode:
                raise self.ImageError("Can't identify image.")
            ret = {}
            for token in _out[0].strip().split("|"):
                pair = token.split(":", 1)
                if pair[1].isdigit():
                    ret[pair[0]] = int(pair[1])
                else:
                    ret[pair[0]] = pair[1]
            return ret

    def thumbnail(self, imageFilename=None, imageData=None, maxSize=(250, 250), outputFile=None, removeAnimation=True):
        if (not imageFilename) and (not imageData):
            raise self.ImageError("No input.")
        else:
            if imageFilename:
                identity = self.identify(imageFilename=imageFilename)
                if identity["width"] < maxSize[0] and identity["height"] < maxSize[1]:
                    maxSize = (identity["width"], identity["height"])
                if outputFile == self.RETURN:
                    pipe = subprocess.Popen(args=[self.toolnames["convert"], os.path.abspath(imageFilename) + ("[0]" if removeAnimation else ""), "-thumbnail", "{t[0]}x{t[1]}".format(t=maxSize), "-unsharp", "0x.5", "-"], stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                elif outputFile == None:
                    pipe = subprocess.Popen(args=[self.toolnames["convert"], os.path.abspath(imageFilename) + ("[0]" if removeAnimation else ""), "-thumbnail", "{t[0]}x{t[1]}".format(t=maxSize), "-unsharp", "0x.5", os.path.dirname(os.path.abspath(imageFilename)) + "/s" + os.path.basename(".".join(os.path.abspath(imageFilename).split(".")[:1])) + ".{0}".format(identity["type"].lower())], stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                else:
                    pipe = subprocess.Popen(args=[self.toolnames["convert"], os.path.abspath(imageFilename) + ("[0]" if removeAnimation else ""), "-thumbnail", "{t[0]}x{t[1]}".format(t=maxSize), "-unsharp", "0x.5", outputFile], stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                _out = pipe.communicate()
                if pipe.returncode:
                    raise self.ImageError("Thumbnail generation failed.")
                if outputFile == self.RETURN:
                    return _out[0]
                elif outputFile == None:
                    return os.path.dirname(os.path.abspath(imageFilename)) + "/s" + os.path.basename(".".join(os.path.abspath(imageFilename).split(".")[:1])) + ".{0}".format(identity["type"].lower())
                else:
                    return outputFile
            elif imageData:
                identity = self.identify(imageData=imageData)
                if identity["width"] < maxSize[0] and identity["height"] < maxSize[1]:
                    maxSize = (identity["width"], identity["height"])
                if outputFile == self.RETURN:
                    pipe = subprocess.Popen(args=[self.toolnames["convert"], "-" + ("[0]" if removeAnimation else ""), "-thumbnail", "{t[0]}x{t[1]}".format(t=maxSize), "-unsharp", "0x.5", "-"], stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                elif outputFile == None:
                    pipe = subprocess.Popen(args=[self.toolnames["convert"], "-" + ("[0]" if removeAnimation else ""), "-thumbnail", "{t[0]}x{t[1]}".format(t=maxSize), "-unsharp", "0x.5", os.path.abspath(".") + "/thumb" + ".{0}".format(identity["type"].lower())], stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                else:
                    pipe = subprocess.Popen(args=[self.toolnames["convert"], "-" + ("[0]" if removeAnimation else ""), "-thumbnail", "{t[0]}x{t[1]}".format(t=maxSize), "-unsharp", "0x.5", outputFile], stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                _out = pipe.communicate(imageData)
                if pipe.returncode:
                    raise self.ImageError("Thumbnail generation failed.")
                if outputFile == self.RETURN:
                    return _out[0]
                elif outputFile == None:
                    return os.path.abspath(".") + "/thumb" + ".{0}".format(identity["type"].lower())
                else:
                    return outputFile
            else:
                raise self.ImageError("Still no input.")

    class ImageError(Exception):
        pass

# this doesn't really work
# i included this because i might be leaking imports somewhere
# Copyright (c) 2012 stalcorp LLC.
from types import ModuleType
import time

class ConfigSerializer(object):
    blacklist = [
        "__builtins__",
        "__doc__",
        "__file__",
        "__name__",
        "__package__"
    ]
    baseIndent = "    "
    def serialize(self, object=None, outfile=None):
        if not outfile:
            s = ""
            if isinstance(object, ModuleType):
                for a, b in object.__dict__.items():
                    if a not in self.blacklist:
                        s += ("{} = ".format(a))
                        s += (self.serializeObject(b))
            else:
                return self.serializeObject(object)
        with open(outfile, "w+") as of:
            if isinstance(object, ModuleType):
                of.write(time.strftime("# Written at %X, %x\n"))
                for a, b in sorted(object.__dict__.items()):
                    if a not in self.blacklist:
                        print a
                        of.write("{} = ".format(a))
                        of.write(self.serializeObject(b) + "\n")
            else:
                of.write(self.serializeObject(object))

    def serializeObject(self, o):
        if o == None:
            return "None"
        so = [(basestring, self.serializeString), (list, self.serializeList), (dict, self.serializeDict), (tuple, self.serializeTuple)]
        for t, m in so:
            if isinstance(o, t):
                return m(o)
        return str(o)

    def serializeList(self, l):
        base = "[\n{}\n]"
        if len(l) < 1:
            return "[]"
        elif len(l) < 3 and all([isinstance(x, basestring) for x in l]):
            return "[{0}]".format(", ".join([self.serializeObject(x) for x in l]))
        strings = []
        for item in l:
            strings.append(self.baseIndent + self.serializeObject(item).replace("\n", "\n" + self.baseIndent) + ",")
        b = base.format(("\n").join(strings))
        return b

    def serializeTuple(self, t):
        base = "({})"
        if len(t) == 1:
            return "({},)".format(self.serializeObject(t))
        return base.format(", ".join([self.serializeObject(s) for s in t]))

    def serializeString(self, s):
        base = "\"{}\""
        baseraw = "r\"{}\""
        if "\\" in s:
            return baseraw.format(s.replace('"', r'\"'))
        return repr(s)

    def serializeDict(self, d):
        base = "{{\n{0}\n}}"
        keys = []
        lvd = []
        for k, v in d.items():
            keys.append("{}: {},".format(self.serializeString(k), self.serializeObject(v).replace("\n", "\n" + self.baseIndent)))
        for i in keys:
            lvd.append(self.baseIndent + i)
        return base.format("\n".join(lvd))

def serialize(object=None, outfile=None):
    ConfigSerializer().serialize(object, outfile)
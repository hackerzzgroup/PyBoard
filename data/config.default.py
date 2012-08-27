# PyBoard Default Configuration -- don't edit this!

# Salt used for making secure tripcodes. Set to None to disable secure tripcodes.
TripcodeSalt = "O*Y#@noNTC*#*TYCBG*O"
# Salt used for some anti-spam functions.
AntiSpamSalt = "349t7owycw83ebotTCW#$T"
# Maximum number of index pages to generate [b]
MaxPages = 10
# Filetypes of allowed images.
AllowedImageFormats = ['gif', 'jpeg', 'png']
# Maximum file size of an image in bytes.
MaxImageFileSize = 1048576
# File extensions of banners
BannerExtensions = ['jpg', 'png', 'gif']
# Used for salting login tokens
ModLoginSalt = 'agdsgvzsg'
# The domain below will be used for serving static content,
# set to None to disable (serve everything from a single domain)
# note: does nothing, but leave it set
StaticDomain = ""
# Directory I will use as root.
DocumentRoot = "siteroot"
# Displayed next to PyBoard version in the footer
EyecatchString = "Development channel: <a href='ircs://opsimathia.datnode.net:6697/hacking'>#hacking</a>"
# Subfolder I will serve from; i.e. http://pyboard.org/pb/ == pb/
# note: don't set this
Subfolder = ""
ThumbnailSize = (250, 250)
MaxImagePixelSize = (2000, 2000)
# DNS blackhole lists I will look up IPs with.
DNSBLServers = [
    ("dnsbl.tor.sectoor.de", [1]),
    ("dnsbl.sorbs.net", [2, 3, 4, 6, 9]),
]
Wordfilters = [
    [r"((http://)?([A-Za-z0-9\-]+?\.){1,127}([a-zA-z]){2,4}/?([!#$-;-\[\]_a-zA-Z~]+)?/{0,1})", r'<a href="\1" rel="outgoing">\1</a>'], # Links
    [r"\*\*(.+?)\*\*", r'<span class="spoiler">\1</span>'], # Spoilers
    [r"---(.+?)---", r'<span class="struck">\1</span>'], # Strikethrough
    [r"'''(.+?)'''", r'<span class="bold">\1</span>'], # Bold
    [r"''(.+?)''", r'<span class="ita">\1</span>'], # Italic
    [r"__(.+?)__", r'<span class="under">\1</span>'], # Underline
    [r"\^\^(.+?)\^\^", r'<sup class="super">\1</sup>'], # Superscript
    [r"==(.+?)==", r'<span class="heading">\1</span>'], # Headings
]
Groups = {
    "Admin": [
        "boards.*",
        "capcode.Admin.use",
        "capcode.Mod.use",
        "capcode.Janitor.use",
    ],
    "Mod": [
        "boards.*.*",
        "boards.ban",
        "capcode.Mod.use",
        "capcode.Janitor.use",
    ],
    "Janitor": [
        "boards.*.delete",
        "boards.*.modview",
        "boards.*.lock",
        "boards.*.autosage",
        "capcode.Janitor.use",
    ],
}
# Imageboard language
Language = "en-GB"
# Header containing the real IP of the request
RealIPHeader = None
# Header containing the scheme [http, https] of the request
ProtocolHeader = None
# Show an error traceback to users
ShowErrorTraceback = True
# If ShowErrorTraceback is off, serve this page when we error
GenericErrorFile = "static/error/500.html"
TemplateSet = "Default"
# Capcode to colour map - users also need the proper permission before they can use them
Capcodes = {
    "Admin": "red",
    "stal": "blue",
}
# Do not enable - broken regex
ReferrerCheck       = False
# These extensions will be skipped during loading
ExtensionBlacklist  = ["example.py"]
# Boards accessible to authenticated users only
AdminBoards = ["h"]
DefaultStyle = "classic"
DatabaseEngine = "SQLite3"
TopbarGroups = [
    ("b", "g"), ("feels", "h"), ("test",)
]
MaxLoginAttempts = 5
# most of these are per board configurable, see docs for a real list
HideSage = False
DoubleTrips = True
AutoNoko = True
SpoilerImages = True
StickyIndexMaxReplies = 1
IndexMaxReplies = 4
TimeBetweenPosts = 10
BumpLimit = 300
# these aren't
SessionLimit = 5
AllowedFields = [
    "bid",
    "tid",
    "ts",
    "name",
    "email",
    "file",
    "raw_html",
    "sticky",
    "lock",
    "spoiler",
    "autosage",
    "subject",
    "body",
    "key",
]
# served on 404s
GenericNotFoundFile = "static/error/404.html"
SessionPersistence = True
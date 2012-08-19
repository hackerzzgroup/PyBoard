# PyBoard language file.
## Console
PB_STARTUP                 = "Starting PyBoard (version {v})..."
PB_GOT_CWD                 = "The working directory is {d}."
PB_MAP_DIR                 = "Document root: {loc} -> {rem}."
PB_LOADING_BOARDS          = "Loading boards from databases..."
PB_DONE                    = "Done! [took {t} seconds] (c) 2011-2012 stalcorp LLC. http://pyboard.net"
PB_INIT_EXTENSION_CLASS    = "Initializing extension class {id}"
PB_IMPORTING_EXTENSION     = "Loading file {file}."
PB_EXTENSION_LOAD_START    = "Loading extensions..."
PB_EXTENSION_LOAD_DONE     = "Loaded {n} extension{s}."
PB_MISSING_IDENTIFIER      = "[ERROR]: Extension {e} is missing an identifier tag."
PB_INVALID_EXTENSION       = "[ERROR]: {f} is not a valid extension!"
PB_FOLDER_NONEXISTENT      = "[WARNING]: The folder {f} does not exist, creating it."
PB_BLACKLISTED_NS          = "[ERROR]: Extensions are not allowed to identifiers beginning with net.pyboard. Skipping {e}."
PB_IDENTIFIER_CONFLICT     = "[ERROR]: Name conflict for extension {i}. Skipping."
PB_FUNC_ALREADY_BOUND_URI  = "There is already a function bound to this URI!"
PB_COULDNT_HOOK_EVENT      = "Can't attach {id}, {func} to handlers!"
PB_BOUND_PAGE              = "Bound function {func} -> {uri}."
PB_UNLOAD_ATTEMPT          = "Attempting to unload {id}."
PB_UNLOAD_MODULE           = "Unloading module for {id}..."
PB_RELOAD_CORE_PAGES       = "Reloading core pages..."
FUNC_LOADED                = "PyBoardFunctions: started."
## Database
DB_CONNECTED               = "PyBoardDatabase: Connected {fn}."
DB_BOARD_OK                = "PyBoardDatabase: Loading board /{bid}/"
DB_PCOUNT_WARNING          = "PyBoardDatabase [WARNING]: Board /{bid}/ has no post count! Defaulting to 0."
DB_TCOUNT_WARNING          = "PyBoardDatabase [WARNING]: Board /{bid}/ has no thread count! Defaulting to 0."
DB_BOARD_DONE              = "PyBoardDatabase: Done!"
DB_LOADING_BOARDS          = "PyBoardDatabase: Loading boards..."
## Errors
ERR_POST_FAILED            = "Post failed:"
ERR_BAD_FORM               = "Your post was improperly submitted."
ERR_FORM_EXPIRED           = "Form expired. Refresh the page, and try your post again."
ERR_TRIPPED_DNSBL          = "You are listed in {}."
ERR_IMAGE_TOO_LARGE        = "Your file is too large (limit {BYTES} bytes)."
ERR_IMAGE_TOO_LARGE_PIXELS = "Your file is too large (limit {s[0]}x{s[1]})."
ERR_IMAGE_PROCESS_FAILED   = "An error occurred while processing your image."
ERR_IMAGE_REQUIRED         = "An image is required for new threads."
ERR_IMAGE_FORMAT_INVALID   = "This type of image is not allowed."
ERR_UNKNOWN                = "Post failed for no reason."
ERR_NONEXISTENT_THREAD     = "This thread does not exist."
ERR_NONEXISTENT_BOARD      = "This board does not exist."
ERR_DB_UNKNOWN             = "An unknown database error occurred."
ERR_NO_POST                = "You didn't make a post."
ERR_POST_TOO_LONG          = "Your post was too long."
ERR_POST_TOO_SHORT         = "Your post was too short."
ERR_WAIT_DAMMIT            = "You must wait 10 seconds between each post."
ERR_FLOOD_DETECTED         = "Wait a bit longer before posting the same thing again."
ERR_REFERRERS_PLS          = "Please enable HTTP referrers."
ERR_THREAD_LOCKED          = "You cannot post in a locked thread."
ERR_404                    = "The requested page was not found on the server."
ERR_403                    = "You do not have permission to view this page."
ERR_NOACTION               = "No action taken."
ERR_PERMISSION_DENIED      = "You don't have permission to do this."
ERR_POST_PERMISSION_DENIED = "You don't have permission to post on this board."
ERR_IN_EVENT               = "Exception caught in handler {handler} of {name} -"
ERR_SPAM                   = "You look like a bot."
ERR_NO_DATABASE            = "Can't find a suitable database backend. Exiting..."
ERR_HANDLER_RETURNED_NONE  = "Handler returned no response."
ERR_UNHANDLED              = "Caught an unhandled {type}: {msg}"
## WebUI
ADMIN                    = "Administration"
USERNAME                 = "Username"
PASSWORD                 = "Password"
LOGIN                    = "Log in"
LOGOUT                   = "Log out"
MP_SETTINGS              = "Settings"
MP_TESTS                 = "Tests"
MP_UNINSTALL             = "Uninstall PyBoard"
MP_BOARDS                = "Boards"
MP_BANS                  = "Bans"
MP_USERS                 = "Users"
POWERED_BY               = "Powered by PyBoard"
REPLY                    = "Reply"
OMIT                     = "{n} post{s} omitted. Click Reply to view."
OMIT_IMAGES              = "{n} post{s} ({i} image{s2}) omitted. Click Reply to view."
RETURN                   = "Return"
ANONYMOUS                = "Anonymous"
EMAIL                    = "E-mail address"
SUBJECT                  = "Subject"
SUBMIT                   = "Submit"
POST                     = "Post"
COMMENT                  = "Comment"
REPLYMODE                = "Posting mode: Reply."
NAME_POSTED_WITH         = "The name you were posting with was"
FROM                     = "from"
ALL_BOARDS               = "all boards"
BAN_FILED                = "Your ban was filed on"
YOU_ARE_BANNED_FROM      = "You are banned from"
BANNED                   = "Banned"
WAS_BANNED               = "(USER WAS BANNED FOR THIS POST)"
CONFIRM_BAN              = "Confirm ban"
IS_ABOUT_TO_BAN          = "You are about to ban"
NEW_BAN                  = "New ban"
BAN                      = "Ban"
BANS                     = "Bans"
ADDRESS                  = "Address"
STARTED                  = "Started"
EXPIRES                  = "Expires"
IONIZE                   = "Ionize"
NO_REASON                = "No reason"
BAN_PERMANENT            = "This ban will not expire."
FOR_FOLLOWING_REASON     = "for the following reason:"
SPOILER                  = "Spoiler image"
BAN_EXPIRES              = "You ban will expire on <b>{date}</b>, <b>{time}</b> from now."
FILE                     = "File"
DELETE                   = "Delete"
STICK                    = "Sticky"
UNSTICK                  = "Unsticky"
LOCK                     = "Lock"
UNLOCK                   = "Unlock"
RAW_HTML                 = "Raw HTML"
EXIT_MODVIEW             = "exit modview"
FILE_DELETED             = "File deleted."
BUMP_LOCK                = "Autosage"
BUMP_UNLOCK              = "-Autosage"
NEW_BOARD                = "New board"
CREATE                   = "Create"
SUB_HEAD                 = "Sub-heading"
BOARD_ID                 = "Board ID (url)"
ACTIVE_POSTS             = "Active posts"
ACTIVE_THREADS           = "Active threads"
NAME                     = "Name"
NO_BANS_TO_SHOW          = "No bans to show."
BOARD                    = "Board"
DELETE_SELECTED          = "Delete selected"
GLOBAL                   = "Global"
NEXT_50                  = "Next 50"
PREV_50                  = "Previous 50"
NO_BOARDS                = "No boards to show."
POST_TRUNCATED           = "This post is too long. Click [Reply] to view the full post."
## Command prefix
PREFIX="$"
## The emoji to bookmark a message
BOOKMARK_REACTION_EMOJI = "🔖"
MESSAGE_BOOKMARK_DELETED = ":white_check_mark: Bookmark {bookmark_name} deleted."
MESSAGE_BOOKMARK_DELETED_ERROR = ":no_entry_sign: Couldn't remove bookmark {bookmark_name}."
MESSAGE_BOOKMARK_ERROR = ":no_entry_sign: You cannot bookmark this message."
MESSAGE_BOOKMARK_NOT_FOUND = ":question: No bookmarks found for search term `{name}`."
MESSAGE_BOOKMARK_SUCCESS = ':white_check_mark: Bookmarked message {message_id} with name "{name}".'
MESSAGE_BOOKMARK_EXISTS = 'A bookmark with the name "{name}" already exists.'

## This is what the bot will report as
USER_AGENT="PasteBot/2.0"

## Minimum number of lines in a code block to be pasted
CODE_BLOCK_MIN_LINES = 5
## Max amount of lines before the message is edited
CODE_BLOCK_MAX_LINES = 15
## Max amount of message attachments to process
MAX_ATTACHMENTS = 3

## For removing language markers from code blocks
## We also use this to compare file extensions
LANGUAGES = [
    "gdscript",
    "gd",
    "tscn",
    "tres",
    "json",
    "csharp",
    "cs",
    "cpp",
    "h",
    "hpp",
    "swift",
    "rust",
    "rs",
    "glsl",
    "gdshader",
    "godot",
    "md",
    "ini",
    "bash",
    "java",
]

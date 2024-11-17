## Command prefix
PREFIX="$"

## This is what the bot will report as
USER_AGENT="PasteBot/1.1"

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

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import aiohttp
import json

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)

## Minimum number of lines in a code block to be pasted
CODE_BLOCK_MIN_LINES = 5
## Max amount of lines before the message is edited
CODE_BLOCK_MAX_LINES = 15
## For removing language markers from code blocks
## We also use this to compare file extensions
LANGUAGES = [
    "gdscript", "gd", "tscn", "tres",
    "json", "csharp", "cs", "cpp",
    "h", "swift", "rust", "rs",
    "glsl", "gdshader", "godot",
    "md", "ini", "bash", "java",
]

MAX_ATTACHMENTS = 3

# (message, content, filename)
upload_queue = []

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    await bot.tree.sync()


@bot.hybrid_command(name="paste", description="Bring up info about pasting")
async def paste(ctx):
    embed = discord.Embed(
        title=":clipboard: Pasting Code",
        description="""When sharing code with others, it's recommended you use a **pasting service**.
        Using a pasting service allows you to share code in a clean and readable format, without flooding the chat.
        This bot can help you with that, but you can also use any of the following paste sites directly:""",
        color=discord.Color.from_rgb(83, 164, 224),
    )
    embed.add_field(
        name=":link: Paste Sites",
        value="- [Pastes.dev](https://pastes.dev)\n- [Pastebin](https://pastebin.com)\n- [Hastebin](https://hastebin.com)\n- [GitHub Gist](https://gist.github.com)",
        inline=False,
    )
    embed.add_field(
        name="How to Use the Bot",
        value='1. Upload a code file as an attachment, or wrap your code in triple backticks (\`\`\`).\n2. If your code is long enough, the bot will automatically upload the content to [pastes.dev](https://pastes.dev) and reply with the link.',
        inline=False,
    )
    embed.set_footer(text="PasteBot v1.0")

    await ctx.send(embed=embed)


async def upload_paste():
    final_string = ""  # Holds the final response to send

    # Dictionary to group URLs and filenames by message
    message_to_urls = {}

    # Process the upload queue
    for message, content_to_paste, filename in upload_queue:
        print(f"Uploading paste for message: {message.id}")
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "text/swift",  # Set to appropriate language
                "User-Agent": "PasteBot/1.0",
            }
            try:
                # Send the paste content to the API
                async with session.post(
                    "https://api.pastes.dev/post",
                    data=content_to_paste,
                    headers=headers,
                ) as response:
                    if response.status == 201:
                        response_data = await response.json()
                        paste_key = response_data.get("key")
                        paste_url = f"https://pastes.dev/{paste_key}"

                        # Group URLs by message, including the filename
                        if message not in message_to_urls:
                            message_to_urls[message] = []
                        message_to_urls[message].append((paste_url, filename))

                    else:
                        print(f"Failed to create paste: {response.status}")
            except Exception as e:
                print(f"An error occurred: {e}")

    # Once all uploads are done, reply with the URLs
    for message, urls in message_to_urls.items():
        # Create the response string with filenames
        combined_urls = "\n".join(
            [f"`{filename}`: {url}" for url, filename in urls]
        )
        final_string = f":clipboard: Pasted **{len(urls)}** file(s):\n{combined_urls}"

        # Reply to the message with all URLs
        await message.reply(final_string)


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if "```" in message.content:
        
        upload_queue.clear()
        code_blocks = []

        line_count = len(message.content.split("\n"))
        if line_count < CODE_BLOCK_MIN_LINES:
            print("Not enough lines to paste")
            return

        # Split the message by code block markers
        parts = message.content.split("```")

        # Iterate over every second part (which should be code blocks)
        for i in range(1, len(parts), 2):
            code_block = parts[i]

            # Skip if the code block doesn't have a valid ending
            if "\n" not in code_block:
                continue

            # Remove language marker if present (e.g., `gdscript`)
            lines = code_block.split("\n")
            for lang in LANGUAGES:
                if lines[0].startswith(lang):
                    lines = lines[1:]
                    break

            formatted_block = "\n".join(lines).strip()  # Clean up the block

            # Add the formatted block to the code_blocks list
            code_blocks.append(formatted_block)


        # Combine the blocks with the specified separation
        if len(code_blocks) > 0:
            combined_code = "\n\n# ...\n\n".join(code_blocks)
            print(f"Combined code content:\n{combined_code}")

            block_line_count = len(combined_code.split("\n"))

            if (block_line_count - 5) < CODE_BLOCK_MIN_LINES:
                print("Code block is too small to paste")
                return
            upload_queue.append((message, combined_code, f"Code blocks"))

    attachment_index = 0

    for attachment in message.attachments:

        if attachment_index == MAX_ATTACHMENTS:
            print("Reached the maximum number of attachments")
            break

        filename = attachment.url.split("/")[-1].split("?")[0]
        print(f"Processing attachment: {filename}")
        print(f"Content type: {attachment.content_type}")

        if filename.split(".")[1] in LANGUAGES:
            # Extract the content of the file as a string
            file_bytes = await attachment.read()
            content_to_paste = file_bytes.decode("utf-8")

            if not content_to_paste or len(content_to_paste) < 10:
                print("Tried to paste an empty or small attachment")
                continue

            upload_queue.append((message, content_to_paste, filename))
            attachment_index += 1

    if len(upload_queue) > 0:
        await upload_paste()

    await bot.process_commands(message)


bot.run(os.environ["DISCORD_TOKEN"])

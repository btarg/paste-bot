import discord
from discord.ext import commands
import aiohttp
import os

# config is 1 level up from the cogs folder
from config import *

class Paste(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.upload_queue = []

    @commands.hybrid_command(name="paste", description="Bring up info about pasting")
    async def paste_info(self, ctx):
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
        embed.set_author(name=USER_AGENT.replace('/', ' v'), url="https://github.com/btarg/paste-bot")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        await self.handle_message(message)
        # await self.bot.process_commands(message)

    async def upload_paste(self):
        final_string = ""  # Holds the final response to send

        # Dictionary to group URLs and filenames by message
        message_to_urls = {}

        # Process the upload queue
        for message, content_to_paste, filename in self.upload_queue:
            print(f"Uploading paste for message: {message.id}")
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "text/swift",
                    "User-Agent": USER_AGENT,
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

    async def handle_message(self, message: discord.Message):
        if "```" in message.content:

            self.upload_queue.clear()
            code_blocks = []

            line_count = len(message.content.split("\n"))
            if line_count < CODE_BLOCK_MIN_LINES:
                print("Not enough lines to paste")
                return False

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

                block_line_count = len(combined_code.split("\n"))

                if (block_line_count - 5) < CODE_BLOCK_MIN_LINES:
                    print("Code block is too small to paste")
                    return False
                self.upload_queue.append((message, combined_code, f"Code blocks"))

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

                self.upload_queue.append((message, content_to_paste, filename))
                attachment_index += 1

        if len(self.upload_queue) > 0:
            await self.upload_paste()
            return True

        return False

async def setup(bot):
    await bot.add_cog(Paste(bot))
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

from config import *
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    await bot.tree.sync()

async def main():
    async with bot:
        for filename in os.listdir(os.path.join(os.path.dirname(__file__), "cogs")):
            if filename.endswith(".py"):
                module = f"cogs.{filename[:-3]}"
                print(f"Loading module {module}")
                try:
                    await bot.load_extension(module)
                except Exception as e:
                    print(f"Failed to load module {module}: {e}")

        await bot.start(os.environ["DISCORD_TOKEN"])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

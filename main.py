import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

from config import *
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

loaded_cogs = []

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    await bot.tree.sync()

async def main():
    global loaded_cogs
    async with bot:
        for filename in os.listdir(os.path.join(os.path.dirname(__file__), "cogs")):
            if filename.endswith(".py"):
                module = f"cogs.{filename[:-3]}"
                print(f"Loading module {module}")
                try:
                    await bot.load_extension(module)
                    loaded_cogs.append(module)

                except Exception as e:
                    print(f"Failed to load module {module}: {e}")

        await bot.start(os.environ["DISCORD_TOKEN"])

async def close_cogs():
    for cog in loaded_cogs:
        print(f"Unloading module {cog}")
        await bot.remove_cog(cog)
    await bot.close()

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
        asyncio.run(close_cogs())
        print("Closed.")

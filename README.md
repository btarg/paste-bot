# PasteBot
A simple [discord.py](https://discordpy.readthedocs.io/en/stable/) bot that allows you to paste code to [pastes.dev](https://pastes.dev) from Discord.

It also has support for personal cross-server bookmarks using SQLite.

# Setup
Put your bot token in a file called `.env`:
```env
DISCORD_TOKEN=your_token_here
```
Then install the dependencies:
```sh
pip install -r requirements.txt
```
And run the bot:
```sh
python main.py
```
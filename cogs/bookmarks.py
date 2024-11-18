import discord
from discord.ext import commands
import sqlite3
import asyncio

class Bookmarks(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ctx_menu = discord.app_commands.ContextMenu(
            name='Bookmark message',
            callback=self.bookmark_context_menu,
        )
        self.bot.tree.add_command(self.ctx_menu) # add the context menu to the tree

        # connect to database
        self.conn = sqlite3.connect('bookmarks.db')
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                name TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    async def bookmark_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        modal = BookmarkModal(self.conn, interaction.user.id, message.guild.id, message.channel.id, message.id)
        await interaction.response.send_modal(modal)

    @commands.hybrid_command(name="add_new_bookmark", description="Bookmark a message with a name")
    async def add_bookmark(self, ctx: commands.Context, guild_id: int, channel_id: int, message_id: int, name: str):
        user_id = ctx.author.id

        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO bookmarks (user_id, guild_id, channel_id, message_id, name) VALUES (?, ?, ?, ?, ?)', (user_id, guild_id, channel_id, message_id, name))
        self.conn.commit()

        await ctx.send(f'Bookmarked message {message_id} with name "{name}" for user {user_id}', ephemeral=True)

    @commands.hybrid_command(name="bookmark", description="Search your bookmarks by name", aliases=["search", "bookmarks", "b"])
    async def search_bookmarks(self, ctx: commands.Context, name: str):
        user_id = ctx.author.id
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, guild_id, channel_id, message_id, name FROM bookmarks WHERE user_id = ? AND name LIKE ?', (user_id, f'%{name}%'))
        rows = cursor.fetchall()

        if not rows or len(rows) == 0:
            await ctx.reply(f'No bookmarks found for search term `{name}`. :(', ephemeral=True)
            return

        for row in rows:
            bookmark_id, guild_id, channel_id, message_id, bookmark_name = row
            print(f"Found bookmark: {bookmark_name}")
            print(f"Guild: {guild_id}, Channel: {channel_id}, Message: {message_id}")

            try:
                channel = self.bot.get_channel(int(channel_id))
                message = await channel.fetch_message(int(message_id))
            except Exception as e:
                print(f"Failed to fetch message: {e}")
                return

            embed = discord.Embed(
                description=message.content, timestamp=message.created_at
            )
            embed.set_author(
                name=message.author.display_name + " (click to jump to message!)",
                icon_url=message.author.display_avatar.url,
                url=message.jump_url,
            )

            icon = message.guild.icon
            if icon:
                embed.set_footer(text=message.guild.name, icon_url=icon.url)
            else:
                embed.set_footer(text=message.guild.name)

            await ctx.reply(embed=embed, view=BookmarkView(self.conn, bookmark_id))

    async def cog_unload(self):
        self.conn.close()

class BookmarkModal(discord.ui.Modal, title="Add Bookmark"):
    def __init__(self, conn, user_id, guild_id, channel_id, message_id):
        super().__init__()
        self.conn = conn
        self.user_id = user_id
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.message_id = message_id

        self.name = discord.ui.TextInput(
            label="Bookmark Name",
            placeholder="Enter the name for your bookmark",
            required=True,
            max_length=64,
            min_length=1
        )
        self.add_item(self.name)

    async def on_submit(self, interaction: discord.Interaction):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM bookmarks WHERE user_id = ? AND name = ?', (self.user_id, self.name.value))
        count = cursor.fetchone()[0]
        if count > 0:
            await interaction.response.send_message(f'A bookmark with the name "{self.name.value}" already exists.', ephemeral=True)
        else:
            cursor.execute('INSERT INTO bookmarks (user_id, guild_id, channel_id, message_id, name) VALUES (?, ?, ?, ?, ?)', (self.user_id, self.guild_id, self.channel_id, self.message_id, self.name.value))
            self.conn.commit()
            await interaction.response.send_message(f'Bookmarked message {self.message_id} with name "{self.name.value}"', ephemeral=True)
        return

class BookmarkView(discord.ui.View):
    def __init__(self, conn, bookmark_id):
        super().__init__()
        self.conn = conn
        self.bookmark_id = bookmark_id

    @discord.ui.button(label='Delete Bookmark', style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM bookmarks WHERE id = ?', (self.bookmark_id,))
        self.conn.commit()
        await interaction.response.send_message('Bookmark deleted.', ephemeral=True)
        await interaction.message.delete()

async def setup(bot):
    await bot.add_cog(Bookmarks(bot))

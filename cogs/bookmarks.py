import discord
from discord.ext import commands
import sqlite3

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

        embeds = []
        for row in rows:
            bookmark_id, guild_id, channel_id, message_id, bookmark_name = row
            print(f"Found bookmark: {bookmark_name}")
            print(f"Guild: {guild_id}, Channel: {channel_id}, Message: {message_id}")

            try:
                guild = self.bot.get_guild(guild_id)
                channel = guild.get_channel(channel_id)
                message = await channel.fetch_message(message_id)
            except Exception as e:
                print(f"Failed to fetch message: {e}")
                continue

            embed = discord.Embed(
                description=message.content, timestamp=message.created_at,
                color=message.author.colour
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

            embeds.append((bookmark_id, bookmark_name, embed))

        if embeds:
            paginator = BookmarkPaginator(embeds, self.conn)
            await paginator.start(ctx)
        else:
            await ctx.send('No valid bookmarks found with that name.', ephemeral=True)

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

class BookmarkPaginator(discord.ui.View):
    def __init__(self, embeds, conn):
        super().__init__()
        self.embeds = embeds
        self.current_page = 0
        self.conn = conn

    async def start(self, ctx):
        self.message = await ctx.reply(content=self.get_page_content(), embed=self.embeds[self.current_page][2], view=self)

    def get_page_content(self):
        bookmark_name = self.embeds[self.current_page][1]
        return f":bookmark: **\"{bookmark_name}\"** ({self.current_page + 1}/{len(self.embeds)})"

    async def user_has_permission(self, user):
        if user.guild_permissions.manage_messages or user.guild_permissions.administrator:
            return True

        bookmark_id = self.embeds[self.current_page][0]
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id FROM bookmarks WHERE id = ?", (bookmark_id,))
        result = cursor.fetchone()
        return result and result[0] == user.id

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.user_has_permission(interaction.user.id):
            if self.current_page > 0:
                self.current_page -= 1
                await self.message.edit(content=self.get_page_content(), embed=self.embeds[self.current_page][2], view=self)
        await interaction.response.defer()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.user_has_permission(interaction.user):
            if self.current_page < len(self.embeds) - 1:
                self.current_page += 1
                await self.message.edit(content=self.get_page_content(), embed=self.embeds[self.current_page][2], view=self)
        await interaction.response.defer()

    @discord.ui.button(label="Delete Bookmark", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.user_has_permission(interaction.user):
            cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
            self.conn.commit()
            await interaction.response.send_message(":white_check_mark: Bookmark deleted.", ephemeral=True)
            await interaction.message.delete()
        else:
            await interaction.response.send_message(":no_entry_sign: You can't delete this bookmark.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Bookmarks(bot))

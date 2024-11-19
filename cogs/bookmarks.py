import discord
from discord.ext import commands
import sqlite3
from config import *

class Bookmarks(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ctx_menu = discord.app_commands.ContextMenu(
            name="Bookmark message",
            callback=self.bookmark_context_menu,
        )
        self.bot.tree.add_command(self.ctx_menu)  # add the context menu to the tree

        # connect to database
        self.conn = sqlite3.connect("bookmarks.db")
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                name TEXT NOT NULL
            )
        """
        )
        self.conn.commit()

    async def user_has_permission(
        self, user: discord.Member, to_check="id", check_value=None
    ):

        if hasattr(user, "guild"):
            if (
                user.guild_permissions.manage_messages
                or user.guild_permissions.administrator
            ):
                return True

        # Check against user ID by default
        if check_value is None:
            check_value = user.id

        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT user_id FROM bookmarks WHERE {to_check} = ?", (check_value,)
        )
        result = cursor.fetchone()
        if not result:
            return False
        return result and result[0] == user.id

    async def remove_bookmark_by_message(self, user: discord.Member, message_id: int):
        try:
            if await self.user_has_permission(self, user, "message_id", message_id):
                cursor = self.conn.cursor()
                cursor.execute(
                    "DELETE FROM bookmarks WHERE message_id = ? AND user_id = ?",
                    (message_id, user.id),
                )
                self.conn.commit()
                return True

        except Exception as e:
            await interaction.response.send_message(
                f":no_entry_sign: Failed to delete bookmark: {e}", ephemeral=True
            )
            print(f"Failed to delete bookmark: {e}")

        return False

    async def remove_bookmark_by_name(
        self, interaction: discord.Interaction, bookmark_name: str
    ):
        pass

    async def remove_bookmark_by_id(
        self, interaction: discord.Interaction, bookmark_id: int
    ):
        if await Bookmarks.user_has_permission(self, interaction.user, check_value=bookmark_id):
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
            if cursor.rowcount == 0:
                return False
            self.conn.commit()
            return True
        return False

    async def bookmark_context_menu(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        if message.author.bot or not message.guild:
            await interaction.response.send_message(MESSAGE_BOOKMARK_ERROR)

        modal = BookmarkModal(
            self.conn,
            interaction.user.id,
            message.guild.id,
            message.channel.id,
            message.id,
        )

        await interaction.response.send_modal(modal)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.guild:
            return

        if str(reaction.emoji) == BOOKMARK_REACTION_EMOJI:
            # we can't send a modal from here, so we just add the bookmark
            # with message author and timestamp as the name
            message_id = reaction.message.id
            name = (
                f"{reaction.message.author.name} - {reaction.message.created_at}"
            )

            result = await self.insert_bookmark(
                self,
                user.id,
                reaction.message.guild.id,
                reaction.message.channel.id,
                message_id,
                name,
            )
            if result:
                await reaction.message.channel.send(
                    MESSAGE_BOOKMARK_SUCCESS.format(**locals()),
                    mention_author=False,
                )

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.guild:
            return

        if str(reaction.emoji) == BOOKMARK_REACTION_EMOJI:
            result = await self.remove_bookmark_by_message(
                user, reaction.message.id
            )
            if result == False:
                await interaction.response.send_message(
                    MESSAGE_BOOKMARK_DELETED_ERROR.format(**locals()), ephemeral=True
                )

    @commands.hybrid_command(name="remove_bookmark", description="Remove a bookmark")
    async def remove_bookmark_command(self, ctx: commands.Context, bookmark_name: str):
        if await self.remove_bookmark_by_name(ctx.author, bookmark_name):
            await ctx.reply(MESSAGE_BOOKMARK_DELETED.format(**locals()), ephemeral=True)
        else:
            await ctx.reply(
                MESSAGE_BOOKMARK_DELETED_ERROR.format(**locals()), ephemeral=True
            )

    @commands.hybrid_command(
        name="bookmark",
        description="Search your bookmarks by name",
        aliases=["search", "bookmarks", "b"],
    )
    async def search_bookmarks(self, ctx: commands.Context, name: str):
        user_id = ctx.author.id
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, guild_id, channel_id, message_id, name FROM bookmarks WHERE user_id = ? AND name LIKE ?",
            (user_id, f"%{name}%"),
        )
        rows = cursor.fetchall()

        embeds = []
        for row in rows:
            bookmark_id, guild_id, channel_id, message_id, bookmark_name = row
            print(f"Found bookmark: {bookmark_name}")
            print(f"Guild: {guild_id}, Channel: {channel_id}, Message: {message_id}")

            try:
                guild = self.bot.get_guild(guild_id)
                channel = await guild.fetch_channel(channel_id)
                message = await channel.fetch_message(message_id)

                embed = discord.Embed(
                    description=message.content,
                    timestamp=message.created_at,
                    color=message.author.colour,
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

                embeds.append((bookmark_id, user_id, embed, bookmark_name))
            except Exception as e:
                print(f"Failed to fetch message: {e}")
                continue

        if embeds:
            paginator = BookmarkPaginator(embeds, self.conn)
            await paginator.start(ctx)
        else:
            await ctx.reply(MESSAGE_BOOKMARK_NOT_FOUND.format(**locals()), ephemeral=True)

    async def insert_bookmark(self, user_id, guild_id, channel_id, message_id, name):
        print("Inserting bookmark for user", user_id)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM bookmarks WHERE user_id = ? AND name = ?",
            (user_id, name),
        )
        count = cursor.fetchone()[0]
        print(count)
        if count or count > 0:
            print("Bookmark already exists")
            return False
        try:
            print("Inserting bookmark")
            cursor.execute(
                "INSERT INTO bookmarks (user_id, guild_id, channel_id, message_id, name) VALUES (?, ?, ?, ?, ?)",
                (
                    user_id,
                    guild_id,
                    channel_id,
                    message_id,
                    name,
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Failed to insert bookmark: {e}")
            return False

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
            min_length=1,
        )
        self.add_item(self.name)

    async def on_submit(self, interaction: discord.Interaction):
        print("Submitted modal")
        name = self.name.value
        message_id = self.message_id

        result = await Bookmarks.insert_bookmark(
            self,
            self.user_id,
            self.guild_id,
            self.channel_id,
            self.message_id,
            self.name.value,
        )
        response_message = MESSAGE_BOOKMARK_SUCCESS if result else MESSAGE_BOOKMARK_EXISTS

        await interaction.response.send_message(
            response_message.format(**locals()),
            ephemeral=True,
        )


class BookmarkPaginator(discord.ui.View):
    def __init__(self, embeds, conn):
        super().__init__()
        self.embeds = embeds
        self.current_page = 0
        self.conn = conn

    async def start(self, ctx):
        self.message = await ctx.reply(
            content=self.get_page_content(),
            embed=self.embeds[self.current_page][2],
            view=self,
        )

    def get_page_content(self):
        # index 3 is bookmark name
        return f':bookmark: **"{self.embeds[self.current_page][3]}"** ({self.current_page + 1}/{len(self.embeds)})'

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.primary)
    async def first_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.embeds[self.current_page][1]:
            self.current_page = 0
            await self.message.edit(
                content=self.get_page_content(),
                # index 2 is the embed object itself
                embed=self.embeds[self.current_page][2],
                view=self,
            )
        await interaction.response.defer()

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.primary)
    async def previous_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.embeds[self.current_page][1]:
            if self.current_page > 0:
                self.current_page -= 1
                await self.message.edit(
                    content=self.get_page_content(),
                    # index 2 is the embed object itself
                    embed=self.embeds[self.current_page][2],
                    view=self,
                )
        await interaction.response.defer()

    @discord.ui.button(emoji="🗑️", style=discord.ButtonStyle.danger)
    async def delete_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        bookmark_name = self.embeds[self.current_page][3]
        if await Bookmarks.remove_bookmark_by_id(
            self, interaction, self.embeds[self.current_page][0]
        ):
            await interaction.response.send_message(
                MESSAGE_BOOKMARK_DELETED.format(**locals()), ephemeral=True
            )
            # remove the bookmark embed and edit the original message
            del self.embeds[self.current_page]

            if len(self.embeds) == 0:
                await interaction.message.delete()
                return

            if self.current_page > 0:
                self.current_page -= 1
            else:
                self.current_page = 0
            await self.message.edit(
                content=self.get_page_content(),
                # index 2 is the embed object itself
                embed=self.embeds[self.current_page][2],
                view=self,
            )
        else:
            await interaction.response.send_message(
                MESSAGE_BOOKMARK_DELETED_ERROR.format(**locals()), ephemeral=True
            )

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.primary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.embeds[self.current_page][1]:
            if self.current_page < len(self.embeds) - 1:
                self.current_page += 1
                await self.message.edit(
                    content=self.get_page_content(),
                    # index 2 is the embed object itself
                    embed=self.embeds[self.current_page][2],
                    view=self,
                )
        await interaction.response.defer()

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary)
    async def last_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.embeds[self.current_page][1]:
            self.current_page = len(self.embeds) - 1
            await self.message.edit(
                    content=self.get_page_content(),
                    # index 2 is the embed object itself
                    embed=self.embeds[self.current_page][2],
                    view=self,
                )
        await interaction.response.defer()


async def setup(bot):
    await bot.add_cog(Bookmarks(bot))

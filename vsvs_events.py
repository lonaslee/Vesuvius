import discord
import vsvs_config
import traceback
import sys
from discord.ext import commands
from datetime import datetime


class GeneralEvents(commands.Cog):
    """listeners for general events"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
    

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        if hasattr(ctx.command, 'on_error'):
            return
        if isinstance(error, commands.NotOwner):
            msg = 'command for bot owner only.'
        if isinstance(error, commands.CommandNotFound):
            if ctx.message.content.count('`') > 1:
                return
            msg = 'command not found. try doing `help for a list of all commands'
        else:
            msg = ''
            await ctx.send(error)
        traceback.print_tb(error.__traceback__, None, sys.stdout)
        if msg:
            await ctx.send(msg)


class MessageDeleteEvent(commands.Cog):
    """cog for the `deletedmessage command"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._deld_msgs = []
        self.deld_num = 20

    @property
    def deleted_msgs(self) -> list[tuple[str, str]]:
        """list of the most recent del'd messages"""
        return self._deld_msgs

    @deleted_msgs.setter
    def deleted_msgs(self, value) -> None:
        # adds to a list, does not set list to one value
        self._deld_msgs.insert(0, value)
        if len(self.deleted_msgs) > self.deld_num:
            del self._deld_msgs[-1]

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author is self.bot.user:
            return
        self.deleted_msgs = (  # adds to
            f'{message.author}:  {message.content}',
            datetime.now().strftime('%m/%d, %H:%M:%S'),
        )

    @commands.command(name='snipe', aliases=['deletedmessage'])
    @commands.has_guild_permissions(
        administrator=True,
        ban_members=True,  # OR, not AND
        kick_members=True,
        manage_messages=True,
        mention_everyone=True,
    )
    async def deldmsgs(self, ctx: commands.Context, *, which: str = ''):
        """view stored deleted messages"""
        if not self.deleted_msgs:
            await ctx.send('no deleted messages since start-time')
            return
        elif not which:
            embed_msg = discord.Embed(
                title='last deleted message', colour=discord.Colour.red()
            )
            embed_msg.add_field(
                name=self.deleted_msgs[0][0], value=self.deleted_msgs[0][1]
            )
        elif which.isdigit() and len(which) != 18:
            which = int(which)
            suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
            if which > self.deld_num:
                await ctx.send(
                    f'index out of range: deleted messages only stored up to the '
                    f'{self.deld_num}{suffixes.get(self.deld_num, "th")} most recent message'
                )
                return
            if which > (l := len(self.deleted_msgs)):
                await ctx.send(f'currently only {l} deleted messages stored')
                return
            embed_msg = discord.Embed(
                title=f'{which}{suffixes.get(which, "th")} most recent deleted message',
                colour=discord.Colour.red(),
            )
            embed_msg.add_field(
                name=self.deleted_msgs[which - 1][0],
                value=self.deleted_msgs[which - 1][1],
            )
        else:
            if which == 'all':
                embed_msg = discord.Embed(
                    title=f'all stored deleted messages', colour=discord.Colour.red()
                )
                for tup in self.deleted_msgs:
                    embed_msg.add_field(name=tup[0], value=tup[1], inline=False)
            elif which in set(
                [m.name for m in ctx.guild.members]
                + [m.nick for m in ctx.guild.members]
                + [str(m) for m in ctx.guild.members]
                + [str(m.id) for m in ctx.guild.members]
            ):
                if which.isdigit():
                    which = ctx.guild.get_member(int(which))
                embed_msg = discord.Embed(
                    title=f'all stored deleted messages from {which}',
                    colour=discord.Colour.red(),
                )
                for m in self.deleted_msgs:
                    if str(which) in m[0]:
                        embed_msg.add_field(name=m[0], value=m[1], inline=False)
                if not embed_msg.fields:
                    await ctx.send(f'no stored deleted messages from {which}')
                    return
            else:
                await ctx.send('invalid user')
                return
        await ctx.send(embed=embed_msg)


def setup(bot: commands.Bot):
    bot.add_cog(GeneralEvents(bot))
    bot.add_cog(MessageDeleteEvent(bot))

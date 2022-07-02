from __future__ import annotations

import traceback
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from aiofiles import open as aopen

from extensions.definitions import ANSIColors as C


class GeneralEvents(commands.Cog):
    """listeners for general events"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.tree.on_error = self.on_app_command_error

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        if hasattr(ctx.command, 'on_error'):
            return

        if (
            isinstance(error, commands.CommandNotFound)
            and ctx.message.content.count('`') > 1
        ):
            return

        if not isinstance(
            error, (commands.CommandOnCooldown, commands.CommandNotFound)
        ):
            self.bot.get_command(ctx.command.name).reset_cooldown(ctx)

        await ctx.send(f'{C.B}{C.RED}{error}{C.E}')
        await self.log_exception(ctx, error)

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if interaction.command.on_error is not None:
            return
        await interaction.response.send_message(f'{C.B}{C.RED}{error}{C.E}')
        await self.log_exception(interaction, error)

    async def log_exception(
        self,
        ctx_info: commands.Context | discord.Interaction,
        error: commands.CommandError | app_commands.AppCommandError,
    ):
        now = datetime.now().strftime("%m/%d, %H:%M:%S")
        if isinstance(ctx_info, discord.Interaction):
            invoker = ctx_info.user
            message = ctx_info.command.name
        else:
            invoker = ctx_info.author
            message = ctx_info.message.content
        async with aopen(self.bot.files['discord_err'], 'a') as errfile:
            # TODO reverse file?
            await errfile.write(
                f'==================== {now} ====================\n'
                f'{ctx_info.guild.name if ctx_info.guild is not None else "DM"} '
                f'({ctx_info.channel.name if ctx_info.guild is not None else "with"}) '
                f'- {invoker}: {message}\n'
            )
            for item in traceback.StackSummary.from_list(
                traceback.extract_tb(error.__traceback__)
            ).format():
                await errfile.write(f'{item}')
            await errfile.write('--------------------\n\n')
        print(f"ERROR {now} -", error)


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
    @commands.guild_only()
    @commands.has_guild_permissions(
        administrator=True,
        ban_members=True,  # OR, not AND
        kick_members=True,
        manage_messages=True,
    )
    async def deldmsgs(self, ctx: commands.Context, *, which: str = ''):
        """snipe deleted messages. usage: `snipe [member | "all"]"""
        if not self.deleted_msgs:
            await ctx.send(f'{C.B}{C.RED}no deleted messages since start-time.{C.E}')
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
                    f'{C.B}{C.RED}index out of range: deleted messages only stored up to the '
                    f'{self.deld_num}{suffixes.get(self.deld_num, "th")} most recent message.{C.E}'
                )
                return
            if which > len(self.deleted_msgs):
                await ctx.send(
                    f'{C.B}{C.RED}currently only {len(self.deleted_msgs)} deleted messages stored.{C.E}'
                )
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
                    await ctx.send(
                        f'{C.B}{C.RED}no stored deleted messages from {which}.{C.E}'
                    )
                    return
            else:
                await ctx.send(f'{C.B}{C.RED}invalid user.{C.E}')
                return
        await ctx.send(embed=embed_msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralEvents(bot))
    await bot.add_cog(MessageDeleteEvent(bot))
    print('LOADED events')

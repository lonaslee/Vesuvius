from __future__ import annotations

import asyncio
import traceback
from datetime import datetime
from datetime import time as dt_time
from datetime import timedelta
from typing import TYPE_CHECKING

import aiohttp
import discord
from aiofiles import open as aopen
from discord import app_commands
from discord.ext import commands, tasks

from extensions import ANSIColors as C
from extensions import wotd
from extensions.definitions import holidays, tzi

if TYPE_CHECKING:
    from vesuvius import Vesuvius


class GeneralEvents(commands.Cog):
    """listeners for general events"""

    def __init__(self, bot: Vesuvius) -> None:
        self.bot = bot
        self.bot.tree.on_error = self.on_app_command_error

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context[Vesuvius], error: commands.CommandError
    ):
        if (
            isinstance(error, commands.CommandNotFound)
            and ctx.message.content.count('`') > 1
        ):
            return

        if hasattr(ctx.command, 'on_error'):
            return

        if not isinstance(
            error, (commands.CommandOnCooldown, commands.CommandNotFound)
        ):
            assert ctx.command is not None
            ctx.command.reset_cooldown(ctx)

        await ctx.send(f'{C.B}{C.RED}{error}{C.E}')
        await self.log_exception(ctx, error)
        raise error

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        print('\napp command error\n', error, '\n')
        assert interaction.command is not None
        if interaction.command.on_error is not None:
            return
        await interaction.response.send_message(f'{C.B}{C.RED}{error}{C.E}')
        await self.log_exception(interaction, error)

    async def log_exception(
        self,
        ctx_info: commands.Context[Vesuvius] | discord.Interaction,
        error: commands.CommandError | app_commands.AppCommandError,
    ):
        now = datetime.now().strftime("%m/%d, %H:%M:%S")
        if isinstance(ctx_info, discord.Interaction):
            assert ctx_info.command is not None
            invoker = ctx_info.user
            content = ctx_info.command.name
        else:
            invoker = ctx_info.author
            content = ctx_info.message.content

        async with aopen(self.bot.files['discord_err'], 'a') as errfile:
            # TODO reverse file?
            if ctx_info.guild is not None:
                assert not isinstance(
                    ctx_info.channel,
                    (discord.PartialMessageable, discord.DMChannel, type(None)),
                )
                message = f'{ctx_info.channel.name} - {invoker}: {content}\n'
            else:
                message = f'DM with - {invoker}: {content}\n'

            await errfile.write(message)
            for item in traceback.StackSummary.from_list(
                traceback.extract_tb(error.__traceback__)  # type: ignore
            ).format():
                await errfile.write(f'{item}')
            await errfile.write('--------------------\n\n')
        print(f"ERROR {now} -", error)


class EventLoggers(commands.Cog):
    def __init__(self, bot: Vesuvius) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        ...

    @commands.Cog.listener()
    async def on_typing(
        self,
        channel: discord.abc.Messageable,
        user: discord.User | discord.Member,
        when: datetime,
    ):
        ...

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(
        self, channel: discord.TextChannel, last_pin: discord.Message
    ):
        ...


class Tasks(commands.Cog):
    def __init__(self, bot: Vesuvius) -> None:
        self.bot = bot

        self.wotd_messages: list[discord.Message] = []
        self.holiday_messages: list[discord.Message] = []
        self.holiday_events: list[discord.ScheduledEvent] = []

        self.wotd.start()
        self.day_start.start()

    async def cog_unload(self) -> None:
        self.wotd.cancel()
        self.day_start.cancel()
        await super().cog_unload()

    @tasks.loop(time=dt_time(hour=0, tzinfo=tzi))
    async def day_start(self):
        print("NEW DAY")
        self.holiday_messages.clear()
        self.holiday_events.clear()
        if res := await self.holiday_today():
            ebd, img = res
            assert ebd.title is not None

            all_channels = await self.bot.database.get_all_channels()
            print("HOLIDAY", ebd.title)
            for channel, option in zip(
                [
                    self.bot.get_channel(id)
                    for id in [
                        row[3] for row in [guild_info for guild_info in all_channels]
                    ]
                ],
                [row[1] for row in [guild_info for guild_info in all_channels]],
            ):
                assert isinstance(channel, discord.TextChannel)
                msg = await channel.send(embed=ebd)
                self.holiday_messages.append(msg)
                if option:
                    event = await channel.guild.create_scheduled_event(
                        name=ebd.title,
                        description=f'Today is {ebd.title}!',
                        start_time=discord.utils.utcnow()
                        + timedelta(days=0, seconds=5),
                        end_time=discord.utils.utcnow() + timedelta(days=1),
                        image=img,
                        location=f'#{channel.name}',
                    )
                    self.holiday_events.append(event)

    @day_start.before_loop
    async def before_day_start(self):
        await self.bot.wait_until_ready()

    @staticmethod
    async def holiday_today() -> tuple[discord.Embed, bytes] | None:
        today = datetime.today()
        for date in holidays:
            if date[0] == today.month and date[1] == today.day:
                title, summary, url, image = await wotd.get_wiki_page(holidays[date][0])
                ebd = discord.Embed(
                    title=title,
                    description=f'{summary}\n{url}',
                    colour=discord.Colour.from_str('#' + holidays[date][1]),
                )
                if image:
                    ebd.set_image(url=image)
                async with aiohttp.request('GET', holidays[date][2]) as r:
                    event_image = await r.read()
                return ebd, event_image

    # ==================================================================================

    @tasks.loop(time=dt_time(19, tzinfo=tzi))
    async def wotd(self):
        print("WOTD started")
        self.wotd_messages.clear()
        ebd = await self.get_wotd()
        for channel_id in await self.bot.database.all_general_channels():
            channel = self.bot.get_channel(channel_id)
            assert isinstance(channel, discord.TextChannel)

            msg = await channel.send(embed=ebd)
            self.wotd_messages.append(msg)

    @wotd.before_loop
    async def before_wotd(self):
        await self.bot.wait_until_ready()

    async def get_wotd(self, redo: bool = False) -> discord.Embed:
        yesterday = await self.bot.database.get_wotd_yesterday()
        title, summary, url, image = await wotd.oneworder(self.bot.files['words_alpha'])
        ebd = discord.Embed(
            title=f'Word of the Day #{yesterday[0] + 1}: {title}',
            description=f'{summary}\n{url}',
            colour=discord.Colour.dark_teal(),
        )

        if image:
            ebd.set_image(url=image)

        if not redo:
            await self.bot.database.set_wotd_newday(title)

        return ebd

    @commands.command(name='wotdmanual')
    @commands.is_owner()
    @commands.guild_only()
    async def wotdmanual(self, ctx: commands.Context[Vesuvius]):
        self.wotd_messages.clear()
        await ctx.send(f'{C.B}{C.RED}wotd manual start. DO THE DB{C.E}')
        ebd = await self.get_wotd()
        for channel_id in await self.bot.database.all_general_channels():
            channel = self.bot.get_channel(channel_id)
            assert isinstance(channel, discord.TextChannel)

            msg = await channel.send(embed=ebd)
            self.wotd_messages.append(msg)
        await ctx.send(f'{C.B}{C.BOLD_GREEN}done.{C.E}')

    @commands.command(name='wotdnew')
    @commands.is_owner()
    @commands.guild_only()
    async def wotdnew(self, ctx: commands.Context[Vesuvius]):
        def chk(m: discord.Message):
            return m.author == ctx.author and m.channel == ctx.channel

        await ctx.send(
            f"{C.B}{C.BOLD_RED}are you sure you want to change today's wotd?{C.E}"
        )
        try:
            m = await self.bot.wait_for('message', check=chk, timeout=10)
        except asyncio.TimeoutError:
            await ctx.send(f'{C.B}{C.RED}wotd redo cancelled.{C.E}')
            return
        if m.content == 'yes':
            ebd = await self.get_wotd(True)
            for k, channel_id in enumerate(
                await self.bot.database.all_general_channels()
            ):
                channel = self.bot.get_channel(channel_id)
                assert isinstance(channel, discord.TextChannel)

                msg = await (
                    await channel.fetch_message(self.wotd_messages[k].id)
                ).edit(embed=ebd)
                self.wotd_messages[k] = msg
            await ctx.send(f'{C.B}{C.BOLD_GREEN}done.{C.E}')
        else:
            await ctx.send(f'{C.B}{C.RED}cancelled.{C.E}')


async def setup(bot: Vesuvius):
    await bot.add_cog(GeneralEvents(bot))
    # await bot.add_cog(MessageSentEvent(bot))
    await bot.add_cog(Tasks(bot))
    print('LOADED events')

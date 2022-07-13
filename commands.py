from __future__ import annotations

import asyncio
from datetime import datetime
from io import BytesIO
from time import time
from typing import TYPE_CHECKING, Literal, Optional, TypeGuard

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image

from extensions import ANSIColors as C
from extensions.definitions import owner_bypass

if TYPE_CHECKING:
    from vesuvius import Vesuvius


class OwnerCommands(commands.Cog):
    """commands for owner to use"""

    def __init__(self, bot: Vesuvius):
        self.bot = bot

    @commands.command(name='exit')
    @commands.is_owner()
    async def exit(self, ctx: commands.Context[Vesuvius]):
        """close the event loop"""

        if await self.confirm(ctx, 'exit'):
            return
        await ctx.send(f'{C.B}{C.BOLD_YELLOW}good bye!{C.E}')
        print("EXITING on exit command")
        await self.bot.close()

    @commands.command(name='reload', aliases=['r'])
    @commands.is_owner()
    async def reload(
        self,
        ctx: commands.Context[Vesuvius],
        extension: Optional[
            Literal['all', 'commands', 'events', 'features', 'games', 'testing']
        ],
    ):
        if not extension:
            extension = self.bot.last_reload
        self.bot.last_reload = extension
        await ctx.send(f'{C.B}{C.BOLD_GREEN}Reloading {C.YELLOW}{extension}.{C.E}')
        print(f'RELOADING {extension}')
        if extension == 'all':
            await self.bot.reload_extension('commands')
            await self.bot.reload_extension('events')
            await self.bot.reload_extension('features')
            await self.bot.reload_extension('games')
            await self.bot.reload_extension('testing')
            return
        await self.bot.reload_extension(extension)

    @commands.command(name='sync')
    @commands.is_owner()
    async def sync_tree(
        self,
        ctx: commands.Context[Vesuvius],
        scope: Literal['local', 'global'] = 'local',
    ):
        msg = await ctx.send(f'{C.B}{C.BOLD_YELLOW}syncing...{C.E}')
        synced_commands = ', '.join(
            [
                str(cmd)
                for cmd in (
                    await self.bot.tree.sync(
                        guild=(
                            None
                            if scope == 'global'
                            else discord.Object(972593245005705297)
                        )
                    )
                )
            ]
        )
        msg = await msg.edit(
            content=f'{C.B}{C.BOLD_GREEN}synced {C.WHITE}{synced_commands}{C.BOLD_GREEN}!{C.E}'
        )

    @app_commands.command()
    @app_commands.guilds(972593245005705297)
    async def setstatus(
        self,
        interaction: discord.Interaction,
        status: Literal['online', 'idle', 'do not disturb', 'invisible'],
    ):
        """set the status of the bot. usage: `setstatus {online, idle, dnd, offline}"""
        assert interaction.guild is not None
        activity_before = interaction.guild.me.activity
        match status:
            case 'online':
                sts = discord.Status.online
            case 'invisible':
                sts = discord.Status.invisible
            case 'do not disturb':
                sts = discord.Status.do_not_disturb
            case 'idle':
                sts = discord.Status.idle
        await self.bot.change_presence(activity=activity_before, status=sts)  # type: ignore
        await interaction.response.send_message(
            f'{C.B}{C.GREEN}set status to {sts}.{C.E}'
        )

    @app_commands.command()
    @app_commands.guilds(972593245005705297)
    async def setactivity(
        self,
        interaction: discord.Interaction,
        activity_type: Literal[
            'playing', 'streaming', 'watching', 'listening', 'competing'
        ],
        *,
        activity: str,
    ):
        """set the activity of the bot. usage: `setactivity {playing, streaming, watching, listening, competing} ..."""
        assert interaction.guild is not None
        status_before = interaction.guild.me.status
        match activity_type:
            case 'playing':
                new_act = discord.Game(activity)
            case 'streaming':
                stream = activity.rsplit(' ', maxsplit=1)
                new_act = discord.Streaming(name=stream[0], url=stream[1])
                status_before = discord.Status.online
            case 'watching':
                new_act = discord.Activity(
                    type=discord.ActivityType.watching, name=activity
                )
            case 'listening':
                new_act = discord.Activity(
                    type=discord.ActivityType.listening, name=activity
                )
            case 'competing':
                new_act = discord.Activity(
                    type=discord.ActivityType.competing, name=activity
                )
            case 'clear':
                await self.bot.change_presence(activity=None, status=status_before)
                await interaction.response.send_message(
                    f'{C.B}{C.GREEN}cleared activity.{C.E}'
                )
                return
        await self.bot.change_presence(activity=new_act, status=status_before)
        await interaction.response.send_message(
            f'{C.B}{C.GREEN}set activity to {C.WHITE}\"{activity_type} '
            f'{"to " if activity_type == "listening" else "in " if activity_type == "competing" else ""}'
            f'{new_act.name}.\"{C.E}'
        )

    @commands.command(name='exec')
    @commands.is_owner()
    async def execbot(self, ctx: commands.Context[Vesuvius], *, exc: str):
        if await self.confirm(ctx, f'exec  "{exc}"  '):
            return
        exec(exc)
        await ctx.send(f'{C.B}{C.BOLD_GREEN}executed.{C.E}')

    @commands.command(name='dbexec')
    @commands.is_owner()
    async def dbexec(self, ctx: commands.Context[Vesuvius], *, query: str):
        query = query.replace('`', '')
        if await self.confirm(ctx, f'execute the query  "{query}" in the database'):
            return
        await self.bot.database.cursor.execute(query)
        data = await self.bot.database.cursor.fetchall()
        datastr = '\n'.join([str(d) for d in data])
        await ctx.send(f'```py\n\u200b{datastr}```')
        await self.bot.database.connection.commit()

    @commands.command(name='webhook')
    @commands.has_guild_permissions(manage_webhooks=True)
    async def webhook_send(
        self, ctx: commands.Context[Vesuvius], name: str, content: str
    ) -> None:
        assert ctx.guild is not None
        for webhook in await ctx.guild.webhooks():
            assert webhook.name is not None
            if webhook.name.lower() == name.lower():
                await webhook.send(content)
                return

    @commands.command(name='webhookebd')
    @commands.has_guild_permissions(manage_webhooks=True)
    async def send_webhook_ebd(
        self,
        ctx: commands.Context[Vesuvius],
        name: str,
        title: str,
        description: str,
        color: str,
    ) -> None:
        """Send an embed from a webhook.

        Params
        -----
        Wrap all parameters in double quotes if it includes a space.
        name:
            The name of the webhook.
        title:
            The title of the embed.
        description:
            The description of the embed.
        color:
            The color of the embed, in formats `0x<hex>` or `#<hex>` or `0x#<hex>` or `rgb(<number>, <number>, <number>)`
        """
        assert ctx.guild is not None
        for webhook in await ctx.guild.webhooks():
            assert webhook.name is not None
            if webhook.name.lower() == name.lower():
                await webhook.send(
                    embed=discord.Embed(
                        title=title,
                        description=description,
                        color=discord.Color.from_str(color) if color else None,
                    )
                )
                return
        await ctx.send(f'{C.B}{C.RED}No webhook with the name {name} found.{C.E}')

    @commands.command(name='sendtf')
    @commands.is_owner()
    async def send_tf(self, ctx: commands.Context[Vesuvius], channel_id: int):
        channel = self.bot.get_channel(channel_id)

        if not await self.text_channel_check(channel, ctx=ctx):
            return
        assert isinstance(channel, discord.TextChannel)
        # for some reason async typeguards don't work

        if await self.confirm(
            ctx,
            'send <:tf:968279073367400458> '
            f'to channel  "{channel.name}"  in guild  "{channel.guild.name}" ',
        ):
            return

        await channel.send('<:tf:968279073367400458>')
        await ctx.send(f'{C.B}{C.BOLD_GREEN}sent!{C.E}')

    @commands.command(name='sendmsg')
    @commands.is_owner()
    async def send_msg(
        self, ctx: commands.Context[Vesuvius], channel_id: int, *, msg: str
    ):
        channel = self.bot.get_channel(channel_id)

        if not await self.text_channel_check(channel, ctx=ctx):
            return
        assert isinstance(channel, discord.TextChannel)

        if await self.confirm(
            ctx,
            f'send  "{msg}"  '
            f'to channel  "{channel.name}"  in guild  "{channel.guild.name}" ',
        ):
            return
        await channel.send(msg)
        await ctx.send(f'{C.B}{C.BOLD_GREEN}sent!{C.E}')

    @commands.command(name='delmsg')
    @commands.is_owner()
    async def del_msg(
        self, ctx: commands.Context[Vesuvius], channel_id: int, message_id: int
    ):
        channel = self.bot.get_channel(channel_id)

        if not await self.text_channel_check(channel, ctx=ctx):
            return
        assert isinstance(channel, discord.TextChannel)

        message: discord.Message = await channel.fetch_message(message_id)
        content = message.content
        if content == '':
            content = ', '.join([a.filename for a in message.attachments])
        if await self.confirm(
            ctx,
            f'delete  "{content}"  in channel  "{channel.name}"  '
            f'in guild  "{channel.guild.name}"  ',
        ):
            return
        await message.delete()
        await ctx.send(f'{C.B}{C.BOLD_GREEN}deleted.{C.E}')

    @commands.command(name='getmsg')
    @commands.is_owner()
    async def get_msg(
        self, ctx: commands.Context[Vesuvius], channel_id: int, msg_id: int
    ):
        channel = self.bot.get_channel(channel_id)

        if not await self.text_channel_check(channel, ctx=ctx):
            return
        assert isinstance(channel, discord.TextChannel)

        message = await channel.fetch_message(msg_id)
        create_time = message.created_at.strftime("%A of %x, at %I:%M:%S %p")
        edit_at_time = '\u200b'
        if message.edited_at is not None:
            edit_at_time = (
                'edited at - '
                f'{message.edited_at.strftime("%A of %x, at %I:%M:%S %p")}\n'
            )

        assert isinstance(message.channel, discord.TextChannel)
        assert isinstance(message.guild, discord.Guild)
        ebd = discord.Embed(
            title=f'Message by {message.author.name}\nin channel '
            f'"{message.channel.name}" of guild "{message.guild.name}"',
            description=f'**"{message.content}"**\n  sent at - {create_time}'
            f'{edit_at_time}{message.jump_url}',
        )
        await ctx.send(embed=ebd)

    @commands.command(name='getchannel')
    @commands.is_owner()
    async def getchannel(self, ctx: commands.Context[Vesuvius], channel_id: int):
        try:
            channel = await self.bot.fetch_channel(channel_id)
        except discord.NotFound:
            await ctx.send(f'{C.B}{C.RED}No channel with id {channel_id} found.{C.E}')
            return

        assert isinstance(channel, discord.abc.Messageable)
        await ctx.send(
            f'{C.B}{C.BOLD_GREEN}channel {C.WHITE} "{channel.name}" '
            f'{C.BOLD_GREEN} in guild {C.WHITE} "{channel.guild}." {C.E}'
        )

    @commands.command(name='getuser')
    @commands.is_owner()
    async def getuser(self, ctx: commands.Context[Vesuvius], user: discord.User):
        info = f'id: {user.id}\naccount created at {user.created_at}\n'
        ebd = discord.Embed(
            title=user.name, description=info, color=discord.Color.darker_gray()
        )
        await ctx.send(embed=ebd)

    async def confirm(self, ctx_info: commands.Context[Vesuvius], action: str) -> int:
        def chk(msg: discord.Message) -> bool:
            return msg.author == ctx_info.author and msg.channel == ctx_info.channel

        await ctx_info.send(
            f'{C.B}{C.RED}are you sure you want to{C.BOLD_RED} {action}? {C.E}'
        )
        try:
            m = await self.bot.wait_for('message', check=chk, timeout=10)
        except asyncio.TimeoutError:
            await ctx_info.send(f'{C.B}{C.RED}cancelled.{C.E}')
            return 1
        if m.content == 'yes':
            return 0
        else:
            await ctx_info.send(f'{C.B}{C.RED}cancelled.{C.E}')
            return 1

    @staticmethod
    async def text_channel_check(
        __channel: discord.abc.GuildChannel
        | discord.abc.PrivateChannel
        | discord.Thread
        | None,
        *,
        ctx: commands.Context[Vesuvius],
    ) -> TypeGuard[discord.TextChannel]:
        if __channel is None:
            await ctx.send(f'{C.B}{C.RED}Cannot find channel.{C.E}')
            return False

        if not isinstance(__channel, discord.TextChannel):
            await ctx.send(f'{C.B}{C.RED}Cannot send to non-text channels.{C.E}')
            return False

        return True


class ServerCommands(commands.Cog):
    def __init__(self, bot: Vesuvius) -> None:
        self.bot = bot

    @commands.command(name='ban')
    @commands.guild_only()
    @commands.has_guild_permissions(moderate_members=True)
    async def ban_user(
        self, ctx: commands.Context[Vesuvius], member: discord.Member, reason: str
    ) -> None:
        await member.ban(reason=reason)
        await ctx.send(f'{C.B}{C.RED}Banned {member.name} for {reason}.{C.E}')

    @commands.command(name='unban')
    @commands.guild_only()
    @commands.has_guild_permissions(moderate_members=True)
    async def unban_user(
        self, ctx: commands.Context[Vesuvius], member: discord.User, reason: str
    ) -> None:
        assert ctx.guild is not None
        await ctx.guild.unban(member, reason=reason)
        await ctx.send(f'{C.B}{C.RED}Unbanned {member.name} for {reason}.{C.E}')

    @commands.command(name='set-channels')
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def set_channels(
        self,
        ctx: commands.Context[Vesuvius],
        option: Literal[0, 1],
        general_channel: discord.TextChannel,
        announcements_channel: discord.TextChannel,
    ):
        assert ctx.guild is not None
        await self.bot.database.set_channels(
            ctx.guild.id, option, general_channel.id, announcements_channel.id
        )
        await ctx.send(
            f'{C.B}{C.GREEN}Succesfully set channels general: {general_channel}'
            f' and announcemets: {announcements_channel}.{C.E}'
        )

    @commands.command(name='get-channels')
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def get_channels(self, ctx: commands.Context[Vesuvius]):
        assert ctx.guild is not None
        guild, option, general, announcements = await self.bot.database.get_channel(
            ctx.guild.id
        )
        await ctx.send(
            f'```apache\nguild: {self.bot.get_guild(guild)}\noption: {option}\n'
            f'general: {self.bot.get_channel(general)}\n'
            f'announcments: {self.bot.get_channel(announcements)}```'
        )

    @commands.command(name='flush')
    @commands.has_guild_permissions(manage_messages=True)
    async def flush_channel(self, ctx: commands.Context[Vesuvius], number: int):
        async for message in ctx.channel.history(limit=number):
            await message.delete()
            await asyncio.sleep(0.3)


class GeneralCommands(commands.Cog):
    """general commands everyone can use with a cooldown"""

    def __init__(self, bot: Vesuvius) -> None:
        self.bot = bot

    @commands.hybrid_command(name='help', aliases=['h'])
    async def help(
        self, ctx: commands.Context[Vesuvius], command: Optional[str] = None
    ):
        """display help for commands. usage: `help [command]"""
        if not command:
            ebd = await self.default_help()
        else:
            cmd = self.bot.all_commands.get(command)
            if cmd is None:
                raise commands.CommandNotFound(
                    f'{C.RED}command "{command}" not found. try doing '
                    f'{C.WHITE}\\`help{C.RED} for a list of all commands{C.E}'
                )
            ebd = discord.Embed(
                title=f'{cmd.name}',
                description=f'{cmd.short_doc}',
                colour=discord.Colour.dark_orange(),
            )
        await ctx.send(embed=ebd)

    @staticmethod
    async def default_help() -> discord.Embed:
        embed_msg = discord.Embed(
            title='Vesuvius#8475',
            description='small bot that will have more stuff added gradually'
            '\n\n**prefix: \\` (backtick)**\n'
            f'{C.B}{C.YELLOW}`help {C.RED}[command]\n[]{C.YELLOW}: '
            f'optional arguments, {C.RED}{{}}{C.YELLOW}: possible values{C.E}',
            colour=discord.Colour.dark_orange(),
        )
        cmds = '\n`'.join(['`help', 'info', 'source'])
        games = '\n'.join(
            ['tictactoe', 'connectfour', 'reversi', 'weiqi', 'battleship']
        )
        math = '\n`'.join(
            [
                '`modulo',
                'divmod',
                'trianglecenters',
                'transformations',
                'permutations',
                'combinations\n',
            ]
        )

        embed_msg.add_field(name='commands:', value=f'{C.B}{C.BLUE}{cmds}{C.E}')
        embed_msg.add_field(name='games - /play:', value=f'{C.B}{C.PINK}{games}{C.E}')
        embed_msg.add_field(name='math:', value=f'{C.B}{C.CYAN}{math}{C.E}')
        embed_msg.add_field(
            name='errors:',
            value='report all bugs (there are a lot of them) to zhona#2155',
            inline=False,
        )
        embed_msg.set_footer(
            text='slash commands, buttons, dropdown menus coming "soon™"'
        )
        return embed_msg

    @commands.command(name='source', aliases=['src'])
    @commands.dynamic_cooldown(owner_bypass(240), type=commands.BucketType.channel)
    async def source(self, ctx: commands.Context[Vesuvius]):
        """link to source code repository."""
        ebd = discord.Embed(
            title='Source Code',
            description='https://github.com/lonaslee/Vesuvius',
            colour=discord.Colour.orange(),
        )
        await ctx.send(embed=ebd)

    @commands.hybrid_command(name='info')
    @commands.dynamic_cooldown(owner_bypass(120), type=commands.BucketType.channel)
    async def info(self, ctx: commands.Context[Vesuvius]):
        """info about the current instance of the bot."""
        ping = round(self.bot.latency * 1000)
        delta = datetime.now() - self.bot.start_time
        start = time()
        message = await ctx.send(f'{C.B}{C.YELLOW}testing...{C.E}')
        end = time()
        diff = end - start
        await message.edit(
            content=f'```apache\nPing: {ping} ms.\n'
            f'API:  {round(diff * 1000)} ms.\n'
            f'Started at  {self.bot.start_time.strftime("%m/%d, %H:%M:%S")}\n'
            f'Running for {delta}```'
        )

    @commands.command(name='c4')
    @commands.dynamic_cooldown(owner_bypass(60), type=commands.BucketType.user)
    async def c4(self, ctx: commands.Context[Vesuvius], *, fillers: Optional[str]):
        """suprise for people who use \\`c4 as a shorthand for \\`connectfour"""
        del fillers
        msg = await ctx.message.reply(f'{C.B}{C.YELLOW}bomb has been planted!{C.E}')
        next = f'{C.B}{C.YELLOW}bomb has been planted!{C.E}'
        for n in reversed(range(1, 6)):
            next = next.removesuffix('```')
            next += f'\n{C.RED}{n}...{C.E}'
            msg = await msg.edit(content=next)
            await asyncio.sleep(1)
        next = next.removesuffix('```')
        msg = await msg.edit(content=next + f'\n{C.BOLD_RED}BOOM! 💥{C.E}')

    @commands.command(name='color')
    async def rgb_color(self, ctx: commands.Context[Vesuvius], clr: str):
        color = discord.Colour.from_str(clr)
        rgb = color.to_rgb()
        img = Image.new('RGB', (100, 100), rgb)
        buffer = BytesIO()
        img.save(buffer, 'png')
        buffer.seek(0)
        file = discord.File(buffer, filename=f'color-{rgb[0]}-{rgb[1]}-{rgb[2]}.png')
        embed = discord.Embed(title=f'RGB: {rgb}', colour=color)
        embed.set_image(url=f'attachment://{file.filename}')
        await ctx.send(embed=embed, file=file)


async def setup(bot: Vesuvius):
    await bot.add_cog(OwnerCommands(bot))
    await bot.add_cog(ServerCommands(bot))
    await bot.add_cog(GeneralCommands(bot))
    print('LOADED commands')

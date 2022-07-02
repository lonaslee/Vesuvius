from __future__ import annotations

import re
import asyncio
from typing import Literal
from datetime import datetime
from time import time

import discord
from discord import app_commands
from discord.ext import commands

from extensions.definitions import owner_bypass, ANSIColors as C


class OwnerCommands(commands.Cog):
    """commands for owner to use"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='exit')
    @commands.is_owner()
    async def exit(self, ctx: commands.Context):
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
        ctx: commands.Context,
        extension: Literal['all', 'commands', 'events', 'features', 'games', 'testing'],
    ):
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
        self, ctx: commands.Context, scope: Literal['local', 'global'] = 'local'
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
        await self.bot.change_presence(activity=activity_before, status=sts)
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
        status_before = interaction.guild.me.status
        match activity_type := activity_type.lower():
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
    async def execbot(self, ctx: commands.Context, *, exc: str):
        if await self.confirm(ctx, f'exec  "{exc}"  '):
            return
        exec(exc)
        await ctx.send(f'{C.B}{C.BOLD_GREEN}executed.{C.E}')

    @commands.command(name='dbexec')
    @commands.is_owner()
    async def dbexec(self, ctx: commands.Context, *, query: str):
        query = query.replace('`', '')
        if await self.confirm(ctx, f'execute the query  "{query}" in the database'):
            return
        await self.bot.database.cursor.execute(query)
        data = await self.bot.database.cursor.fetchall()
        datastr = '\n'.join([str(d) for d in data])
        await ctx.send(f'```py\n\u200b{datastr}```')
        await self.bot.database.connection.commit()

    @commands.command(name='sendtf')
    @commands.is_owner()
    async def send_tf(self, ctx: commands.Context, channel: int):
        channel = self.bot.get_channel(channel)
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
    async def sendmsg(self, ctx: commands.Context, channel: int, *, msg: str):
        channel = self.bot.get_channel(channel)
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
    async def dele(self, ctx: commands.Context, chid: int, msgid: int):
        channel = self.bot.get_channel(chid)
        message = await channel.fetch_message(msgid)
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
    async def getmsg(self, ctx: commands.Context, channel_id: int, msg_id: int):
        channel = self.bot.get_channel(channel_id)
        if channel_id is None:
            await ctx.send(f'{C.B}{C.BOLD_RED}channel not found.{C.E}')
            return
        message = await channel.fetch_message(msg_id)
        create_time = message.created_at.strftime("%A of %x, at %I:%M:%S %p")
        edit_at_time = '\u200b'
        if message.edited_at is not None:
            edit_at_time = f'edited at - {message.edited_at.strftime("%A of %x, at %I:%M:%S %p")}\n'
        ebd = discord.Embed(
            title=f'Message by {message.author.name}\nin channel '
            f'"{message.channel.name}" of guild "{message.guild.name}"',
            description=f'**"{message.content}"**\n  sent at - {create_time}'
            f'{edit_at_time}{message.jump_url}',
        )
        await ctx.send(embed=ebd)

    @commands.command(name='getchannel')
    @commands.is_owner()
    async def getchannel(self, ctx: commands.Context, channel_id: int):
        ch = await self.bot.fetch_channel(channel_id)
        await ctx.send(
            f'{C.B}{C.BOLD_GREEN}channel {C.WHITE} "{ch.name}" '
            f'{C.BOLD_GREEN} in guild {C.WHITE} "{ch.guild}." {C.E}'
        )

    @commands.command(name='getuser')
    @commands.is_owner()
    async def getuser(self, ctx: commands.Context, user: discord.User):
        info = f'id: {user.id}\naccount created at {user.created_at}\n'
        ebd = discord.Embed(
            title=user.name, description=info, color=discord.Color.darker_gray()
        )
        await ctx.send(embed=ebd)

    async def confirm(
        self, ctx_info: commands.Context | discord.Interaction, action: str
    ) -> int:
        def chk(msg: discord.Message):
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


class GeneralCommands(commands.Cog):
    """general commands everyone can use with a cooldown"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name='help')
    async def help(self, ctx: commands.Context, command: str = None):
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
        cmds = '\n`'.join(['`help', 'info', 'leaderboard', 'snipe', 'source'])
        cmds2 = '\n`'.join(
            [
                '`modulo',
                'divmod',
                'trianglecenters',
                'transformations',
                'permutations',
                'combinations\n',
            ]
        )
        cmds3 = '\n`'.join(
            ['`tictactoe', 'connectfour', 'reversi', 'weiqi', 'battleship']
        )
        embed_msg.add_field(name='commands:', value=f'{C.B}{C.BLUE}{cmds}{C.E}')
        embed_msg.add_field(name='games:', value=f'{C.B}{C.PINK}{cmds3}{C.E}')
        embed_msg.add_field(name='math:', value=f'{C.B}{C.CYAN}{cmds2}{C.E}')

        embed_msg.add_field(
            name='errors:',
            value='report all bugs (there are a lot of them) to zhona#2155',
            inline=False,
        )
        embed_msg.set_footer(
            text='slash commands, buttons, dropdown menus coming "soon"'
        )
        return embed_msg

    @commands.command(name='source', aliases=['src'])
    @commands.dynamic_cooldown(owner_bypass(240), type=commands.BucketType.channel)
    async def source(self, ctx: commands.Context):
        """link to source code repository."""
        ebd = discord.Embed(
            title='Source Code',
            description='https://github.com/lonaslee/Vesuvius',
            colour=discord.Colour.orange(),
        )
        await ctx.send(embed=ebd)

    @commands.hybrid_command(name='info')
    @commands.dynamic_cooldown(owner_bypass(120), type=commands.BucketType.channel)
    async def info(self, ctx: commands.Context):
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

    @commands.command(name='wins', aliases=['leaderboard'])
    @commands.cooldown(rate=1, per=180, type=commands.BucketType.channel)
    @commands.guild_only()
    async def wins(self, ctx: commands.Context, *, gameorplayer: str = None):
        """display the leaderboard for wins in games! usage: `leaderboard [game | player]"""
        pats = {
            'tictactoe': r'tic[- ]?tac[- ]?toe|(t[- ]?){3}',
            'connectfour': r'connect[- ]?(four|4)|c[- ]?f',
            'reversi': r'reversi|rvsi|othello|oto',
            'weiqi': r'weiqi|wq|go',
            'battleship': r'battle[- ]?ship|bsh?',
        }
        if gameorplayer:
            for key, pat in zip(pats, pats.values()):
                if re.search(pat, gameorplayer.strip().lower()):
                    ebd = await self.ranks_embed(
                        await self.game_ranks(key), title=f'{key} Leaderboard'
                    )
                    await ctx.send(embed=ebd)
                    return
            else:
                player = await commands.MemberConverter().convert(
                    ctx, gameorplayer.strip()
                )  # raises command.BadArgument
                ebd = await self.ranks_embed(
                    await self.player_ranks(player.id),
                    title=f'Rank of {player.display_name}',
                )
                await ctx.send(embed=ebd)
                return
        else:
            ebd = await self.ranks_embed(await self.all_ranks())
            await ctx.send(embed=ebd)

    @staticmethod
    async def ranks_embed(ranks: list[list], title='Leaderboard') -> discord.Embed:
        ebd = discord.Embed(
            title=title.capitalize(),
            description='ranked by win/loss/tie ratios!',
            colour=discord.Colour.brand_green(),
        )
        start = 0
        cutoff = 13
        if 'battleship' in title:
            cutoff = 10
        if 'Leaderboard' in title:
            start = 3
            top_three = (
                f'```ansi\n\u001b[0m\u001b[4;37m'
                f'\u001b[1;33m#1 | {ranks[0][2][:cutoff]}🥇 {ranks[0][1]}\n'
                f'\u001b[1;30m#2 | {ranks[1][2][:cutoff]}🥈 {ranks[1][1]}\n'
                f'\u001b[1;31m#3 | {ranks[2][2][:cutoff]}🥉 {ranks[2][1]}```'
            )
            ebd.add_field(name='\u200b', value=top_three, inline=False)
        for n in range(start, len(ranks), 5):
            ebdstr = ''
            for i in range(5):
                if (n + i) >= len(ranks):
                    break
                ebdstr += f'#{ranks[n + i][3]} | {ranks[n + i][2]}\n'
            ebd.add_field(
                name='\u200b',
                value=f'```ansi\n\u001b[0m\u001b[4;36m{ebdstr}```',
                inline=False,
            )
        return ebd

    async def game_ranks(self, game: str) -> list[list]:
        ranks: list = await self.bot.database.get_games_winloss()
        indexdict = {
            'tictactoe': [1, 2, 3],
            'connectfour': [4, 5, 6],
            'reversi': [7, 8, 9],
            'weiqi': [10, 11, 12],
            'battleship': [13, 14],
        }
        key = indexdict.get(game)
        for k, lst in enumerate(ranks):
            ranks[k] = [
                lst[0],
                '',
                ':'.join([str(lst[k]).rjust(3, '~') for k in key]),
                lst[key[0]] - lst[key[1]],
            ]
            dis_name = (await self.bot.fetch_user(lst[0])).display_name
            if len(dis_name) > 25:
                ranks[k][2] += ' | ' + dis_name[:18] + '...'
                ranks[k][1] = dis_name[:18] + '...'
            else:
                ranks[k][2] += ' | ' + dis_name
                ranks[k][1] = dis_name
        ranks.sort(key=(lambda l: l[3]), reverse=True)
        for k, lst in enumerate(ranks):
            ranks[k][3] = k + 1
        return ranks

    async def all_ranks(self) -> list[list]:
        ranks: list = await self.bot.database.get_games_winloss()
        for k, lst in enumerate(ranks):
            wins = sum([lst[n] for n in range(1, 14, 3)])
            loss = sum([lst[n] for n in range(2, 15, 3)])
            ties = sum([lst[n] for n in range(3, 14, 3)])
            ranks[k] = [
                lst[0],
                '',
                ':'.join([str(n).rjust(3, '~') for n in [wins, loss, ties]]),
                wins - loss,
            ]
            dis_name = (await self.bot.fetch_user(lst[0])).display_name
            if len(dis_name) > 25:
                ranks[k][2] += ' | ' + dis_name[:18] + '...'
                ranks[k][1] = dis_name[:18] + '...'
            else:
                ranks[k][2] += ' | ' + dis_name
                ranks[k][1] = dis_name
        ranks.sort(key=(lambda l: l[3]), reverse=True)
        for k, lst in enumerate(ranks):
            ranks[k][3] = k + 1
        return ranks

    async def player_ranks(self, user_id: int) -> list[list, list, list]:
        ranks = await self.all_ranks()
        k = 0
        for k, p in enumerate(ranks):
            if p[0] == user_id:
                ranks[k][2] = f'\u001b[1;47m{p[2]}\u001b[0m\u001b[4;36m'
                ranks[k][3] = k + 1
                break
        lst = []
        if (k - 1) >= 0:
            ranks[k - 1][3] = k
            lst.append(ranks[k - 1])
        lst.append(ranks[k])
        if (k + 1) < len(ranks):
            ranks[k + 1][3] = k + 2
            lst.append(ranks[k + 1])
        print(f"DBG {lst}")
        return lst

    @commands.command(name='c4')
    @commands.dynamic_cooldown(owner_bypass(60), type=commands.BucketType.user)
    async def c4(self, ctx: commands.Context, *, fillers=None):
        """suprise for people who use \\`c4 as a shorthand for \\`connectfour"""
        msg = await ctx.message.reply(f'{C.B}{C.YELLOW}bomb has been planted!{C.E}')
        next = f'{C.B}{C.YELLOW}bomb has been planted!{C.E}'
        for n in reversed(range(1, 6)):
            next = next.removesuffix('```')
            next += f'\n{C.RED}{n}...{C.E}'
            msg = await msg.edit(content=next)
            await asyncio.sleep(1)
        next = next.removesuffix('```')
        msg = await msg.edit(content=next + f'\n{C.BOLD_RED}BOOM! 💥{C.E}')


async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCommands(bot))
    await bot.add_cog(GeneralCommands(bot))
    print('LOADED commands')

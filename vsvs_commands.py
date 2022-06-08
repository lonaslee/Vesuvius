import re
import discord
import asyncio
from discord.ext import commands
from datetime import datetime
from time import time


class OwnerCommands(commands.Cog):
    """commands for owner to use"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='exit', aliases=['ex'])
    @commands.is_owner()
    @commands.guild_only()
    async def exit(self, ctx: commands.Context):
        """close the event loop"""
        await ctx.send('are you sure you want to exit?')

        def chk(e):
            return e.author == ctx.author and e.channel == ctx.channel

        try:
            confirmation = await self.bot.wait_for('message', check=chk, timeout=10)
        except asyncio.TimeoutError:
            await ctx.send('timed out')
            return
        if confirmation.content == 'yes':
            print("EXITING on exit command")
            await ctx.send('good bye!')
            await self.bot.close()
        else:
            await ctx.send('cancelled.')

    @commands.command(name='reload', aliases=['r'])
    @commands.is_owner()
    @commands.guild_only()
    async def reload(self, ctx: commands.Context):
        await ctx.send('reloading.')
        print('RELOADING extensions')
        await self.bot.reload_extension('vsvs_events')
        await self.bot.reload_extension('vsvs_features')
        await self.bot.reload_extension('vsvs_testing')
        await self.bot.reload_extension('vsvs_games')
        await self.bot.reload_extension('vsvs_commands')

    @commands.command(name='setstatus')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.default)
    @commands.guild_only()
    async def setstatus(self, ctx: commands.Context, new: str):
        """set the status of the bot. usage: `setstatus {online, idle, dnd, offline}"""
        act_rn = ctx.me.activity
        match new.strip().lower():
            case 'online':
                sts = discord.Status.online
            case 'offline' | 'invis' | 'invisible':
                sts = discord.Status.invisible
            case 'dnd' | 'donotdisturb':
                sts = discord.Status.do_not_disturb
            case 'idle':
                sts = discord.Status.idle
            case _:
                raise commands.BadArgument(
                    message='invalid status. must be of types '
                    '{online, idle, dnd, offline}. for activities do \\`setactivity'
                )
        await self.bot.change_presence(activity=act_rn, status=sts)
        await ctx.send(f'set status to {sts}')

    @commands.command(name='setactivity')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.default)
    @commands.guild_only()
    async def setactivity(
        self, ctx: commands.Context, activity_type: str, *, act: str = 'something'
    ):
        """set the activity of the bot. usage: `setactivity {playing, streaming, watching, listening, competing} ..."""
        sts_rn = ctx.me.status
        match activity_type := activity_type.lower():
            case 'playing':
                new_act = discord.Game(act)
            case 'streaming':
                stream = act.rsplit(' ', maxsplit=1)
                new_act = discord.Streaming(name=stream[0], url=stream[1])
                sts_rn = discord.Status.online
            case 'watching':
                new_act = discord.Activity(type=discord.ActivityType.watching, name=act)
            case 'listening':
                new_act = discord.Activity(
                    type=discord.ActivityType.listening, name=act
                )
            case 'competing':
                new_act = discord.Activity(
                    type=discord.ActivityType.competing, name=act
                )
            case 'clear':
                await self.bot.change_presence(activity=None, status=sts_rn)
                await ctx.send(f'cleared activity')
                return
            case _:
                raise commands.BadArgument(
                    message='invalid activity. must be of types '
                    '{playing, streaming, watching, listening, competing} {...}'
                )
        await self.bot.change_presence(activity=new_act, status=sts_rn)
        await ctx.send(
            f'set activity to \"{activity_type} '
            f'{"to " if activity_type == "listening" else "in " if activity_type == "competing" else ""}'
            f'{new_act.name}\"'
        )

    @commands.command(name='exec')
    @commands.is_owner()
    @commands.guild_only()
    async def botexec(self, ctx: commands.Context, *, exc: str):
        if await self.confirm(ctx, f'exec  "{exc}"  '):
            return
        exec(exc)
        await ctx.send('executed')

    @commands.command(name='dbexec')
    @commands.is_owner()
    @commands.guild_only()
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
    @commands.guild_only()
    async def send_tf(self, ctx: commands.Context, channel: int):
        channel = self.bot.get_channel(channel)
        if await self.confirm(
            ctx,
            'send <:tf:968279073367400458> '
            f'to channel  "{channel.name}"  in guild  "{channel.guild.name}" ?',
        ):
            return
        await channel.send('<:tf:968279073367400458>')
        await ctx.send('sent!  <:tf:968279073367400458>')

    @commands.command(name='sendmsg')
    @commands.is_owner()
    @commands.guild_only()
    async def sendmsg(self, ctx: commands.Context, channel: int, *, msg: str):
        channel = self.bot.get_channel(channel)
        if await self.confirm(
            ctx,
            f'send  "{msg}"  '
            f'to channel  "{channel.name}"  in guild  "{channel.guild.name}" ',
        ):
            return
        await channel.send(msg)
        await ctx.send('sent.')

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
        await ctx.send('deleted.')

    @commands.command(name='getmsg')
    @commands.is_owner()
    async def getmsg(self, ctx: commands.Context, channel_id: int, msg_id: int):
        channel = self.bot.get_channel(channel_id)
        if channel_id is None:
            await ctx.send('channel not found.')
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
        await ctx.send(f'channel  "{ch.name}"  in guild  "{ch.guild}"')

    async def confirm(self, ctx: commands.Context, action: str) -> int:
        def chk(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        await ctx.send(f'are you sure you want to {action}?')
        try:
            m = await self.bot.wait_for('message', check=chk, timeout=10)
        except asyncio.TimeoutError:
            await ctx.send('del cancelled.')
            return 1
        if m.content == 'yes':
            return 0
        else:
            await ctx.send('cancelled.')
            return 1


class GeneralCommands(commands.Cog):
    """general commands everyone can use with a cooldown"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.start_time = datetime.now()

    @commands.command(name='help')
    async def help(self, ctx: commands.Context, command: str = None):
        """display help for commands. usage: `help [command]"""
        if not command:
            ebd = await self.default_help()
        else:
            cmd = self.bot.all_commands.get(command)
            if cmd is None:
                raise commands.CommandNotFound(
                    f'command "{command}" not found. '
                    'try doing \\`help for a list of all commands'
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
            description='small bot that will have more stuff added gradually\n'
            '```\n`help [command]\n[]: optional arguments, {}: possible values```',
            colour=discord.Colour.dark_orange(),
        )
        cmds = '\n\\`'.join(
            [
                '\\`exit',
                'setstatus',
                'setactivity',
                'help',
                'starttime',
                'ping',
                'leaderboard',
                'snipe',
                'source',
            ]
        )
        cmds2 = '\n'.join(
            [
                '**math:**',
                '\\`modulo',
                '\\`divmod',
                '\\`trianglecenters',
                '\\`transformations\n',
                '**games:**',
                '\\`tictactoe',
                '\\`connectfour',
                '\\`reversi',
                '\\`weiqi',
                '\\`battleship',
            ]
        )
        embed_msg.add_field(name='commands:', value=cmds)
        embed_msg.add_field(name='prefix: `', value=f'(backtick)\n\n{cmds2}')
        embed_msg.add_field(
            name='errors:',
            value='report all bugs (there are a lot of them)\nto @zhona#2155 with a ping',
            inline=False,
        )
        embed_msg.set_footer(
            text='slash commands, buttons, dropdown menus coming "soon"'
        )
        return embed_msg

    @commands.command(name='source', aliases=['src'])
    @commands.cooldown(rate=1, per=240, type=commands.BucketType.channel)
    @commands.guild_only()
    async def source(self, ctx: commands.Context):
        """link to source code repository. usage: `source"""
        ebd = discord.Embed(
            title='Source Code',
            description='https://github.com/lonaslee/Vesuvius',
            colour=discord.Colour.orange(),
        )
        await ctx.send(embed=ebd)

    @commands.command(name='uptime')
    @commands.cooldown(rate=1, per=180, type=commands.BucketType.channel)
    @commands.guild_only()
    async def uptime(self, ctx: commands.Context):
        """get the uptime of the current instance of the bot. usage: `uptime"""
        delta = datetime.now() - self.start_time
        await ctx.send(
            f'bot started at {self.start_time.strftime("%m/%d, %H:%M:%S")}\n'
            f'running for {delta.days} days and {delta.seconds} seconds.'
        )

    @commands.command(name='ping')
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.channel)
    @commands.guild_only()
    async def ping(self, ctx: commands.Context):
        """test bot ping and API. usage: `ping"""
        ping = round(self.bot.latency * 1000)
        if ping > 149:
            msg = f'Ouch!  {ping}ms!'
        elif ping < 21:
            msg = f'Wow!   {ping}ms!'
        else:
            msg = f'Pong!  {ping}ms!'
        start = time()
        await ctx.send(msg)
        end = time()
        diff = end - start
        await ctx.send(f'API:     {round(diff * 1000)}ms.')

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
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    @commands.guild_only()
    async def c4(self, ctx: commands.Context, *, fillers=None):
        """suprise for people who use \\`c4 as a shorthand for \\`connectfour"""
        await ctx.message.reply('bomb has been planted!')
        for n in reversed(range(1, 6)):
            await ctx.send(f'{n}...')
            await asyncio.sleep(1)
        await ctx.send('BOOM! :boom:')


async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCommands(bot))
    await bot.add_cog(GeneralCommands(bot))
    print('LOADED commands')

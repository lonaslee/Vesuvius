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

    @commands.command(name='dbexec')
    @commands.is_owner()
    async def dbexec(self, ctx: commands.Context, query: str):
        await self.bot.database.cursor.execute(query)

    @commands.command(name='reload')
    @commands.is_owner()
    async def reload(self, ctx: commands.Context):
        await ctx.send('reloading.')
        print('RELOADING extensions')
        await self.bot.reload_extension('vsvs_events')
        await self.bot.reload_extension('vsvs_features')
        await self.bot.reload_extension('vsvs_testing')
        await self.bot.reload_extension('vsvs_commands')

    @commands.command(name='setstatus')
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.default)
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
                    '{online, idle, dnd, offline}. for activities do \`setactivity'
                )
        await self.bot.change_presence(activity=act_rn, status=sts)
        await ctx.send(f'set status to {sts}')

    @commands.command(name='setactivity')
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.default)
    async def setactivity(
        self, ctx: commands.Context, type: str, *, act: str = 'something'
    ):
        """set the activity of the bot. usage: `setactivity {playing, streaming, watching, listening, competing} ..."""
        sts_rn = ctx.me.status
        match type := type.lower():
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
            f'set activity to \"{type} '
            f'{"to " if type == "listening" else "in " if type == "competing" else ""}'
            f'{new_act.name}\"'
        )

    @commands.command(name='sendtf')
    @commands.is_owner()
    async def send_tf(self, ctx: commands.Context, channel: int):
        def chk(m):
            return m.author == ctx.author and m.channel == ctx.channel

        channel = self.bot.get_channel(channel)
        await ctx.send(
            f'are you sure you want to send <:tf:968279073367400458> '
            f'to channel  "{channel.name}"  in guild  "{channel.guild.name}" ?'
        )
        try:
            m = await self.bot.wait_for('message', check=chk, timeout=10)
        except asyncio.TimeoutError:
            await ctx.send('tfsend cancelled.')
            return
        if m.content == 'yes':
            await channel.send('<:tf:968279073367400458>')
            await ctx.send('sent!  <:tf:968279073367400458>')
        else:
            await ctx.send('ok.  <:td:968282301593157723>')


class GeneralCommands(commands.Cog):
    """general commands everyone can use with a cooldown"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.start_time = datetime.now().strftime('%m/%d, %H:%M:%S')

    @commands.command(name='help')
    async def help(self, ctx: commands.Context, command: str = None):
        """display help for commands. usage: `help [command]"""
        ebd = None
        if not command:
            ebd = await self.default_help()
        else:
            cmd = self.bot.all_commands.get(command)
            if cmd is None:
                raise commands.CommandNotFound(
                    f'command "{command}" not found. '
                    'try doing \`help for a list of all commands'
                )
            ebd = discord.Embed(
                title=f'{cmd.name}',
                description=f'{cmd.short_doc}',
                colour=discord.Colour.dark_orange(),
            )
        await ctx.send(embed=ebd)

    async def default_help(self) -> discord.Embed:
        embed_msg = discord.Embed(
            title='Vesuvius#8475',
            description='small bot that will have more stuff added gradually\n'
            '```\n`help [command]\n[]: optional arguments, {}: options```',
            colour=discord.Colour.dark_orange(),
        )
        cmds = '\n\`'.join(
            [
                '\`exit',
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
                '\`modulo',
                '\`divmod',
                '\`trianglecenters',
                '\`transformations\n',
                '**games:**',
                '\`tictactoe',
                '\`connectfour',
                '\`reversi',
                '\`weiqi',
            ]
        )
        embed_msg.add_field(name='commands:', value=cmds)
        embed_msg.add_field(name='prefix: `', value=f'(backtick)\n\n{cmds2}')
        embed_msg.add_field(
            name='errors:',
            value='report all bugs (there are a lot of them)\nto @zhona#2155 with a ping',
            inline=False,
        )
        return embed_msg

    @commands.command(name='source', aliases=['src'])
    @commands.cooldown(rate=1, per=240, type=commands.BucketType.channel)
    async def source(self, ctx: commands.Context):
        """link to source code repository. usage: `source"""
        ebd = discord.Embed(
            title='Source Code',
            description='embarassing...\ngithub.com/lonaslee/Vesuvius',
            colour=discord.Colour.dark_blue(),
        )
        await ctx.send(embed=ebd)

    @commands.command(name='starttime')
    @commands.cooldown(rate=1, per=180, type=commands.BucketType.channel)
    async def starttime(self, ctx: commands.Context):
        """get the start time of the current instance of the bot. usage: `starttime"""
        await ctx.send(f'bot started at {self.start_time}')

    @commands.command(name='ping')
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.channel)
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
    async def wins(self, ctx: commands.Context):
        """display the leaderboard for wins in games! usage: `leaderboard"""
        medals = {0: '\u001b[1;33m', 1: '\u001b[1;30m', 2: '\u001b[1;31m'}
        ebd = discord.Embed(
            title='Game Wins, Losses, and Ties!',
            description=None,
            colour=discord.Colour.dark_green(),
        )
        lst = await self.bot.database.get_games_winloss()
        lst.sort(
            key=(lambda v: v[1] + v[4] + v[7] + v[10] - v[2] - v[5] - v[8] - v[11]),
            reverse=True,
        )
        fs = '\u001b[0m\u001b[4;37m\u001b[1;37m       ttt | c4    | rvsi  | weiqi '
        for k, r in enumerate(lst):
            pairs = ' | '.join(
                [
                    f'{r[1]}:{r[2]}:{r[3]}',
                    f'{r[4]}:{r[5]}:{r[6]}',
                    f'{r[7]}:{r[8]}:{r[9]}',
                    f'{r[10]}:{r[11]}:{r[12]}',
                ]
            )
            dis_name = ctx.guild.get_member(r[0]).display_name
            if len(dis_name) > 20:
                dis_name = dis_name[:12] + '...'
            color = medals.get(k, '\u001b[0;32m')
            fs = ''.join(
                ['\n', fs, '\n', color, f'#{k + 1} - ', pairs, ' - ', dis_name]
            )
        ebd.add_field(name='--- Leaderboard ---', value=f'```ansi{fs}```')
        await ctx.send(embed=ebd)

    @commands.command(name='sendmsg')
    @commands.is_owner()
    async def sendmsg(self, ctx: commands.Context, channel: int, *, msg: str):
        def chk(m):
            return m.author == ctx.author and m.channel == ctx.channel

        channel = self.bot.get_channel(channel)
        await ctx.send(
            f'are you sure you want to send  "{msg}"  '
            f'to channel  "{channel.name}"  in guild  "{channel.guild.name}" ?'
        )
        try:
            m = await self.bot.wait_for('message', check=chk, timeout=10)
        except asyncio.TimeoutError:
            await ctx.send('tfsend cancelled.')
            return
        if m.content == 'yes':
            await channel.send(msg)
            await ctx.send('sent!')
        else:
            await ctx.send('ok.')

    @commands.command(name='c4')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    async def c4(self, ctx: commands.Context, *, fillers=None):
        """suprise for people who use \`c4 as a shorthand for \`connectfour"""
        await ctx.message.reply('bomb has been planted!')
        for n in reversed(range(1, 6)):
            await ctx.send(f'{n}...')
            await asyncio.sleep(1)
        await ctx.message.reply('BOOM! :boom:')


async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCommands(bot))
    await bot.add_cog(GeneralCommands(bot))
    print('LOADED commands')

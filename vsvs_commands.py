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
            confirmation = await self.bot.wait_for(
                event='message', check=chk, timeout=10
            )
        except asyncio.TimeoutError:
            await ctx.send('timed out')
            return
        if confirmation.content == 'yes':
            await ctx.send('good bye!')
            await self.bot.close()

    @exit.error
    async def exit_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.NotOwner):
            await ctx.send('permission denied.')
        else:
            await ctx.send(error)

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
        """set the activity of the bot. usage: `setactivity {playing, streaming, watching, listening, competing} {...}"""
        sts_rn = ctx.me.status
        match type := type.lower():
            case 'playing':
                new_act = discord.Game(act)
            case 'streaming':
                stream = act.split(' ', maxsplit=1)
                new_act = discord.Streaming(name=stream[0], url=stream[1])
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
                    '{playing, streaming, watching, listening, competing}{...}'
                )
        await self.bot.change_presence(activity=new_act, status=sts_rn)
        await ctx.send(
            f'set activity to \"{type} '
            f'{"to " if type == "listening" else "in " if type == "competing" else ""}'
            f'{new_act.name}\"'
        )


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
            description='small bot that will have more stuff added gradually',
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

    @commands.command(name='c4')
    @commands.cooldown(rate=1, per=60)
    async def c4(self, ctx: commands.Context, *, fillers=None):
        """suprise for people who use `c4 as a shorthand for `connectfour"""
        await ctx.message.reply('bomb has been planted!')
        for n in reversed(range(1, 6)):
            await ctx.send(f'{n}...')
            await asyncio.sleep(1)
        await ctx.message.reply('BOOM! :boom:')


def setup(bot: commands.Bot):
    bot.add_cog(OwnerCommands(bot))
    bot.add_cog(GeneralCommands(bot))
    print('LOADED commands')

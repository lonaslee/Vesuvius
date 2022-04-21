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
    @commands.is_owner()
    async def setstatus(self, ctx: commands.Context, new: str):
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
                await ctx.send('invalid status')
                return
        await self.bot.change_presence(activity=act_rn, status=sts)
        await ctx.send(f'set status to {sts}')

    @commands.command(name='setactivity')
    @commands.is_owner()
    async def setactivity(
        self, ctx: commands.Context, type: str, *, act: str = 'something'
    ):
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
                await ctx.send('invalid activity')
                return
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
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.channel)
    async def help(self, ctx: commands.Context):
        """display docs"""
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
                'ey',
                'ping',
                'snipe',
            ]
        )
        cmds2 = '\n'.join(
            [
                '**math:**',
                '\`trianglecenters',
                '\`transformations\n',
                '**games:**',
                '\`tictactoe',
                '\`connectfour',
                '\`reversi',
            ]
        )
        embed_msg.add_field(name='commands:', value=cmds)
        embed_msg.add_field(name='prefix: `', value=f'(backtick)\n\n{cmds2}')
        embed_msg.add_field(
            name='errors:',
            value='report all bugs (there are a lot of them)\nto @zhona#2155 with a ping',
            inline=False,
        )
        await ctx.send(embed=embed_msg)

    @commands.command(name='starttime')
    @commands.cooldown(rate=1, per=180, type=commands.BucketType.channel)
    async def starttime(self, ctx: commands.Context):
        """get the start time of the current instance of the bot"""
        await ctx.send(f'bot started at {self.start_time}')

    @commands.command(name='ey')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    async def ey(self, ctx: commands.Context):
        """reply with 'Oi'"""
        await ctx.send('Oi')

    @commands.command(name='ping')
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.channel)
    async def ping(self, ctx: commands.Context):
        """test bot ping and API"""
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


def setup(bot: commands.Bot):
    bot.add_cog(OwnerCommands(bot))
    bot.add_cog(GeneralCommands(bot))

from __future__ import annotations
import discord
import asyncio
import datetime
import re
from features import trianglecenters, transformations, wotd
from matplotlib import pyplot as plt
from pathlib import Path
from itertools import combinations, chain
from discord.ext import commands, tasks


class GraphFeatures(commands.Cog):
    """features cog that has the commands to invoke special features that use a graph"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name='trianglecenters')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    async def trianglecenters(self, ctx: commands.Context, *, text: str = None):
        """calculate orthocenter, circumcenter, and centroid from three coordinate points of a triangle. usage:
        \\`trianglecenters [x, y, x2, y2, x3, y3]"""
        a, b, c = {}, {}, {}
        nstr = False
        if text:
            if 'noword' in text:
                nstr = True
            mch = re.findall(r'(-?\d+.?\d*?[\s,]*?)', text)
            mch = [(lambda p: p.strip(' ,(), '))(pt) for pt in mch]
            mch = [float(p) for p in mch]
            try:
                a['x'], a['y'] = mch[0], mch[1]
                b['x'], b['y'] = mch[2], mch[3]
                c['x'], c['y'] = mch[4], mch[5]
            except ValueError:
                await ctx.send('this command must be invoked with all or no points.')
                return
        else:
            try:
                a['x'], a['y'] = await self.get_point(ctx, 1)
                b['x'], b['y'] = await self.get_point(ctx, 2)
                c['x'], c['y'] = await self.get_point(ctx, 3)
            except ValueError:  # get_point timed out and returned None
                return
        try:
            fs, fsnw, mpa = await self.bot.run_in_tpexec(
                lambda: trianglecenters.main(a, b, c)
            )
        except ValueError:
            ctx.send(
                f'not a triangle. if there is nothing wrong with your input, '
                f'report the error to @\u200b{ctx.guild.get_member(self.bot.owner_id)}'
            )
            return
        path = await self.plt_plt(ctx.message.author, mpa[0], mpa[1], mpa[2], a, b, c)
        fobj = discord.File(path)
        embed_msg = discord.Embed(
            title='Triangle Centers',
            description=f'```py\n{fsnw if nstr else fs}```',
            color=discord.Colour.dark_green(),
            timestamp=datetime.datetime.utcnow(),
        )
        embed_msg.set_image(url=f'attachment://{fobj.filename}')
        await ctx.send(file=fobj, embed=embed_msg)

    async def get_point(
        self, ctx: commands.Context, ptn: int
    ) -> tuple[float, float] | None | str:
        def chkp(m):
            return m.author == ctx.message.author and m.channel == ctx.channel

        await ctx.send(f'point {ptn}:')
        try:
            msg = await self.bot.wait_for('message', check=chkp, timeout=30)
            if msg.content == 'end':
                return 'end'
            x, y = re.search(
                r'(?P<x>-?\d+.?\d*?)[\s,]*?(?P<y>-?\d+.?\d*?)', msg.content
            ).groups()
        except asyncio.TimeoutError:
            await ctx.send('command timed out.')
            return None
        except ValueError:
            await ctx.send(f'format error: cannot unpack {msg.content}.')
            return await self.get_point(ctx, ptn)
        return float(x), float(y)

    async def plt_plt(
        self,
        caller,
        ortho: tuple,
        circum: tuple,
        medi: tuple,
        a: dict,
        b: dict,
        c: dict,
    ) -> Path:
        a = (a['x'], a['y'])
        b = (b['x'], b['y'])
        c = (c['x'], c['y'])
        xes = (ptx := [float(pt[0]) for pt in [a, b, c]]) + [
            pt[3][0] for pt in [ortho, circum, medi]
        ]
        yes = (pty := [float(pt[1]) for pt in [a, b, c]]) + [
            pt[3][1] for pt in [ortho, circum, medi]
        ]
        mx, mn = round(max(xes + yes)), round(min(xes + yes))
        if mn >= 0:
            plt.xlim(0, mx * 1.25)
            plt.ylim(0, mx * 1.25)
        else:
            axis = mx if mx > abs(mn) else abs(mn)
            plt.xlim(axis * -1.25, axis * 1.25)
            plt.ylim(axis * -1.25, axis * 1.25)
            plt.axhline(y=0, linewidth=2.0, color='dimgrey', linestyle='--')
            plt.axvline(x=0, linewidth=2.0, color='dimgrey', linestyle='--')
        plt.grid(b=True)
        markers = ['o', 'o', 'o', 'X', 's', 'D']
        colors = ['black', 'black', 'black', 'blue', 'green', 'purple']
        list(
            map(
                lambda x, y, m, clr: plt.plot(  # plot all points
                    [x],
                    [y],
                    marker=m,
                    markersize=5,
                    markeredgecolor=clr,
                    markerfacecolor=clr,
                ),
                xes,
                yes,
                markers,
                colors,
            )
        )
        pt_tuples = list(zip(ptx, pty))
        cmbs = list(combinations([p for p in pt_tuples], 2))
        for cmb in cmbs:
            plt.plot(
                [cmb[0][0], cmb[1][0]],
                [cmb[0][1], cmb[1][1]],
                linewidth=2.0,
                color='black',
            )
        tme = datetime.datetime.now().strftime('%H%M%S')
        plt.savefig(
            fl := Path(
                f'{self.bot.files["trianglecenters"].as_posix()}/'
                f'{tme}--{str(caller).replace("#", "")}--plot.png'
            )
        )
        plt.clf()
        return fl

    @commands.command(name='transformations')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    async def transformations(self, ctx: commands.Context, *, text: str = None):
        """compute translations, reflections, rotations, and dilations on a set of points. usage: `transformations [x, y, ...]"""
        pt_lst = []
        if text:
            pt_lst = re.findall(r'(-?\d+.?\d*?[\s,]*?)', text)
            pt_lst = [(lambda p: p.strip(' ,(), '))(pt) for pt in pt_lst]
            pt_lst = [float(p) for p in pt_lst]
            if len(pt_lst) % 2 != 0:
                ctx.send('each point must have x and y.')
                return
            pt_lst = [(pt_lst[d], pt_lst[d + 1]) for d in range(0, len(pt_lst), 2)]
        else:
            for n in range(100):
                tup = await self.get_point(ctx, n + 1)
                if tup == 'end':
                    break
                if tup is None:
                    return  # get_point timed out and returned None
                pt_lst.append((tup[0], tup[1]))
        aps = await self.bot.run_in_tpexec(lambda: transformations.AllPoints(pt_lst))
        for n in range(100):
            res = await self.get_inp(ctx)
            if res is None:
                return
            if res != 'end':
                m, a = res
                await self.bot.run_in_tpexec(lambda: getattr(aps, m)(a))
            ap_str = '\n'.join([str(p) for p in aps.allpoints])
            embed_msg = discord.Embed(
                title='Transformations',
                description=ap_str,
                colour=discord.Colour.dark_blue(),
                timestamp=datetime.datetime.utcnow(),
            )
            path = await self.graph_fig(aps, ctx.message.author)
            fobj = discord.File(path)
            embed_msg.set_image(url=f'attachment://{fobj.filename}')
            await ctx.send(file=fobj, embed=embed_msg)
            if res == 'end':
                return

    async def get_inp(self, ctx: commands.Context) -> tuple | str | None:
        await ctx.send('transformation:')

        def chki(m):
            return m.author == ctx.message.author and m.channel == ctx.channel

        msg = None
        try:
            msg = await self.bot.wait_for('message', check=chki, timeout=30)
            if msg.content == 'end':
                return 'end'
            ap_mtd, ap_args = await self.bot.run_in_tpexec(
                lambda: transformations.Inputs().main(msg.content)
            )
        except asyncio.TimeoutError:
            await ctx.send('command timed out.')
            return None
        except ValueError:
            await ctx.send(f'format error: cannot unpack {msg.content}')
            return await self.get_inp(ctx)
        return ap_mtd, ap_args

    async def graph_fig(self, apts: transformations.AllPoints, caller) -> Path:
        avs = list(chain.from_iterable([[p.x, p.y] for p in apts.allpoints]))
        mx, mn = round(max(avs)), round(min(avs))
        axis = mx * 1.25 if mx > abs(mn) else mn * 1.25
        if axis >= 0:
            plt.xlim(0, axis)
            plt.ylim(0, axis)
        else:
            plt.xlim(axis, axis * -1)
            plt.ylim(axis, axis * -1)
            plt.axhline(y=0, linewidth=2.0, color='dimgrey', linestyle='--')
            plt.axvline(x=0, linewidth=2.0, color='dimgrey', linestyle='--')
        plt.grid(b=True)
        list(
            map(
                lambda p: plt.plot(
                    [p.x],
                    [p.y],
                    marker='o',
                    markersize=5,
                    markeredgecolor='black',
                    markerfacecolor='black',
                ),
                apts.allpoints,
            )
        )
        cmbs = list(combinations(apts.allpoints, 2))
        for cmb in cmbs:
            plt.plot(
                [cmb[0].x, cmb[1].x], [cmb[0].y, cmb[1].y], linewidth=2.0, color='black'
            )
        tme = datetime.datetime.now().strftime('%H%M%S')
        plt.savefig(
            fl := Path(
                f'{self.bot.files["transformations"].as_posix()}/'
                f'{tme}--{str(caller).replace("#", "")}--plot.png'
            )
        )
        plt.clf()
        return fl


class UtilFeatures(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name='modulo', aliases=['mod', 'modulus', 'remainder'])
    async def modulo(self, ctx: commands.Context, n1: float, n2: float):
        """remainder of divison. usage: `modulo n1, n2"""
        await ctx.send(f'{n1 % n2}')

    @commands.command(name='divmod', aliases=['floormod', 'floordivisionmodulo'])
    async def dvmd(self, ctx: commands.Context, n1: float, n2: float):
        """division with remainder. usage: `divmod n1, n2"""
        res = divmod(n1, n2)
        await ctx.send(f'{res[0]}; {res[1]}')


class Tasks(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.wotd_messages = []
        self.wotd_loop = None
        self.wotd()
        self.wotd_loop.start(self)

    async def cog_unload(self) -> None:
        self.wotd.cancel()
        await super().cog_unload()

    def wotd(self):  # we need tzi from bot, but we don't have that until init
        @tasks.loop(time=datetime.time(12, 10, 45, tzinfo=self.bot.timezoneinfo))
        async def wotd_inner(self):
            print("WOTD started")
            self.wotd_messages.clear()
            ebd = await self.get_wotd()
            for channel in await self.wotd_channels():
                msg = await channel.send(embed=ebd)
                self.wotd_messages.append(msg)

        self.wotd_loop = wotd_inner

    async def wotd_channels(self) -> list[discord.TextChannel]:
        return [
            self.bot.get_channel(956339556435759136),  # smesper general
            self.bot.get_channel(960200050389172344),  # testga cout
            self.bot.get_channel(972593770283565169),  # testoo clog
        ]

    async def get_wotd(self, redo=False) -> discord.Embed:
        yesterday = await self.bot.database.get_wotd_yesterday()
        title, summary, url, image = await wotd.oneworder()
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
    async def wotdmanual(self, ctx: commands.Context):
        self.wotd_messages.clear()
        ebd = await self.get_wotd()
        for channel in self.wotd_channels:
            msg = await channel.send(embed=ebd)
            self.wotd_messages.append(msg)
        await ctx.send('done.')

    @commands.command(name='wotdnew')
    @commands.is_owner()
    @commands.guild_only()
    async def wotdnew(self, ctx: commands.Context):
        def chk(m):
            return m.author == ctx.author and m.channel == ctx.channel

        await ctx.send("are you sure you want to change today's wotd?")
        try:
            m = await self.bot.wait_for('message', check=chk, timeout=10)
        except asyncio.TimeoutError:
            await ctx.send('wotd redo cancelled.')
            return
        if m.content == 'yes':
            ebd = await self.get_wotd(True)
            for k, channel in enumerate(self.wotd_channels):
                msg = await (
                    await channel.fetch_message(self.wotd_messages[k].id)
                ).edit(embed=ebd)
                self.wotd_messages[k] = msg
            await ctx.send('done.')
        else:
            await ctx.send('ok.')


async def setup(bot: commands.Bot):
    await bot.add_cog(GraphFeatures(bot))
    await bot.add_cog(UtilFeatures(bot))
    await bot.add_cog(Tasks(bot))
    print('LOADED features')

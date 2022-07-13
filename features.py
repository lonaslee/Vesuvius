from __future__ import annotations

import asyncio
import itertools
import math
import re
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from matplotlib import pyplot as plt

from extensions import ANSIColors as C
from extensions import transformations, trianglecenters

if TYPE_CHECKING:
    from extensions.transformations import Equation, Point
    from extensions.trianglecenters import MatPlotArg, PointDict
    from vesuvius import Vesuvius


class GraphFeatures(commands.Cog):
    """features cog that has the commands to invoke special features that use a graph"""

    def __init__(self, bot: Vesuvius) -> None:
        self.bot = bot

    @commands.command(name='trianglecenters')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    async def trianglecenters(self, ctx: commands.Context[Vesuvius], *, text: str = ''):
        """calculate orthocenter, circumcenter, and centroid from three coordinate points of a triangle. usage:
        \\`trianglecenters [x, y, x2, y2, x3, y3]"""
        a, b, c = {}, {}, {}
        nstr = False
        if text:
            if 'noword' in text:
                nstr = True
            match: list[str] = re.findall(r'(-?\d+.?\d*?[\s,]*?)', text)
            points = [float(p.strip(' ,(), ')) for p in match]
            try:
                a['x'], a['y'] = points[0], points[1]
                b['x'], b['y'] = points[2], points[3]
                c['x'], c['y'] = points[4], points[5]
            except ValueError:
                await ctx.send(
                    f'{C.B}{C.RED}this command must be invoked with all or no points.{C.E}'
                )
                return
        else:
            try:
                a['x'], a['y'] = await self.get_point(ctx, 1)  # type: ignore
                b['x'], b['y'] = await self.get_point(ctx, 2)  # type: ignore
                c['x'], c['y'] = await self.get_point(ctx, 3)  # type: ignore
            except TypeError:  # get_point timed out and returned None
                return
        try:
            fs, fsnw, mpa = await self.bot.run_in_tpexec(trianglecenters.main, a, b, c)
        except ValueError:
            await ctx.send(f'{C.B}{C.RED}not a triangle.{C.E}')
            return
        buffer = await self.plt_plt(mpa[0], mpa[1], mpa[2], a, b, c)
        buffer.seek(0)
        fobj = discord.File(
            buffer, f'trianglecenters-{datetime.utcnow().strftime("%m-%d-%H-%M")}.png'
        )
        embed_msg = discord.Embed(
            title='Triangle Centers',
            description=f'```py\n{fsnw if nstr else fs}```',
            color=discord.Colour.dark_green(),
            timestamp=datetime.utcnow(),
        )
        embed_msg.set_image(url=f'attachment://{fobj.filename}')
        await ctx.send(file=fobj, embed=embed_msg)

    async def get_point(
        self, ctx: commands.Context[Vesuvius], ptn: int | str
    ) -> tuple[float, float] | None | str:
        def chkp(m: discord.Message):
            return m.author == ctx.message.author and m.channel == ctx.channel

        await ctx.send(f'point {ptn}:')
        msg = None
        try:
            msg = await self.bot.wait_for('message', check=chkp, timeout=30)
            if msg.content == 'end':
                return 'end'
            x, y = re.search(
                r'(?P<x>-?\d+.?\d*?)[\s,]*?(?P<y>-?\d+.?\d*?)', msg.content
            ).groups()  # type: ignore
        except asyncio.TimeoutError:
            await ctx.send(f'{C.B}{C.RED}command timed out.{C.E}')
            return None
        except ValueError:
            assert msg is not None
            await ctx.send(
                f'{C.B}{C.RED}format error: cannot unpack {msg.content}.{C.E}'
            )
            return await self.get_point(ctx, ptn)
        return float(x), float(y)

    async def plt_plt(
        self,
        ortho: MatPlotArg,
        circum: MatPlotArg,
        medi: MatPlotArg,
        a_dict: PointDict,
        b_dict: PointDict,
        c_dict: PointDict,
    ) -> BytesIO:
        a = (a_dict['x'], a_dict['y'])
        b = (b_dict['x'], b_dict['y'])
        c = (c_dict['x'], c_dict['y'])
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
            plt.axhline(y=0, linewidth=2.0, color='dimgrey', linestyle='--')  # type: ignore
            plt.axvline(x=0, linewidth=2.0, color='dimgrey', linestyle='--')  # type: ignore
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
        cmbs = list(itertools.combinations([p for p in pt_tuples], 2))
        for cmb in cmbs:
            plt.plot(
                [cmb[0][0], cmb[1][0]],
                [cmb[0][1], cmb[1][1]],
                linewidth=2.0,
                color='black',
            )
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.clf()
        return buffer

    @commands.command(name='transformations')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    async def transformations(self, ctx: commands.Context[Vesuvius], *, text: str = ''):
        """compute translations, reflections, rotations, and dilations on a set of points. usage: `transformations [x, y, ...]"""
        point_list: list[tuple[float, float]]
        if text:
            match_list: list[str] = re.findall(r'(-?\d+.?\d*?[\s,]*?)', text)
            match_list = [pt.strip(' ,(), ') for pt in match_list]
            num_list = [float(p) for p in match_list]

            if len(point_list) % 2 != 0:
                await ctx.send(f'{C.B}{C.RED}Each point must have x and y.{C.E}')
                return

            point_list = [
                (num_list[d], num_list[d + 1]) for d in range(0, len(num_list), 2)
            ]

        else:
            for n in range(100):
                tup = await self.get_point(ctx, f'{n+1} (send "end" to stop)')

                if isinstance(tup, str):
                    break
                if tup is None:
                    return  # timeout

                point_list.append(tup)

        aps = await self.bot.run_in_tpexec(
            lambda: transformations.AllPoints(point_list)
        )
        prompt = await ctx.send('transformation (send "end" to stop):')
        for n in range(100):
            prompt = await prompt.edit(
                content=f'transformation {n} (send "end" to stop):'
            )
            res = await self.get_inp(ctx)
            if res is None:
                return
            if not isinstance(res, str):
                m, a = res
                await self.bot.run_in_tpexec(lambda: getattr(aps, m)(a))
            ap_str = '\n'.join([str(p) for p in aps.allpoints])
            embed_msg = discord.Embed(
                title='Transformations',
                description=ap_str,
                colour=discord.Colour.dark_blue(),
                timestamp=datetime.utcnow(),
            )
            buffer = await self.graph_fig(aps)
            buffer.seek(0)
            fobj = discord.File(
                buffer,
                f'transformations-{datetime.utcnow().strftime("%m-%d-%H-%M")}.png',
            )
            embed_msg.set_image(url=f'attachment://{fobj.filename}')
            await ctx.send(file=fobj, embed=embed_msg)
            if res == 'end':
                return

    async def get_inp(
        self, ctx: commands.Context[Vesuvius]
    ) -> tuple[str, Point | Equation | tuple[Point, float]] | str | None:
        def chk(m: discord.Message):
            return m.author == ctx.message.author and m.channel == ctx.channel

        msg = None
        try:
            msg = await self.bot.wait_for('message', check=chk, timeout=30)
            if msg.content == 'end':
                return 'end'
            return await self.bot.run_in_tpexec(
                transformations.Inputs().main, msg.content
            )
        except asyncio.TimeoutError:
            await ctx.send(f'{C.B}{C.RED}Command timed out.{C.E}')
            return None
        except ValueError:
            assert msg is not None
            await ctx.send(
                f'{C.B}{C.RED}format error: cannot unpack {msg.content}{C.E}'
            )
            return await self.get_inp(ctx)

    async def graph_fig(self, apts: transformations.AllPoints) -> BytesIO:
        avs = list(itertools.chain.from_iterable([[p.x, p.y] for p in apts.allpoints]))
        mx, mn = round(max(avs)), round(min(avs))
        axis = mx * 1.25 if mx > abs(mn) else mn * 1.25
        if axis >= 0:
            plt.xlim(0, axis)
            plt.ylim(0, axis)
        else:
            plt.xlim(axis, axis * -1)
            plt.ylim(axis, axis * -1)
            plt.axhline(y=0, linewidth=2.0, color='dimgrey', linestyle='--')  # type: ignore
            plt.axvline(x=0, linewidth=2.0, color='dimgrey', linestyle='--')  # type: ignore
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
        cmbs = list(itertools.combinations(apts.allpoints, 2))
        for cmb in cmbs:
            plt.plot(
                [cmb[0].x, cmb[1].x], [cmb[0].y, cmb[1].y], linewidth=2.0, color='black'
            )
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.clf()
        return buffer


class UtilFeatures(commands.Cog):
    def __init__(self, bot: Vesuvius) -> None:
        self.bot = bot

    @commands.command(name='modulo', aliases=['remainder'])
    async def modulo(self, ctx: commands.Context[Vesuvius], n1: float, n2: float):
        """remainder of divison. usage: `modulo n1, n2"""
        await ctx.send(f'{n1 % n2}')

    @commands.command(name='divmod')
    async def dvmd(self, ctx: commands.Context[Vesuvius], n1: float, n2: float):
        """division with remainder. usage: `divmod n1, n2"""
        res = divmod(n1, n2)
        await ctx.send(f'{res[0]}; {res[1]}')

    @commands.command(name='permutations', aliases=['nPr', 'npr'])
    @commands.max_concurrency(1, commands.BucketType.default)
    @commands.cooldown(1, 360, commands.BucketType.default)
    async def npr(self, ctx: commands.Context[Vesuvius], length: int, *args: str):
        """n length permutations of given arguments. usage: `permutations length, ..."""
        if len(args) == 1:
            args = tuple(args[0])
        sep = ''
        if 'sep=' in args[-1]:
            sep = args[-1][4:]
            args = tuple(args[0:-1])
        if sep == 'space':
            sep = ' '
        numof = math.factorial(arg_len := len(args)) / math.factorial(arg_len - length)
        if numof > 2000:
            await ctx.send(
                f'{C.B}{C.RED}result too large.{C.GREEN} number of permutations: '
                f'{C.CYAN}{numof}.{C.END}'
            )
            return
        pers = await self.bot.run_in_tpexec(
            lambda: itertools.permutations(args, length)
        )
        joined = '\n'.join([sep.join(a) for a in pers])
        s_now = datetime.now().strftime('%m_%d_%y__%H_%M_%S')
        if numof > 40:
            buffer = BytesIO()
            buffer.write(bytes(joined, encoding='utf-8'))
            buffer.seek(0)
            fobj = discord.File(buffer, filename=f'permutations_{s_now}.txt')
            await ctx.send(
                f'{C.B}{C.GREEN}{numof} permutations of {length} length in attached file:{C.E}',
                file=fobj,
            )
        else:
            await ctx.send(
                f'{C.B}{C.GREEN}{numof} permutations of {length} length:{C.CYAN}\n{joined}{C.E}'
            )

    @commands.command(name='combinations', aliases=['nCr', 'ncr'])
    @commands.max_concurrency(1, commands.BucketType.default)
    @commands.cooldown(1, 360, commands.BucketType.default)
    async def ncr(self, ctx: commands.Context[Vesuvius], length: int, *args: str):
        """n length combinations of given arguments. usage: `combinations length, ..."""
        if len(args) == 1:
            args = tuple(args[0])
        sep = ''
        if 'sep=' in args[-1]:
            sep = args[-1][4:]
            args = tuple(args[0:-1])
        numof = (
            math.factorial(arg_len := len(args))
            / math.factorial(length)
            * math.factorial(arg_len - length)
        )
        if numof > 2000:
            await ctx.send(
                f'{C.B}{C.RED}result too large.{C.GREEN} number of permutations: '
                f'{C.CYAN}{numof}.{C.END}'
            )
            return
        pers = await self.bot.run_in_tpexec(
            lambda: itertools.combinations(args, length)
        )
        joined = '\n'.join([sep.join(a) for a in pers])
        s_now = datetime.now().strftime('%m_%d_%y__%H_%M_%S')
        if numof > 40:
            buffer = BytesIO()
            buffer.write(bytes(joined, encoding='utf-8'))
            fobj = discord.File(buffer, filename=f'combinations_{s_now}.txt')
            await ctx.send(
                f'{C.B}{C.GREEN}{numof} combinations of {length} length in attached file:{C.E}',
                file=fobj,
            )
        else:
            await ctx.send(
                f'{C.B}{C.GREEN}{numof} combinations of {length} length:{C.CYAN}\n{joined}{C.E}'
            )


async def setup(bot: Vesuvius):
    await bot.add_cog(GraphFeatures(bot))
    await bot.add_cog(UtilFeatures(bot))
    print('LOADED features')

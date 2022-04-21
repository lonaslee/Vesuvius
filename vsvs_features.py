from __future__ import annotations
import discord
import asyncio
import re
from features import trianglecenters, transformations, tictactoe, connectfour, reversi
from random import randint
from datetime import datetime
from time import time
from concurrent.futures import ThreadPoolExecutor
from matplotlib import pyplot as plt
from itertools import combinations, chain
from discord.ext import commands


class GraphFeatures(commands.Cog):
    """features cog that has the commands to invoke special features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name='trianglecenters')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType(1))
    async def trianglecenters(self, ctx: commands.Context, *, text: str = None):
        """calculate orthocenter, circumcenter, and centroid from
        three coordinate points of a triangle.

        implemented from an old command line program I wrote.
        """
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
            fs, fsnw, mpa = await self.executor(lambda: trianglecenters.main(a, b, c))
        except ValueError:
            ctx.send(
                f'not a triangle. if there is nothing wrong with your input, '
                f'report the error to @\u200b{ctx.guild.get_member(self.bot.owner_id)}'
            )
            return
        path = await self.plt_plt(ctx.message.author, mpa[0], mpa[1], mpa[2], a, b, c)
        fobj = discord.File(
            path, filename=path.removeprefix('vsvs_files/trianglecenters/')
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

    @staticmethod
    async def plt_plt(
        caller, ortho: tuple, circum: tuple, medi: tuple, a: dict, b: dict, c: dict
    ):
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
        axis = mx * 1.25 if mx > abs(mn) else mn * 1.25
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
                lambda x, y, m, c: plt.plot(  # plot all points
                    [x],
                    [y],
                    marker=m,
                    markersize=5,
                    markeredgecolor=c,
                    markerfacecolor=c,
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
        tme = datetime.now().strftime('%H%M%S')
        plt.savefig(
            fl := f'vsvs_files/trianglecenters/{tme}--{str(caller).replace("#", "")}--plot.png'
        )
        plt.clf()
        return fl

    # =========================================================================

    @commands.command(name='transformations')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType(1))
    async def transformations(self, ctx: commands.Context, *, text: str = None):
        """compute translations, reflections, rotations,
        and dilations on a set of points

        implemented from a command line program I wrote.
        """
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
        aps = await self.executor(lambda: transformations.AllPoints(pt_lst))
        ap_str = '\n'.join([str(p) for p in aps.allpoints])
        for n in range(100):
            res = await self.get_inp(ctx)
            if res is None:
                return
            if res != 'end':
                m, a = res
                await self.executor(lambda: getattr(aps, m)(a))
            ap_str = '\n'.join([str(p) for p in aps.allpoints])
            embed_msg = discord.Embed(
                title='Transformations',
                description=ap_str,
                colour=discord.Colour.dark_blue(),
                timestamp=datetime.utcnow(),
            )
            path = await self.graph_fig(aps, ctx.message.author)
            fobj = discord.File(
                path, filename=path.removeprefix('vsvs_files/transformations/')
            )
            embed_msg.set_image(url=f'attachment://{fobj.filename}')
            await ctx.send(file=fobj, embed=embed_msg)
            if res == 'end':
                return

    async def get_inp(self, ctx: commands.Context) -> tuple | str | None:
        await ctx.send('transformation:')

        def chki(m):
            return m.author == ctx.message.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for(event='message', check=chki, timeout=30)
            if msg.content == 'end':
                return 'end'
            ap_mtd, ap_args = await self.executor(
                lambda: transformations.Inputs().main(msg.content)
            )
        except asyncio.TimeoutError:
            await ctx.send('command timed out.')
            return None
        except ValueError:
            await ctx.send(f'format error: cannot unpack {msg.content}')
            return await self.get_inp(ctx)
        return ap_mtd, ap_args

    @staticmethod
    async def graph_fig(apts: transformations.AllPoints, caller):
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
        tme = datetime.now().strftime('%H%M%S')
        plt.savefig(
            fl := f'vsvs_files/transformations/{tme}--{str(caller).replace("#", "")}--plot.png'
        )
        plt.clf()
        return fl

    @staticmethod
    async def executor(func):
        res = await asyncio.get_event_loop().run_in_executor(
            ThreadPoolExecutor(1), func
        )
        return res


# =============================================================================


class GameFeatures(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ingame = []

    @commands.command(name='ingames')
    @commands.cooldown(rate=1, per=300, type=commands.BucketType(2))
    async def ingames(self, ctx: commands.Context, clear: bool = False):
        await ctx.send(str(self.ingame))
        if clear:
            self.ingame = []
            await ctx.send('cleared!')

    @commands.command(name='tictactoe')
    async def tictactoe(self, ctx: commands.Context, opponent: discord.guild.Member):
        """play tic-tac-toe with another user"""
        if await self.wait_confirm(ctx, opponent, 'tic-tac-toe'):
            plyr_x: discord.Member
            plyr_o: discord.Member
            if randint(0, 1):
                plyr_x, plyr_o = ctx.message.author, opponent
            else:
                plyr_x, plyr_o = opponent, ctx.message.author
            await ctx.send(f'X: {plyr_x.display_name}, O: {plyr_o.display_name}')
            bd = tictactoe.Board()
            msg_bd = await ctx.send(str(bd))
            prompt = await ctx.send(f"{plyr_x.mention} X's turn! (send coordinates)")
            for n in range(1, 10):
                if n % 2 == 0:
                    turn = plyr_o
                    await prompt.edit(
                        content=f"{plyr_o.mention} O's turn! (send coordinates)"
                    )
                else:
                    turn = plyr_x
                    await prompt.edit(
                        content=f"{plyr_x.mention} X's turn! (send coordinates)"
                    )
                try:
                    x, y = await self.ttt_move(ctx, plyr_o, plyr_x, turn)
                except TypeError:
                    await self.done_playing(plyr_x, plyr_o)
                    return
                while w := await bd.assign_square(x, y):
                    if w in {'X', 'O'}:
                        await msg_bd.edit(content=str(bd))
                        await prompt.edit(
                            content=f'winner is {w}, '
                            f'{plyr_x.display_name if w == "X" else plyr_o.display_name}!'
                        )
                        await self.done_playing(plyr_x, plyr_o)
                        return
                    if w == 'occupied':
                        errm = await ctx.send(
                            f'{turn.display_name}: {x, y} is already occupied, '
                            'are you blind? try another spot.'
                        )
                        x, y = await self.ttt_move(ctx, plyr_o, plyr_x, turn)
                        await errm.delete()
                    else:
                        break
                await msg_bd.edit(content=str(bd))
            await prompt.edit(content=f'draw!')
        else:
            await self.done_playing(plyr_x, plyr_o)
            return

    async def ttt_move(
        self,
        ctx: commands.Context,
        po: discord.Member,
        px: discord.Member,
        pr: discord.Member,
    ):
        def chkt(m):
            return m.author == pr and m.channel == ctx.channel

        try:
            cds = await self.bot.wait_for('message', check=chkt, timeout=30)
        except asyncio.TimeoutError:
            faster = await ctx.send(
                f'{pr.mention} hurry up! it takes you more than '
                '30 seconds to make a move in tic-tac-toe?'
            )
            try:
                cds = await self.bot.wait_for('message', check=chkt, timeout=30)
                await faster.delete()
            except asyncio.TimeoutError:
                await ctx.send(
                    f'game ended. {px.display_name if pr is po else po.display_name} '
                    f'is winner, because {pr.display_name} took over a 60 '
                    'seconds to make a move in fricking tic-tac-toe.'
                )
                return
        try:
            x, y = re.search(r'(?P<x>\d)[(), ]*(?P<y>\d)', cds.content).groups()
        except AttributeError:
            errm = await ctx.send(f'must have x and y positions. try again')
            await cds.delete()
            x, y = await self.ttt_move(ctx, po, px, pr)
            await errm.delete()
            return x, y
        if not x or not y:
            errm = await ctx.send(f'incorrect formatting: {cds.content}. try again')
            await cds.delete()
            x, y = await self.ttt_move(ctx, po, px, pr)
            await errm.delete()
            return x, y
        if x not in {'1', '2', '3'} or y not in {'1', '2', '3'}:
            errm = await ctx.send(f'off board range: {x, y}. try again')
            await cds.delete()
            x, y = await self.ttt_move(ctx, po, px, pr)
            await errm.delete()
            return x, y
        await cds.delete()
        return x, y

    # =========================================================================

    @commands.command(name='connectfour', aliases=['connect4'])
    async def connectfour(self, ctx: commands.Context, opponent: discord.guild.Member):
        """play connect-four with another user"""
        if await self.wait_confirm(ctx, opponent, 'connect-four'):
            plyr_r: discord.Member
            plyr_y: discord.Member
            if randint(0, 1):
                plyr_r, plyr_y = ctx.message.author, opponent
            else:
                plyr_r, plyr_y = opponent, ctx.message.author
            await ctx.send(
                f'```ansi\n\u001b[0m\u001b[1;33mYellow: {plyr_y.display_name}, \u001b[1;31mRed: {plyr_r.display_name}```'
            )
            bd = connectfour.C4Board()
            sbd = await bd.as_string()
            msg_bd1 = await ctx.send(sbd[0])
            msg_bd2 = await ctx.send(sbd[1])
            num17 = (
                '1\N{variation selector-16}\N{combining enclosing keycap}',
                '2\N{variation selector-16}\N{combining enclosing keycap}',
                '3\N{variation selector-16}\N{combining enclosing keycap}',
                '4\N{variation selector-16}\N{combining enclosing keycap}',
                '5\N{variation selector-16}\N{combining enclosing keycap}',
                '6\N{variation selector-16}\N{combining enclosing keycap}',
                '7\N{variation selector-16}\N{combining enclosing keycap}',
            )
            for rtion in num17:
                await msg_bd2.add_reaction(rtion)
            prompt = await ctx.send(
                f"{plyr_y.mention} Yellow's turn! (react under column)"
            )
            for n in range(1, 43):
                if n % 2 == 0:
                    turn = plyr_r
                    await prompt.edit(
                        content=f"{plyr_r.mention} Red's Turn! (react under column)"
                    )
                else:
                    turn = plyr_y
                    await prompt.edit(
                        content=f"{plyr_y.mention} Yellow's Turn! (react under column)"
                    )
                row = await self.c4_move(ctx, plyr_r, plyr_y, turn)
                if row is None:
                    await self.done_playing(plyr_r, plyr_y)
                    return
                while res := await bd.drop_square(row):
                    if res == 'column full':
                        errm = await ctx.send(
                            f'{turn.display_name}: row {row} is already full, '
                            'are you blind? try another row.'
                        )
                        row = await self.c4_move(ctx, plyr_r, plyr_y, turn)
                        await errm.delete()
                        sbd = await bd.as_string()
                        await msg_bd1.edit(content=sbd[0])
                        await msg_bd2.edit(content=sbd[1])
                        continue
                    if res in {'YW', 'RW'}:
                        sbd = await bd.as_string()
                        await msg_bd1.edit(content=sbd[0])
                        await msg_bd2.edit(content=sbd[1])
                        await prompt.edit(
                            content=f'''```ansi\n\u001b[0m\u001b[1;{33 if res == "YW" else 31}mwinner is {"Yellow" if res == "YW" else "Red"}, {plyr_y.display_name if res == "YW" else plyr_r.display_name}!```'''
                        )
                        await self.done_playing(plyr_r, plyr_y)
                        return
                    else:
                        sbd = await bd.as_string()
                        await msg_bd1.edit(content=sbd[0])
                        await msg_bd2.edit(content=sbd[1])
                        break
            await prompt.edit(content='draw!')
        else:
            await self.done_playing(plyr_r, plyr_y)
            return

    async def c4_move(
        self,
        ctx: commands.Context,
        pr: discord.Member,
        py: discord.Member,
        prn: discord.Member,
    ):
        num17 = (
            '1\N{variation selector-16}\N{combining enclosing keycap}',
            '2\N{variation selector-16}\N{combining enclosing keycap}',
            '3\N{variation selector-16}\N{combining enclosing keycap}',
            '4\N{variation selector-16}\N{combining enclosing keycap}',
            '5\N{variation selector-16}\N{combining enclosing keycap}',
            '6\N{variation selector-16}\N{combining enclosing keycap}',
            '7\N{variation selector-16}\N{combining enclosing keycap}',
        )

        def chkf(r, u):
            return u == prn and str(r.emoji) in num17

        try:
            reaction, user = await self.bot.wait_for(
                'reaction_add', check=chkf, timeout=30
            )
        except asyncio.TimeoutError:
            faster = await ctx.send(
                f'{prn.mention} hurry up! it takes you more than '
                '30 seconds to make a move in connect-four?'
            )
            try:
                reaction, user = await self.bot.wait_for(
                    'reaction_add', check=chkf, timeout=30
                )
                await faster.delete()
            except asyncio.TimeoutError:
                await ctx.send(
                    f'game ended. {py if pr is prn else pr} is winner, because '
                    f'{pr.display_name} took over 60 seconds to make '
                    'a move in fricking connect-four.'
                )
                return
        num = str(reaction.emoji)[0]
        await reaction.remove(user)
        return num

    @commands.command(name='reversi', aliases=['othello'])
    async def reversi(
        self, ctx: commands.Context, opponent: discord.guild.Member, length: int = 10
    ):
        """play reversi with another user"""
        if await self.wait_confirm(ctx, opponent, ctx.invoked_with):
            if length not in list(range(60)):
                length = 10
            endtime = time() + length * 60
            black: discord.Member
            white: discord.Member
            if randint(0, 1):
                black, white = ctx.message.author, opponent
            else:
                black, white = opponent, ctx.message.author
            await ctx.send(
                f'```ansi\n\u001b[0m\u001b[1;32mTime limit: {length} minutes!\n\u001b[1;45;1;30mBlack: {black.display_name}, \u001b[1;45;1;37mWhite: {white.display_name}```'
            )
            bd = reversi.Board()
            sbd = await bd.as_string()
            msg_bd1 = await ctx.send(sbd[0])
            msg_bd2 = await ctx.send(sbd[1])
            msg_bd3 = await ctx.send(sbd[2])
            prompt = await ctx.send(f"{black.mention} Black's turn! (send coordinates)")
            last = white
            for n in range(64):
                if time() >= endtime:
                    winner = await bd.count_all()
                    if winner[0] != 'D':
                        await prompt.edit(
                            content=f"```ansi\n\u001b[1;45;1;{30 if winner[0] == 'Black' else 37}m"
                            f"Time's up! winner is {winner[0]}, "
                            f'{black.display_name if winner[0] == "Black" else white.display_name} '
                            f'with {winner[1]} circles!```'
                        )
                        await self.done_playing(black, white)
                        return
                    await prompt.edit(content='Draw!')
                    await self.done_playing(black, white)
                    return
                if not await bd.possible('B'):
                    await prompt.edit(content=f'winner is White, {white.display_name}!')
                    await self.done_playing(black, white)
                    return
                if not await bd.possible('W'):
                    await prompt.edit(content=f'winner is Black, {black.display_name}!')
                    await self.done_playing(black, white)
                    return
                if last is black:
                    turn = last = white
                    await prompt.edit(
                        content=f"{white.mention} White's turn! (send coordinates)"
                    )
                else:
                    turn = last = black
                    await prompt.edit(
                        content=f"{black.mention} Black's turn! (send coordinates)"
                    )
                res = await self.rvsi_move(ctx, black, white, turn, prompt)
                if not res:
                    await self.done_playing(black, white)
                    return
                while not await bd.assign_square(
                    res[0], res[1], 'B' if turn is black else 'W'
                ):
                    errm = await ctx.send('not a valid spot. try again')
                    res = await self.rvsi_move(ctx, black, white, turn, prompt)
                    await errm.delete()
                sbd1, sbd2, sbd3 = await bd.as_string()
                await msg_bd1.edit(content=sbd1)
                await msg_bd2.edit(content=sbd2)
                await msg_bd3.edit(content=sbd3)
            winner = await bd.count_all()
            if winner[0] != 'D':
                await prompt.edit(
                    content=f'```ansi\n\u001b[1;45;1;{30 if winner[0] == "Black" else 37}'
                    f'mwinner is {winner[0]}, '
                    f'{black.display_name if winner[0] == "Black" else white.display_name} '
                    f'with {winner[1]} circles!```'
                )
                await self.done_playing(black, white)
                return

    async def rvsi_move(
        self,
        ctx: commands.Context,
        b: discord.Member,
        w: discord.Member,
        pr: discord.Member,
        ppt: discord.Member,
    ) -> tuple:
        def chkr(m):
            return m.author == pr and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', check=chkr, timeout=60)
        except asyncio.TimeoutError:
            await ppt.edit(content=f'{pr.mention} hurry up!')
            try:
                msg = await self.bot.wait_for('message', check=chkr, timeout=60)
            except asyncio.TimeoutError:
                await ppt.edit(
                    content=f'game ended. {b.display_name if pr is w else w.display_name} '
                    f'is winner, because {pr.display_name} took too long to make a move!'
                )
                return ()
            return x, y
        try:
            x, y = re.search(r'(?P<x>\d)[(), ]*(?P<y>\d)', msg.content).groups()
        except AttributeError:
            await msg.delete()
            fmterr = await ctx.send('must have x and y positions. try again')
            x, y = await self.rvsi_move(ctx, b, w, pr)
            await fmterr.delete()
            return x, y
        if not x or not y:
            await msg.delete()
            fmterr = await ctx.send('must have x and y positions. try again')
            x, y = await self.rvsi_move(ctx, b, w, pr)
            await fmterr.delete()
            return x, y
        if int(x) not in (st := set(range(1, 9))) or int(y) not in st:
            await msg.delete()
            rgerr = await ctx.send('off board range. try again')
            x, y = await self.rvsi_move(ctx, b, w, pr)
            await rgerr.delete()
            return x, y
        await msg.delete()
        return x, y

    async def wait_confirm(
        self, octx: commands.Context, opp: discord.guild.Member, game: str
    ) -> int:
        """wait for confirmation that the opp wants to play game"""
        if octx.author in self.ingame:
            await octx.send('you are already in another game.')
            return 0
        if opp in self.ingame:
            await octx.send(
                f'{opp.display_name} is already in another game. '
                'wait for it to finish or try another person!'
            )
            return
        if opp == octx.author:
            await octx.send('you cannot challenge yourself.')
            return 0
        if opp == self.bot.user:
            await octx.send('no.')
            return 0
        self.ingame.append(octx.author)
        inv = await octx.send(
            f'{octx.message.author.display_name} has challenged {opp.display_name} '
            f'to a match of {game}! {opp.mention}, do you accept? '
            '(react with :white_check_mark: or :negative_squared_cross_mark:)'
        )
        await inv.add_reaction('✅')
        await inv.add_reaction('❎')

        def chk(r, u):
            return u == opp and str(r.emoji) in '✅❎'

        try:
            reaction, user = await self.bot.wait_for(
                'reaction_add', check=chk, timeout=30
            )
        except asyncio.TimeoutError:
            await octx.send(
                f'command timed out. it seems that {opp.display_name} '
                'does not want to play rn. try someone else!'
            )
            self.ingame.remove(octx.author)
            return 0
        if str(reaction.emoji) == '❎':
            await inv.reply(f'{opp.display_name} did not accept the challenge.')
            self.ingame.remove(octx.author)
            return 0
        else:
            await inv.reply(f'{opp.display_name} has accepted the challenge!')
            self.ingame.append(opp)
            return 1

    async def done_playing(self, *args):
        for player in args:
            self.ingame.remove(player)


# =============================================================================


class UtilFeatures(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot


def setup(bot: commands.Bot):
    bot.add_cog(GraphFeatures(bot))
    bot.add_cog(GameFeatures(bot))
    bot.add_cog(UtilFeatures(bot))

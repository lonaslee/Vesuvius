from __future__ import annotations
import discord
import asyncio
import re
import aiofile
from features import tictactoe, connectfour, reversi, weiqi
from random import randint
from datetime import datetime
from time import time
from discord.ext import commands


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

    @commands.command(name='tictactoe', aliases=['ttt'])
    async def tictactoe(self, ctx: commands.Context, opponent: discord.guild.Member):
        """play tic-tac-toe with another user. usage: `tictactoe member"""
        if await self.wait_confirm(ctx, opponent, 'tic-tac-toe'):
            plyr_x: discord.Member
            plyr_o: discord.Member
            if randint(0, 1):
                plyr_x, plyr_o = ctx.message.author, opponent
            else:
                plyr_x, plyr_o = opponent, ctx.message.author
            await ctx.send(f'X: {plyr_x.display_name}, O: {plyr_o.display_name}')
            bd = await self.bot.run_in_tpexec(lambda: tictactoe.Board())
            msg_bd = await ctx.send(await bd.as_string())
            prompt = await ctx.send(f"{plyr_x.mention} X's turn! (send coordinates)")
            for n in range(1, 10):
                if n % 2 == 0:
                    turn = plyr_o
                    prompt = await prompt.edit(
                        content=f"{plyr_o.mention} O's turn! (send coordinates)"
                    )
                else:
                    turn = plyr_x
                    prompt = await prompt.edit(
                        content=f"{plyr_x.mention} X's turn! (send coordinates)"
                    )
                try:
                    x, y = await self.ttt_move(ctx, plyr_o, plyr_x, turn)
                except TypeError:
                    print("KLDFJKLSDFJSDKLFJSDKL")
                    await self.done_playing(
                        'tictactoe', plyr_x if turn is plyr_o else plyr_o, turn
                    )
                    return
                while w := await bd.assign_square(x, y):
                    if w in {'X', 'O'}:
                        winner = plyr_x if w == "X" else plyr_o
                        msg_bd = await msg_bd.edit(content=await bd.as_string())
                        prompt = await prompt.edit(
                            content=f'winner is {w}, ' f'{winner.display_name}!'
                        )
                        await self.done_playing(
                            'tictactoe', winner, plyr_o if winner is plyr_x else plyr_x
                        )
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
                msg_bd = await msg_bd.edit(content=await bd.as_string())
            prompt = await prompt.edit(content=f'draw!')
            await self.done_playing('tictactoe', plyr_x, plyr_o, tie=True)

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

    @commands.command(name='connectfour', aliases=['connect4', 'cf'])
    async def connectfour(self, ctx: commands.Context, opponent: discord.guild.Member):
        """play connect-four with another user. usage: `connect4 member"""
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
            bd = await self.bot.run_in_tpexec(connectfour.C4Board)
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
                    prompt = await prompt.edit(
                        content=f"{plyr_r.mention} Red's Turn! (react under column)"
                    )
                else:
                    turn = plyr_y
                    prompt = await prompt.edit(
                        content=f"{plyr_y.mention} Yellow's Turn! (react under column)"
                    )
                row = await self.c4_move(ctx, plyr_r, plyr_y, turn)
                if row is None:
                    await self.done_playing(
                        'connectfour', plyr_r if turn is plyr_y else plyr_y, turn
                    )
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
                        msg_bd1 = await msg_bd1.edit(content=sbd[0])
                        msg_bd2 = await msg_bd2.edit(content=sbd[1])
                        continue
                    if res in {'YW', 'RW'}:
                        sbd = await bd.as_string()
                        winner = plyr_y if res == "YW" else plyr_r
                        msg_bd1 = await msg_bd1.edit(content=sbd[0])
                        msg_bd2 = await msg_bd2.edit(content=sbd[1])
                        prompt = await prompt.edit(
                            content=f'''```ansi\n\u001b[0m\u001b[1;{33 if res == "YW" else 31}mwinner is {"Yellow" if res == "YW" else "Red"}, {winner.display_name}!```'''
                        )

                        await self.done_playing(
                            'connectfour',
                            winner,
                            plyr_y if winner is plyr_r else plyr_r,
                        )
                        return
                    else:
                        sbd = await bd.as_string()
                        msg_bd1 = await msg_bd1.edit(content=sbd[0])
                        msg_bd2 = await msg_bd2.edit(content=sbd[1])
                        break
            prompt = await prompt.edit(content='draw!')

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

    @commands.command(name='reversi', aliases=['othello', 'oto'])
    async def reversi(
        self, ctx: commands.Context, opponent: discord.guild.Member, length: int = 10
    ):
        """play reversi with another user. usage: `reversi member [length]"""
        if await self.wait_confirm(
            ctx,
            opponent,
            ctx.invoked_with
            if ctx.invoked_with in {'reversi', 'othello'}
            else 'Reversi',
        ):
            if length not in range(91):
                length = 15
            endtime = time() + length * 60
            black: discord.Member
            white: discord.Member
            if randint(0, 1):
                black, white = ctx.message.author, opponent
            else:
                black, white = opponent, ctx.message.author
            await ctx.send(
                f'```ansi\n\u001b[0m\u001b[1;32mTime limit: {length} minutes!\n\u001b[1;45;1;30mBlack: '
                f'{black.display_name}, \u001b[1;45;1;37mWhite: {white.display_name}```'
            )
            bd = await self.bot.run_in_tpexec(reversi.Board)
            sbd = await bd.as_string()
            msg_bd1 = await ctx.send(sbd[0])
            msg_bd2 = await ctx.send(sbd[1])
            msg_bd3 = await ctx.send(sbd[2])
            prompt = await ctx.send(f"{black.mention} Black's turn! (send coordinates)")
            last = white
            for n in range(64):
                if time() >= endtime:
                    winner = await bd.count_all()
                    if winner[0] != 'Draw':
                        wnr = black if winner[0] == "Black" else white
                        prompt = await prompt.edit(
                            content=f"```ansi\n\u001b[1;45;1;{30 if winner[0] == 'Black' else 37}m"
                            f"Time's up! winner is {winner[0]}, {wnr.display_name} "
                            f'with {winner[1]} circles!```'
                        )
                        await self.done_playing(
                            'reversi', wnr, white if wnr is black else black
                        )
                        return
                    prompt = await prompt.edit(content=f'Draw! - {winner[1]}')
                    await self.done_playing('reversi', black, white, tie=True)
                    return
                if not await bd.possible('B'):
                    prompt = await prompt.edit(
                        content=f'winner is White, {white.display_name}!'
                    )
                    await self.done_playing('reversi', white, black)
                    return
                if not await bd.possible('W'):
                    prompt = await prompt.edit(
                        content=f'winner is Black, {black.display_name}!'
                    )
                    await self.done_playing('reversi', black, white)
                    return
                if last is black:
                    turn = last = white
                    prompt = await prompt.edit(
                        content=f"{white.mention} White's turn! (send coordinates)"
                    )
                else:
                    turn = last = black
                    prompt = await prompt.edit(
                        content=f"{black.mention} Black's turn! (send coordinates)"
                    )
                res = await self.rvsi_move(ctx, black, white, turn, prompt)
                if not res:
                    await self.done_playing(
                        'reversi', black if turn is white else white, turn
                    )
                    return
                if res == (None,):
                    winner = await bd.count_all()
                    if winner[0] != 'D':
                        wnr = black if winner[0] == "Black" else white
                        prompt = await prompt.edit(
                            content=f'```ansi\n\u001b[1;45;1;{30 if winner[0] == "Black" else 37}'
                            f'mwinner is {winner[0]}, {wnr.display_name} '
                            f'with {winner[1]} circles!```'
                        )
                        await self.done_playing(
                            'reversi', wnr, black if wnr is white else white
                        )
                        return
                    else:
                        prompt = await prompt.edit(content=f'Draw! - {winner[1]}')
                        await self.done_playing('reversi', black, white, tie=True)
                        return
                while not await bd.assign_square(
                    res[0], res[1], 'B' if turn is black else 'W'
                ):
                    errm = await ctx.send('not a valid spot. try again')
                    res = await self.rvsi_move(ctx, black, white, turn, prompt)
                    await errm.delete()
                sbd1, sbd2, sbd3 = await bd.as_string()
                msg_bd1 = await msg_bd1.edit(content=sbd1)
                msg_bd2 = await msg_bd2.edit(content=sbd2)
                msg_bd3 = await msg_bd3.edit(content=sbd3)
            winner = await bd.count_all()
            if winner[0] != 'D':
                wnr = black if winner[0] == "Black" else white
                prompt = await prompt.edit(
                    content=f'```ansi\n\u001b[1;45;1;{30 if winner[0] == "Black" else 37}'
                    f'mwinner is {winner[0]}, {wnr.display_name} '
                    f'with {winner[1]} circles!```'
                )
                await self.done_playing(
                    'reversi', wnr, black if wnr is white else white
                )
                return
            else:
                prompt = await prompt.edit(content=f'Draw! - {winner[1]}')
                await self.done_playing('reversi', black, white, tie=True)
                return

    async def rvsi_move(
        self,
        ctx: commands.Context,
        b: discord.Member,
        w: discord.Member,
        pr: discord.Member,
        ppt: discord.Message,
    ) -> tuple:
        def chkr(m):
            return m.author == pr and m.channel == ctx.channel

        def chkr2(m):
            return m.author == (b if pr is w else w) and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', check=chkr, timeout=60)
        except asyncio.TimeoutError:
            ppt = await ppt.edit(content=f'{pr.mention} hurry up!')
            try:
                msg = await self.bot.wait_for('message', check=chkr, timeout=60)
            except asyncio.TimeoutError:
                ppt = await ppt.edit(
                    content=f'game ended. {b.display_name if pr is w else w.display_name} '
                    f'is winner, because {pr.display_name} took too long to make a move!'
                )
                return ()
            return x, y
        if msg.content == 'end':
            ppt = await ppt.edit(
                content=f'{b.mention if pr is w else w.mention}'
                f'{pr.display_name} wants to end the game now!'
                'if you agree, respond with yes, else say'
            )
            try:
                resp = await self.bot.wait_for('message', check=chkr2, timeout=80)
                if resp.content.lower() in {'end', 'yes', 'y', 'ok', 'ye'}:
                    await resp.delete()
                    await msg.delete()
                    return (None,)
            except asyncio.TimeoutError:
                pass
            await msg.delete()
            ppt = await ppt.edit(
                content=f'{pr.mention} your opponent has decided to continue! '
                '(now send coordinates)'
            )
            return await self.rvsi_move(ctx, b, w, pr, ppt)
        try:
            x, y = re.search(r'(?P<x>\d)[(), ]*(?P<y>\d)', msg.content).groups()
        except (AttributeError, ValueError):
            await msg.delete()
            fmterr = await ctx.send('must have x and y positions. try again')
            x, y = await self.rvsi_move(ctx, b, w, pr, ppt)
            await fmterr.delete()
            return x, y
        if not x or not y:
            await msg.delete()
            fmterr = await ctx.send('must have x and y positions. try again')
            x, y = await self.rvsi_move(ctx, b, w, pr, ppt)
            await fmterr.delete()
            return x, y
        if int(x) not in (st := set(range(1, 9))) or int(y) not in st:
            await msg.delete()
            rgerr = await ctx.send('off board range. try again')
            x, y = await self.rvsi_move(ctx, b, w, pr, ppt)
            await rgerr.delete()
            return x, y
        await msg.delete()
        return x, y

    @commands.command(name='go', aliases=['weiqi'])
    async def weiqi(
        self,
        ctx: commands.Context,
        opponent: discord.guild.Member,
        length: int = 30,
        size: int = 19,
    ):
        """play weiqi with another user. usage: `weiqi member [length] [boardsize]"""
        if await self.wait_confirm(ctx, opponent, ctx.invoked_with):
            if length not in range(3, 91):
                length = 20
            endtime = time() + length * 60
            if size not in range(10, 21):
                size = 19
            black: discord.Member
            white: discord.Member
            if randint(0, 1):
                black, white = ctx.message.author, opponent
            else:
                black, white = opponent, ctx.message.author
            bd = await self.bot.run_in_tpexec(lambda: weiqi.Board(size))
            bd_ebd = discord.Embed(description=await bd.as_string())
            msg_with_ebd = await ctx.send(
                f'```ansi\n\u001b[0m\u001b[1;33mTime limit: {length} minutes!\n\u001b[1;45;1;30mBlack: {black.display_name}, \u001b[1;45;1;37mWhite: {white.display_name}```',
                embed=bd_ebd,
            )
            prompt = await ctx.send(f"{black.mention} Black's turn! (send coordinates)")
            turn = white
            for n in range(600):
                if time() >= endtime:
                    winner, ratio = await bd.all_counts()
                    if winner != 'Draw':
                        wnr = black if winner == "Black" else white
                        prompt = await prompt.edit(
                            content=f"```ansi\n\u001b[1;45;1;{30 if winner == 'Black' else 37}m"
                            f"Time's up! winner is {winner}, {wnr.display_name} "
                            f'with {ratio} stones!```'
                        )
                        await self.done_playing(
                            'weiqi', wnr, black if wnr is white else white
                        )
                    else:
                        prompt = await prompt.edit(content=f'Draw! - {ratio}')
                        await self.done_playing('weiqi', black, white, tie=True)
                    return
                if turn is black:
                    turn = white
                    prompt = await prompt.edit(
                        content=f"{white.mention} White's turn! (send coordinates)"
                    )
                else:
                    turn = black
                    prompt = await prompt.edit(
                        content=f"{black.mention} Black's turn! (send coordinates)"
                    )
                res = await self.wq_move(ctx, black, white, turn, prompt)
                if not res:
                    await self.done_playing(
                        'weiqi', black if turn is white else white, turn
                    )
                    return
                if res == (None,):
                    winner, ratio = await bd.all_counts()
                    if winner != 'Draw':
                        prompt = await prompt.edit(
                            content=f"```ansi\n\u001b[1;45;1;{30 if winner == 'Black' else 37}m"
                            f"Game ended! winner is {winner}, "
                            f'{black.display_name if winner == "Black" else white.display_name} '
                            f'with {ratio} stones!```'
                        )
                    else:
                        prompt = await prompt.edit(content=f'Draw! - {ratio}')
                    await self.done_playing('weiqi', black, white, tie=True)
                    return
                while not await bd.assign(
                    res[0], res[1], 'B' if turn is black else 'W'
                ):
                    errm = await ctx.send('not a valid spot! try again')
                    res = await self.wq_move(ctx, black, white, turn, prompt)
                    await errm.delete()
                bd_ebd = discord.Embed(description=await bd.as_string())
                msg_with_ebd = await msg_with_ebd.edit(embed=bd_ebd)
            winner, ratio = await bd.all_counts()
            if winner != 'Draw':
                wnr = black if winner == "Black" else white
                prompt = await prompt.edit(
                    content=f"```ansi\n\u001b[1;45;1;{30 if winner == 'Black' else 37}m"
                    f"Game ended! winner is {winner}, {wnr.display_name} "
                    f'with {ratio} stones!```'
                )
                await self.done_playing('weiqi', wnr, black if wnr is white else white)
                return
            else:
                prompt = await prompt.edit(content=f'Draw! - {ratio}')
                await self.done_playing('weiqi', black, white, tie=True)
                return

    async def wq_move(
        self,
        ctx: commands.Context,
        b: discord.Member,
        w: discord.Member,
        pr: discord.Member,
        ppt: discord.Message,
    ) -> tuple:
        def chkr(m):
            return m.author == pr and m.channel == ctx.channel

        def chkr2(m):
            return m.author == (b if pr is w else w) and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', check=chkr, timeout=80)
        except asyncio.TimeoutError:
            ppt = await ppt.edit(content=f'{pr.mention} hurry up!')
            try:
                msg = await self.bot.wait_for('message', check=chkr, timeout=120)
            except asyncio.TimeoutError:
                ppt = await ppt.edit(
                    content=f'game ended. {b.display_name if pr is w else w.display_name} '
                    f'is winner, because {pr.display_name} took too long to make a move!'
                )
                return ()
            return x, y
        if msg.content.lower() == 'end':
            ppt = await ppt.edit(
                content=f'{b.mention if pr is w else w.mention} {pr.display_name} '
                'wants to end the game now! if you agree, respond with yes, else say no.'
            )
            try:
                resp = await self.bot.wait_for('message', check=chkr2, timeout=80)
                if resp.content.lower() in {'end', 'yes', 'y', 'ok', 'ye'}:
                    await resp.delete()
                    await msg.delete()
                    return (None,)
            except asyncio.TimeoutError:
                pass
            await msg.delete()
            ppt = await ppt.edit(
                content=f'{pr.mention} your opponent has decided to continue! '
                '(now send coordinates)'
            )
            return await self.wq_move(ctx, b, w, pr, ppt)
        try:
            x, y = re.search(r'(?P<x>\d\d?)[(), ]*(?P<y>\d\d?)', msg.content).groups()
        except AttributeError:
            await msg.delete()
            fmterr = await ctx.send('must have x and y positions. try again')
            x, y = await self.wq_move(ctx, b, w, pr, ppt)
            await fmterr.delete()
            return x, y
        if not x or not y:
            await msg.delete()
            fmterr = await ctx.send('must have x and y positions. try again')
            x, y = await self.wq_move(ctx, b, w, pr, ppt)
            await fmterr.delete()
            return x, y
        if int(x) not in (st := set(range(1, 20))) or int(y) not in st:
            await msg.delete()
            rgerr = await ctx.send('off board range. try again')
            x, y = await self.wq_move(ctx, b, w, pr, ppt)
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
            return 0
        if opp == octx.author:
            await octx.send('you cannot challenge yourself.')
            return 0
        if opp == self.bot.user:
            await octx.send('no.')
            return 0
        self.ingame.append(octx.author)
        inv = await octx.send(
            f'{octx.message.author.display_name} has challenged {opp.display_name} '
            f'to a match of {game.title()}! {opp.mention}, do you accept? '
            '(react with :white_check_mark: or :negative_squared_cross_mark:)'
        )
        await inv.add_reaction('✅')
        await inv.add_reaction('❎')

        def chk(r, u):
            return u == opp and str(r.emoji) in '✅❎'

        reaction = ''
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
            status = 'ignored'
        if reaction:
            if str(reaction.emoji) == '❎':
                await inv.reply(f'{opp.display_name} did not accept the challenge.')
                self.ingame.remove(octx.author)
                status = 'rejected'
            elif str(reaction.emoji) == '✅':
                await inv.reply(f'{opp.display_name} has accepted the challenge!')
                self.ingame.append(opp)
                status = 'accepted'
        now = datetime.now().strftime("%m/%d, %H:%M:%S")
        if game == 'go':
            game = 'weiqi'
        elif game == 'othello':
            game = 'reversi'
        async with aiofile.async_open('vsvs_files/game_log.txt', 'a') as gl:
            await gl.write(
                f'{now} | {octx.author.display_name}{game:>16} {opp.display_name:>17},{status:>18}\n'
            )
        if status in {'ignored', 'rejected'}:
            return 0
        return 1

    async def done_playing(
        self, game: str, p1: discord.Member, p2: discord.Member, tie=False
    ):
        self.ingame.remove(p1)
        self.ingame.remove(p2)
        await self.bot.database.set_games_winloss(p1.id, p2.id, game, tie)


async def setup(bot: commands.Bot):
    await bot.add_cog(GameFeatures(bot))
    print('LOADED games')

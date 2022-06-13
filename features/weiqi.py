from __future__ import annotations
import asyncio
from typing import Literal


class Square:
    def __init__(self, x, y) -> None:
        self.occ = 'N'
        self.x = x
        self.y = y
        self.up = self.down = self.right = self.left = None

    async def naybors(self) -> list[Square]:
        return [
            sq for sq in [self.up, self.down, self.right, self.left] if sq is not None
        ]

    async def liberty(self) -> tuple[bool, list[Square]]:
        """checks this square's liberty

        returns a list of [liberty: bool, group: set[Square]]. liberty is if
        the group has liberty. group is a set of all squares of the connected group.
        """
        group = set([self])
        return await self._liberty2(group), group

    async def _liberty2(self, gp: list) -> bool:
        # modifies gp
        if self.occ == 'N':
            return True
        for sq in await self.naybors():
            if sq.occ == 'N':
                return True
        for sq in await self.naybors():
            if sq.occ == self.occ and sq not in gp:
                gp.add(sq)
                if await sq._liberty2(gp):
                    return True
        return False

    async def empty_group(self) -> tuple[Literal['N', 'B', 'W'], set[Square]]:
        """gets a set of all neighboring squares if its occ is N"""
        emptygroup = set([self])
        surrounded = set(await self.naybors())
        await self._group2(emptygroup, surrounded)
        bcount = wcount = 0
        for sq in surrounded.copy():
            if sq.occ == 'B':
                bcount += 1
            elif sq.occ == 'W':
                wcount += 1
        if bcount and wcount:
            return 'N', emptygroup
        if bcount:
            return 'B', emptygroup
        if wcount:
            return 'W', emptygroup
        return 'N', emptygroup

    async def _group2(self, gp: set, sr: set) -> bool:
        # modifies gp and sr
        for sq in await self.naybors():
            if sq.occ == 'N' and sq not in gp:
                nbr = await sq.naybors()
                gp |= {sq}
                sr |= {*nbr}
                await sq._group2(gp, sr)

    def __str__(self) -> str:
        return self.occ

    def __repr__(self) -> str:
        return f'{self.occ}{self.x, self.y}'


class Board:
    def __init__(self, size=19) -> None:
        self.rows = [[Square(x, y) for x in range(size)] for y in range(size)]
        self.columns = [[r[n] for r in self.rows] for n in range(size)]
        self.unliberated = set()
        self.unlibnum = 0
        for k, rw in enumerate(self.rows):
            if k != 0:
                for n in range(size):
                    rw[n].down = self.rows[k - 1][n]
            if k != size - 1:
                for n in range(size):
                    rw[n].up = self.rows[k + 1][n]
        for k, cl in enumerate(self.columns):
            if k != 0:
                for n in range(size):
                    cl[n].left = self.columns[k - 1][n]
            if k != size - 1:
                for n in range(size):
                    cl[n].right = self.columns[k + 1][n]

    def __str__(self) -> str:
        fs = ''
        for rw in reversed(self.rows):
            fs = ''.join([fs, '\n', *[p.occ for p in rw]])
        return fs

    async def as_string(self) -> str:
        fs = ''
        nums = '⒈⒉⒊⒋⒌⒍⒎⒏⒐⒑⒒⒓⒔⒕⒖⒗⒘⒙⒚'
        for k, ln in enumerate(self.rows):
            lnstr = ''.join([p.occ for p in ln])
            fs = ''.join([f'{nums[k]:>3} {lnstr:>3}', '\n', fs])
        fs = fs.replace('N', '🟫').replace('B', '🌑').replace('W', '⚪')
        xaxis = '     ⒈ ⒉ ⒊ ⒋⒌ ⒍⒎ ⒏ ⒐⒑ ⒒ ⒓ ⒔⒕ ⒖ ⒗ ⒘⒙ ⒚'
        return f'''```{fs}{xaxis:>3}```'''

    async def all_liberties(self):
        checked = set()
        todie = set()
        if self.unlibnum == 3:
            self.unliberated.clear()
            self.unlibnum = 0
        for cl in self.columns:
            for sq in cl:
                if sq in checked:
                    continue
                lbt, gp = await sq.liberty()
                checked |= gp
                if not lbt:
                    self.unliberated |= gp
                    todie |= gp
        for s in todie:
            s.occ = 'N'
        self.unlibnum += 1

    async def all_emptygroups(self) -> tuple[int, int]:
        checked = set()
        bcaptgs = wcaptgs = 0
        for cl in self.columns:
            for sq in cl:
                if sq.occ != 'N' or sq in checked:
                    continue
                surround, group = await sq.empty_group()
                checked |= group
                if surround == 'B':
                    bcaptgs += len(group)
                elif surround == 'W':
                    wcaptgs += len(group)
        return bcaptgs, wcaptgs

    async def all_counts(self) -> tuple[Literal['Black', 'White', 'Draw'], str]:
        """get the number of occupied and surrounded groups both players have

        Returns a tuple consisting of [WinnerStr, Str[NumTOnum]]. Nums
        are the number of solid stones plus the number of empty squares the
        solid stones surround.
        """
        bnum = wnum = 0
        for cl in self.columns:
            for sq in cl:
                if sq.occ == 'B':
                    bnum += 1
                elif sq.occ == 'W':
                    wnum += 1
        bcapt, wcapt = await self.all_emptygroups()
        bnum += bcapt
        wnum += wcapt
        if bnum > wnum:
            return 'Black', f'{bnum} to {wnum}'
        if wnum > bnum:
            return 'White', f'{wnum} to {bnum}'
        return 'Draw', f'{bnum} to {wnum}'

    async def assign(self, x, y, clr) -> int:
        """place a square

        x, y are indexed from one, color must be 'B' or 'W'.
        Return 1 on success and 0 if the square is occupied or
        if it breaks the ko rule. Checks all liberties after aswell.
        """
        x, y = int(x) - 1, int(y) - 1
        if self.columns[x][y].occ != 'N':
            return 0
        if self.columns[x][y] in self.unliberated:
            return 0
        self.columns[x][y].occ = clr
        await self.all_liberties()
        return 1


async def main():
    bd = Board(10)


if __name__ == '__main__':
    asyncio.run(main())

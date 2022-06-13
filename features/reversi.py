import re
from itertools import chain

NUM10 = (
    '8\N{variation selector-16}\N{combining enclosing keycap}',
    '7\N{variation selector-16}\N{combining enclosing keycap}',
    '6\N{variation selector-16}\N{combining enclosing keycap}',
    '5\N{variation selector-16}\N{combining enclosing keycap}',
    '4\N{variation selector-16}\N{combining enclosing keycap}',
    '3\N{variation selector-16}\N{combining enclosing keycap}',
    '2\N{variation selector-16}\N{combining enclosing keycap}',
    '1\N{variation selector-16}\N{combining enclosing keycap}',
)


class Square:
    def __init__(self, x, y) -> None:
        self.occ = 'G'  # G
        self.xy = (x, y)

    def __str__(self) -> str:
        return self.occ

    def __repr__(self) -> str:
        return f'{self.xy}'


class Board:
    """a reversi board"""

    def __init__(self) -> None:
        self.rows = [[Square(x, y) for x in range(8)] for y in range(8)]
        # rows for printing
        self.columns = [[r[n] for r in self.rows] for n in range(8)]
        # columns for assigning
        self.columns[3][4].occ = 'W'
        self.columns[4][3].occ = 'W'
        self.columns[3][3].occ = 'B'
        self.columns[4][4].occ = 'B'
        self.rdiag = [
            [(0, 5)],
            [(0, 4)],
            [(0, 3)],
            [(0, 2)],
            [(0, 1)],
            [(0, 0)],
            [(1, 0)],
            [(2, 0)],
            [(3, 0)],
            [(4, 0)],
            [(5, 0)],
        ]
        self.ldiag = [
            [(0, 2)],
            [(0, 3)],
            [(0, 4)],
            [(0, 5)],
            [(0, 6)],
            [(0, 7)],
            [(1, 7)],
            [(2, 7)],
            [(3, 7)],
            [(4, 7)],
            [(5, 7)],
        ]
        for n in range(1, 8):
            for rl in self.rdiag:
                try:
                    rl.append(self.columns[rl[0][0] + n][rl[0][1] + n])
                except IndexError:
                    continue
            for ll in self.ldiag:
                try:
                    if ll[0][1] - n < 0:
                        continue
                    ll.append(self.columns[ll[0][0] + n][ll[0][1] - n])
                except IndexError:
                    continue
        for l in self.rdiag:
            l[0] = self.columns[l[0][0]][l[0][1]]
        for l in self.ldiag:
            l[0] = self.columns[l[0][0]][l[0][1]]

    async def as_string(self):
        """string representation of current board

        Returns a tuple of three strings of len (3, 3, 2) that combined
        is the entire board, emojis are replaced with :name: aswell
        """
        fs = ''
        for k, l in enumerate(reversed(self.rows)):
            fs = ''.join([fs, NUM10[k], ' ', *[str(s) for s in l], '\n'])
        fs = (
            fs.replace('G', ':green_square:')
            .replace('B', ':new_moon:')
            .replace('W', ':white_circle:')
        )
        fs = fs.splitlines(keepends=True)
        return (
            ''.join(fs[0:3]),
            ''.join(fs[3:6]),
            ''.join(fs[6:8]) + '🟦 ' + ''.join(reversed(NUM10)),
        )

    async def assign_square(self, x, y, clr) -> int:
        """place a square

        x, y are indexed from one, color must be 'B' or 'W'.
        Return 1 on success and 0 if the square does not meet requirements
        """
        x, y = int(x) - 1, int(y) - 1
        if self.columns[x][y].occ != 'G':
            return 0
        self.columns[x][y].occ = clr
        rd, ld = [], []
        for l in self.rdiag:
            if f'{x, y}' in str(l):
                rd = l
        for l in self.ldiag:
            if f'{x, y}' in str(l):
                ld = l
        hasthis, spans = [], []
        if span := await self.find_string(self.columns[x], clr):
            hasthis.append(self.columns[x])
            spans.append(span)
        if span := await self.find_string(self.rows[y], clr):
            hasthis.append(self.rows[y])
            spans.append(span)
        if span := await self.find_string(rd, clr):
            hasthis.append(rd)
            spans.append(span)
        if span := await self.find_string(ld, clr):
            hasthis.append(ld)
            spans.append(span)
        if not hasthis:
            self.columns[x][y].occ = 'G'
            return 0
        for k, l in enumerate(hasthis):
            for p in l[spans[k][0] + 1 : spans[k][1] - 1]:
                p.occ = clr
        return 1

    async def count_all(self):
        alloccs = [p.occ for p in chain.from_iterable(self.columns)]
        bcount = alloccs.count('B')
        wcount = alloccs.count('W')
        if bcount > wcount:
            return 'Black', f'{bcount} to {wcount}'
        if bcount < wcount:
            return 'White', f'{wcount} to {bcount}'
        return 'Draw', f'{bcount} to {wcount}'

    async def possible(self, color) -> bool:
        pat = re.compile(f'{color}{"W" if color == "B" else "B"}{{1,5}}G')
        pat2 = re.compile(f'G{"W" if color == "B" else "B"}{{1,5}}{color}')
        for l in self.rows + self.columns + self.rdiag + self.ldiag:
            if pat.search(ss := ''.join([p.occ for p in l])) or pat2.search(ss):
                return True
        return False

    @staticmethod
    async def find_string(lst: list, char) -> tuple:
        fs = ''.join([p.occ for p in lst])
        try:
            if char == 'B':
                return re.search(r'B[WB]+B', fs).span()  # greedy
            else:
                return re.search(r'W[BW]+W', fs).span()
        except AttributeError:
            return ()

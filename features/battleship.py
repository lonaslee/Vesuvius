from __future__ import annotations
from random import randint

NUM10 = (
    '🔟 ',
    '9\N{variation selector-16}\N{combining enclosing keycap} ',
    '8\N{variation selector-16}\N{combining enclosing keycap} ',
    '7\N{variation selector-16}\N{combining enclosing keycap} ',
    '6\N{variation selector-16}\N{combining enclosing keycap} ',
    '5\N{variation selector-16}\N{combining enclosing keycap} ',
    '4\N{variation selector-16}\N{combining enclosing keycap} ',
    '3\N{variation selector-16}\N{combining enclosing keycap} ',
    '2\N{variation selector-16}\N{combining enclosing keycap} ',
    '1\N{variation selector-16}\N{combining enclosing keycap} ',
)
CHARAJ = '\u200b'.join(
    [
        '🟦 ',
        '\U0001f1e6',
        '\U0001f1e7',
        '\U0001f1e8',
        '\U0001f1e9',
        '\U0001f1ea',
        '\U0001f1eb',
        '\U0001f1ec',
        '\U0001f1ed',
        '\U0001f1ee',
        '\U0001f1ef',
    ]
)


class Square:
    """square of board

    possible values:\n
    'N, 🌊': nothing, ocean
    'S, ⏹': ship
    'H, 💥': ship hit
    'M, 📌': miss
    """

    def __init__(self):
        self.occ = '🟦' if randint(0, 4) else '🌊'


class Board:
    def __init__(self) -> None:
        self._rows = [[Square() for x in range(10)] for y in range(10)]
        self._columns = [[r[n] for r in self._rows] for n in range(10)]
        for k, rw in enumerate(self._rows):
            if k != 0:
                for n in range(10):
                    rw[n].down = self._rows[k - 1][n]
            if k != 10 - 1:
                for n in range(10):
                    rw[n].up = self._rows[k + 1][n]
        for k, cl in enumerate(self._columns):
            if k != 0:
                for n in range(10):
                    cl[n].left = self._columns[k - 1][n]
            if k != 10 - 1:
                for n in range(10):
                    cl[n].right = self._columns[k + 1][n]

    @property
    def columns(self) -> list[str]:
        fs = []
        ls = [[p.occ for p in l] for l in reversed(self._columns)]
        for l in ls:
            fs.append(''.join(l))
        return fs

    @property
    def rows(self) -> list[str]:
        fs = []
        ls = [[p.occ for p in l] for l in reversed(self._rows)]
        for l in ls:
            fs.append(''.join(l))
        return fs

    def __str__(self) -> str:
        """for use during placing ships, all ships are visible"""
        fs = ''
        for k, rw in enumerate(self.rows):
            fs += NUM10[k] + rw + '\n'
        return fs + CHARAJ

    async def getsquare(self, x, y) -> Square | None:
        """return a Square object at (x, y), with indexing starting from one"""
        x, y = int(x) - 1, int(y) - 1
        if x > 9 or y > 9:
            return None
        if x < 0 or y < 0:
            return None
        return self._columns[x][y]

    async def hit_square(self, x: int, y: int):
        """change a square's occupier to the miss symbol and return the square"""
        sq = await self.getsquare(x, y)
        sq.occ = '📌'
        return sq

    async def already_placed(self, x: int, y: int):
        sq = await self.getsquare(x, y)
        if sq.occ not in {'🟦', '🌊'}:
            return True
        return False


class Ship:
    """base class of ship

    subclasses supply length for init. x and y have to be in board range,
    face has to be in 'nesw'
    """

    def __init__(self, length: int, bd: Board, x: int, y: int, face: str) -> None:
        self.length = length
        self.bd = bd
        self.head = (x, y)
        self.facing = face
        self.allsqs = []

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.head} {self.facing}>'

    async def generate_span(self) -> bool:
        """mark ship on board, based on type of ship, facing direction, and head point

        return True on success and False if out of range or overlaps another ship
        """
        hx, hy = self.head
        operdict = {
            'n': (lambda n, n2: n, lambda n, n2: n - n2),
            's': (lambda n, n2: n, lambda n, n2: n + n2),
            'e': (lambda n, n2: n - n2, lambda n, n2: n),
            'w': (lambda n, n2: n + n2, lambda n, n2: n),
        }
        xoper, yoper = operdict[self.facing]
        for n in range(self.length):
            sq = await self.bd.getsquare(xoper(hx, n), yoper(hy, n))
            if sq is None or sq.occ not in {'🟦', '🌊'}:
                for sh in self.allsqs:
                    sh.occ = '🟦'
                return False
            self.allsqs.append(sq)
        for sq in self.allsqs:
            sq.occ = '⬜'
        return True

    async def is_hit(self, sq: Square) -> bool:
        """check if a square on the board is one in the ship.

        call is_dead if this returns True
        """
        for sh in self.allsqs:
            if sh is sq:
                sh.occ = '💥'
                return True
        return False

    async def is_dead(self) -> bool:
        """checks if all of this ship's squares have been hit"""
        for sh in self.allsqs:
            if sh.occ != '💥':
                return False
        return True

    async def hide(self) -> None:
        for sh in self.allsqs:
            sh.occ = '🟦' if randint(0, 4) else '🌊'

    async def show(self) -> None:
        for sh in self.allsqs:
            if sh.occ in {'🟦', '🌊'}:
                sh.occ = '⬜'


class Carrier(Ship):
    def __init__(self, bd: Board, x: int, y: int, face: str) -> None:
        super().__init__(5, bd, x, y, face)


class Battleship(Ship):
    def __init__(self, bd: Board, x: int, y: int, face: str) -> None:
        super().__init__(4, bd, x, y, face)


class Cruiser(Ship):
    def __init__(self, bd: Board, x: int, y: int, face: str) -> None:
        super().__init__(3, bd, x, y, face)


class Submarine(Cruiser):
    ...


class Destroyer(Ship):
    def __init__(self, bd: Board, x: int, y: int, face: str) -> None:
        super().__init__(2, bd, x, y, face)


class BshError:
    def __init__(self) -> None:
        self.err = False
        self.errperson = None


class Player:
    def __init__(self, c: str, plyr):
        self.clrhx = (255, 0, 0) if c == 'red' else (51, 153, 255)
        self.color = 'Red' if c == 'red' else 'Blue'
        self.user = plyr
        self.dmchannel = None
        self.dmprompt = None
        self.board = Board()
        self.ships: list[Ship] = []

    async def pin_ship(self, x, y, face):
        """add the next ship to the board"""
        nextship = [Carrier, Battleship, Cruiser, Submarine, Destroyer]
        try:
            sh = nextship[len(self.ships)](self.board, x, y, face)
        except IndexError:
            return 2
        if not (await sh.generate_span()):
            return 1
        self.ships.append(sh)
        return 0

    async def all_ship_check(self, sq: Square):
        dead = None
        for k, sh in enumerate(self.ships):
            if await sh.is_hit(sq):
                if await sh.is_dead():
                    dead = k
                break
        else:
            return False
        if isinstance(dead, int):
            self.ships.pop(dead)
        return True

    async def all_ship_dead(self):
        if not len(self.ships):
            return True
        return False

    async def hide_all_ships(self) -> None:
        for ship in self.ships:
            await ship.hide()

    async def show_all_ships(self) -> None:
        for ship in self.ships:
            await ship.show()

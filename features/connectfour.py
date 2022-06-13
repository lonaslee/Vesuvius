from __future__ import annotations
from itertools import chain


class SQ:
    def __init__(self) -> None:
        self.color = 'N'  # N, R, Y; S, Q

    def __str__(self) -> str:
        return self.color


class C4Board:
    """a connect-four board"""

    def __init__(self) -> None:
        self.last_assigned = None
        self.allsqs = [SQ() for _ in range(42)]
        self.y_horizontal_rows = [self.allsqs[k - 7 : k] for k in range(7, 43, 7)]
        self.x_vertical_rows = [
            [l[n] for l in self.y_horizontal_rows] for n in range(7)
        ]
        self.rtilt_diagonals = [
            [(0, 2)],
            [(0, 1)],
            [(0, 0)],
            [(1, 0)],
            [(2, 0)],
            [(3, 0)],
        ]
        self.ltilt_diagonals = [
            [(0, 3)],
            [(0, 4)],
            [(0, 5)],
            [(1, 5)],
            [(2, 5)],
            [(3, 5)],
        ]
        for n in range(1, 4):  # TODO delete all this and use try except
            [
                l.append(self.x_vertical_rows[l[0][0] + n][l[0][1] + n])
                for l in self.rtilt_diagonals
            ]
            [
                l.append(self.x_vertical_rows[l[0][0] + n][l[0][1] - n])
                for l in self.ltilt_diagonals
            ]
        [
            l.append(self.x_vertical_rows[l[0][0] + 4][l[0][1] + 4])
            for l in self.rtilt_diagonals[1:5]
        ]
        [
            l.append(self.x_vertical_rows[l[0][0] + 4][l[0][1] - 4])
            for l in self.ltilt_diagonals[1:5]
        ]
        [
            l.append(self.x_vertical_rows[l[0][0] + 5][l[0][1] + 5])
            for l in self.rtilt_diagonals[2:4]
        ]
        [
            l.append(self.x_vertical_rows[l[0][0] + 5][l[0][1] - 5])
            for l in self.ltilt_diagonals[2:4]
        ]
        for l in self.rtilt_diagonals:
            l[0] = self.x_vertical_rows[l[0][0]][l[0][1]]
        for l in self.ltilt_diagonals:
            l[0] = self.x_vertical_rows[l[0][0]][l[0][1]]

    async def as_string(self) -> tuple[str, str]:
        """string representation of current board

        returns a tuple of two strings being the original string
        split in half, emojis are replaced with :name: aswell

        """
        fs1, fs2 = '', ''
        ls = [[str(p) for p in l] for l in reversed(self.y_horizontal_rows)]
        k = 1
        for l in ls:
            if k < 4:
                fs1 = ''.join(chain([fs1], ['\n'], l))
            else:
                fs2 = ''.join(chain([fs2], ['\n'], l))
            k += 1
        fs1 = (
            fs1.replace('S', ':red_square:')
            .replace('Q', ':yellow_square:')
            .replace('R', ':red_circle:')
            .replace('Y', ':yellow_circle:')
            .replace('N', ':black_circle:')
        )
        fs2 = (
            fs2.replace('S', ':red_square:')
            .replace('Q', ':yellow_square:')
            .replace('R', ':red_circle:')
            .replace('Y', ':yellow_circle:')
            .replace('N', ':black_circle:')
        )
        return fs1, fs2

    async def drop_square(self, r) -> None | str:
        sqs = [s for s in self.x_vertical_rows[int(r) - 1] if s.color == 'N']
        if not sqs:
            return 'column full'
        self.last_assigned = sqs[0].color = 'R' if self.last_assigned == 'Y' else 'Y'
        return await self.check_four()

    async def check_four(self) -> None | str:
        for lst in (
            self.x_vertical_rows,
            self.y_horizontal_rows,
            self.rtilt_diagonals,
            self.ltilt_diagonals,
        ):
            for k, cl in enumerate(await self.strs_in_list(lst)):
                if (p := cl.find('YYYY')) != -1:
                    for sq in lst[k * -1 - 1][p : p + 4]:
                        sq.color = 'Q'
                    return 'YW'
                if (p := cl.find('RRRR')) != -1:
                    for sq in lst[k * -1 - 1][p : p + 4]:
                        sq.color = 'S'
                    return 'RW'
        return 'None'

    @staticmethod
    async def strs_in_list(rw: list) -> list[str]:
        fs = []
        ls = [[str(p) for p in l] for l in reversed(rw)]
        for l in ls:
            fs.append(''.join(l))
        return fs

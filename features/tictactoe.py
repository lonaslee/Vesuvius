from __future__ import annotations


class Square:
    def __init__(self, x, y) -> None:
        self.x = x
        self.y = y
        self.occupier = '?'


class Board:
    def __init__(self) -> None:
        self.bd_list = []
        self.last_assigned = None
        for y in range(1, 4):
            rw = [Square(x, y) for x in range(1, 4)]
            self.bd_list.append(rw)

    async def as_string(self) -> str:
        strr = ''
        for rw in reversed(self.bd_list):
            rws = '  '.join([rw[0].occupier, rw[1].occupier, rw[2].occupier])
            strr = '\n'.join([strr, rws])
        return strr.replace('X', ':x:').replace('O', ':o:').replace('?', ':question:')

    async def assign_square(self, x, y):
        if self.bd_list[int(y) - 1][int(x) - 1].occupier == '?':
            self.last_assigned = self.bd_list[int(y) - 1][int(x) - 1].occupier = (
                'O' if self.last_assigned == 'X' else 'X'
            )
        else:
            return 'occupied'
        return await self.check_connects()

    async def check_connects(self):
        for yrow in self.bd_list:
            if (
                yrow[0].occupier != '?'
                and yrow[0].occupier == yrow[1].occupier
                and yrow[0].occupier == yrow[2].occupier
            ):
                return yrow[0].occupier
        for n in range(3):
            if (
                self.bd_list[0][n].occupier != '?'
                and self.bd_list[0][n].occupier == self.bd_list[1][n].occupier
                and self.bd_list[0][n].occupier == self.bd_list[2][n].occupier
            ):
                return self.bd_list[0][n].occupier
        if (
            self.bd_list[1][1].occupier != '?'
            and self.bd_list[1][1].occupier == self.bd_list[0][2].occupier
            and self.bd_list[1][1].occupier == self.bd_list[2][0].occupier
        ):
            return self.bd_list[1][1].occupier
        if (
            self.bd_list[1][1] != '?'
            and self.bd_list[1][1].occupier == self.bd_list[0][0].occupier
            and self.bd_list[1][1].occupier == self.bd_list[2][2].occupier
        ):
            return self.bd_list[1][1].occupier
        return None

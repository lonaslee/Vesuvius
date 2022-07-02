from __future__ import annotations

from math import sqrt, sin, cos, radians
from re import search, findall


class Point:
    def __init__(self, x: float, y: float, name: str = '') -> None:
        self.x = float(x)
        self.y = float(y)
        self.name = name

    def __str__(self) -> str:
        return f'{self.name}{round(self.x, 2), round(self.y, 2)}'

    def __bool__(self) -> bool:
        if self.x and self.y:
            return True
        else:
            return False


class Line:
    def __init__(
        self, a: Point, b: Point | None, d: float = None, m: float = None
    ) -> None:
        self.a = a
        self._b = b
        self._length = d
        self._slope = m

    @property
    def length(self) -> float:
        if self._length is None:
            x2, y2 = self.b.x - self.a.x, self.b.y - self.a.y
            self._length = sqrt(x2 * x2 + y2 * y2)
        return self._length

    @property
    def slope(self) -> float | str:
        if self._slope is None:
            if d := self.b.x - self.a.x == 0:
                self._slope = 'undef'
            else:
                self._slope = (self.b.y - self.a.y) / d
        return self._slope

    @property
    def b(self) -> Point | tuple:
        if not self._b:
            if self.slope == 'undef':
                self._b = (
                    Point(self.a.x + self.length, self.a.y),
                    Point(self.a.x - self.length, self.a.y),
                )
            elif self.slope == 0:
                self._b = (
                    Point(self.a.x, self.a.y + self.length),
                    Point(self.a.x, self.a.y - self.length),
                )
            else:
                xmove = self.length / sqrt(1 + self.slope * self.slope)
                ymove = self.slope * xmove
                self._b = (
                    Point(self.a.x + xmove, self.a.y + ymove),
                    Point(self.a.x - xmove, self.a.y - ymove),
                )
        return self._b

    @property
    def eq(self) -> Equation:
        if self.slope == 'undef':
            return Equation(f'x={self.a.x}')
        elif self.slope == 0:
            return Equation(f'y={self.a.y}')
        else:
            return Equation(
                f'y={self.slope}x+'
                f'{self.slope * self.a.x * -1 + self.a.y}'.replace('+-', '-')
            )


class Equation:
    def __init__(self, eq: str) -> None:
        self.eq = self.clean_eq(eq)
        self.rslope = 'undef' if 'x=' in self.eq else 0 if 'x' not in self.eq else None

    def __repr__(self) -> str:
        rep = f'{self.eq} -> {self.m} -> {self.rslope}'
        if not self.rslope:
            rep += f' -> {self.b}'
        return rep

    @staticmethod
    def clean_eq(eq: str):
        eq = eq.strip().lower().replace(' ', '').replace('=x', '=1.0x')
        if eq.endswith('x'):
            eq += '+0.0'
        return eq

    @property
    def m(self) -> float:
        if self.rslope is not None:
            return float(self.eq[2:])
        else:
            return float(self.eq[2 : self.eq.index('x')])

    @property
    def b(self) -> float:
        return float(self.eq[self.eq.index('x') + 1 :].lstrip('+'))

    def __eq__(self, other: Equation):
        x, y = float(), float()
        match other.rslope, self.rslope:
            case 'undef', 0:
                x, y = other.m, self.m
            case 'undef', _:
                x = other.m
                y = self.m * x + self.b
            case 0, 'undef':
                x, y = other.m, self.m
            case 0, _:
                y = other.m
                x = (y - self.b) / self.m
            case _, 'undef':
                x = self.m
                y = other.m * x + other.b
            case _, 0:
                y = self.m
                x = (y - other.b) / other.m
            case _, _:
                mval, bval = self.m - other.m, other.b - self.b
                x = bval / mval
                y = self.m * x + self.b
        return Point(x, y)


class AllPoints:
    def __init__(self, ap: list[tuple[float, float]]) -> None:
        self.allpoints = [Point(p[0], p[1]) for p in ap]

    @staticmethod
    def in_points() -> list[Point]:
        print('points: ')
        pl = []
        while nx := input('-> ').strip():
            pl.append(nx)
            print(nx)
        for key, str_p in enumerate(pl):
            m = search(r'(?P<n>[a-zA-Z])?[\s,]*?(?P<x>-?\d+)[\s,]*?(?P<y>-?\d+)', str_p)
            pl[key] = Point(
                m.group('x'), m.group('y'), m.group('n') if m.group('n') else ''
            )
        return pl

    def translate_all(self, shift: Point) -> None:
        for key, pt in enumerate(self.allpoints):
            self.allpoints[key].x, self.allpoints[key].y = (
                pt.x + shift.x,
                pt.y + shift.y,
            )

    def reflect_all(self, line_of_ref: Equation) -> None:
        refl_dict = {'undef': self.refl_undef, 0: self.refl_zero}
        functype = refl_dict.get(line_of_ref.rslope, self.refl_else)
        for pt in self.allpoints:
            functype(pt, line_of_ref)

    @staticmethod
    def refl_undef(pt, lor) -> None:
        shift = abs(pt.x - lor.m)  # If x is to the right of the
        if pt.x >= lor.m:          # line of ref, then shift has to be
            shift *= -1            # negative for the next point
        pt.x = lor.m + shift

    @staticmethod
    def refl_zero(pt, lor) -> None:
        shift = abs(pt.y - lor.m)
        if pt.y >= lor.m:
            shift *= -1
        pt.y = lor.m + shift

    @staticmethod
    def refl_else(pt, lor) -> None:
        perp_line = Line(pt, None, None, lor.m**-1 * -1).eq
        intersection = (perp_line == lor)
        len_from_point = Line(pt, intersection).length
        new_points = Line(intersection, None, len_from_point, perp_line.m).b
        if str(new_points[0]) == str(pt):
            pt.x, pt.y = new_points[1].x, new_points[1].y
        else:
            pt.x, pt.y = new_points[0].x, new_points[0].y

    def rotate_all(self, args: tuple[Point, float]) -> None:
        pt_of_rot, ang = args[0], args[1]
        for pt in self.allpoints:
            pt.x, pt.y = (
                pt_of_rot.x
                + ((pt.x - pt_of_rot.x) * cos(ang) - (pt.y - pt_of_rot.y) * sin(ang)),
                pt_of_rot.y
                + ((pt.x - pt_of_rot.x) * sin(ang) + (pt.y - pt_of_rot.y) * cos(ang)),
            )

    def dilate_all(self, args: tuple[Point, float]) -> None:
        point_of_dil, scale = args[0], args[1]
        for pt in self.allpoints:
            pt.x, pt.y = (
                point_of_dil.x + scale * (pt.x - point_of_dil.x),
                point_of_dil.y + scale * (pt.y - point_of_dil.y),
            )


class Inputs:
    def main(self, val):
        name_dict = {
            'T': 'translate_all',
            'r': 'reflect_all',
            'R': 'rotate_all',
            'D': 'dilate_all',
        }
        type_dict = {
            'T': (lambda x, y: Point(x, y)),
            'r': (lambda e: Equation(e)),
            'R': (lambda x, y, r: (Point(x, y), radians(int(r)))),
            'D': (lambda x, y, s: (Point(x, y), float(s))),
        }
        this_oper = str(val)
        if search(r'(?P<t>[TRrD]).*?[TRrD]', this_oper):
            match_list = findall(r'[TRrD]\([\d, y=x.+-]+?\)', this_oper)
            match_list.reverse()
            for t in match_list:
                func_args = self.rematch(t, t[0])
                return name_dict[t[0]], type_dict[t[0]](*func_args)
        else:
            func_args = self.rematch(this_oper[0], this_oper[1:])
            return name_dict[this_oper[0]], type_dict[this_oper[0]](*func_args)

    @staticmethod
    def in_val(t: str = '') -> str:
        msgs = {
            'T': ('translation: ',),
            'r': ('line of reflection: ',),
            'R': ('point of rotation: ', 'angle of rotation: '),
            'D': ('point of dilation: ', 'scale factor: '),
        }
        inp = ''
        for m in msgs.get(t, ('transformation: ',)):
            new = input(m).strip()
            inp = ' '.join([inp, new]).strip()
        return inp

    @staticmethod
    def rematch(m, s) -> tuple[str, ...]:
        match m:
            case 'T':
                mch = search(r'([\d.-]+)[, ]+([\d.-]+)', s).groups()
                print(mch)
            case 'r':
                mch = (search(r'[\dy=x.+-]+', s).group(),)
            case _:
                mch = search(r'([\d.-]+)[, ]+([\d.-]+)[, ]+([\d.-]+)', s).groups()
        return mch


def main(ap: list[tuple[float, float]]):
    n = AllPoints(ap)
    for p in n.allpoints:
        print(p)
    for func, args in Inputs().main():
        getattr(n, func)(args)
        for p in n.allpoints:
            print(p)


if __name__ == '__main__':
    main()

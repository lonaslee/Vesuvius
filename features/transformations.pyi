from __future__ import annotations
from math import sqrt, sin, cos, radians
from re import search, findall

class Point:
    def __init__(self, x: float, y: float, name: str = '') -> None: ...
    def __str__(self) -> str: ...
    def __bool__(self) -> bool: ...

class Line:
    def __init__(
        self, a: Point, b: Point | None, d: float = None, m: float = None
    ) -> None: ...
    @property
    def length(self) -> float: ...
    @property
    def slope(self) -> float | str: ...
    @property
    def b(self) -> Point | tuple: ...
    @property
    def eq(self) -> Equation: ...

class Equation:
    def __init__(self, eq: str) -> None: ...
    def __repr__(self) -> str: ...
    @staticmethod
    def clean_eq(eq: str) -> str: ...
    @property
    def m(self) -> float: ...
    @property
    def b(self) -> float: ...
    def __eq__(self, other: Equation) -> Point: ...

class AllPoints:
    def __init__(self, ap: list[tuple[float, float]]) -> None: ...
    @staticmethod
    def in_points() -> list[Point]: ...
    def translate_all(self, shift: Point) -> None: ...
    def reflect_all(self, line_of_ref: Equation) -> None: ...
    @staticmethod
    def refl_undef(pt, lor) -> None: ...
    @staticmethod
    def refl_zero(pt, lor) -> None: ...
    @staticmethod
    def refl_else(pt, lor) -> None: ...
    def rotate_all(self, args: tuple[Point, float]) -> None: ...
    def dilate_all(self, args: tuple[Point, float]) -> None: ...

class Inputs:
    def main(self, val) -> tuple: ...
    @staticmethod
    def in_val(t: str = '') -> str: ...
    @staticmethod
    def rematch(m, s) -> tuple[str, ...]: ...
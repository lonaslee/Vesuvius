import re
from itertools import chain

NUM10: tuple[str]

class Square:
    def __init__(self, x, y) -> None: ...
    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...

class Board:
    """a reversi board"""

    def __init__(self) -> None: ...
    async def as_string(self) -> tuple[str, str, str]:
        """string representation of current board

        Returns a tuple of three strings of len (3, 3, 2) that combined
        is the entire board, emojis are replaced with :name: aswell
        """
        ...
    async def assign_square(self, x, y, clr) -> int:
        """place a square

        x, y are indexed from one, color must be 'B' or 'W'.
        Return 1 on success and 0 if the square does not meet requirements
        """
        ...
    async def count_all(self) -> tuple[str, str]: ...
    async def possible(self, color) -> bool: ...
    @staticmethod
    async def find_string(lst: list, char) -> tuple: ...

from __future__ import annotations

import datetime
from itertools import zip_longest
from typing import Any, Callable, Sequence, cast

import aiosqlite
import config
import discord

__all__ = (
    'NUM_EMOTES',
    'CHAR_EMOTES',
    'owner_bypass',
    'justice',
    'horizontal_join',
    'tzi',
    'Database',
    'ANSIColors',
)

NUM_EMOTES = (
    '1\N{variation selector-16}\N{combining enclosing keycap}',
    '2\N{variation selector-16}\N{combining enclosing keycap}',
    '3\N{variation selector-16}\N{combining enclosing keycap}',
    '4\N{variation selector-16}\N{combining enclosing keycap}',
    '5\N{variation selector-16}\N{combining enclosing keycap}',
    '6\N{variation selector-16}\N{combining enclosing keycap}',
    '7\N{variation selector-16}\N{combining enclosing keycap}',
    '8\N{variation selector-16}\N{combining enclosing keycap}',
    '9\N{variation selector-16}\N{combining enclosing keycap}',
    '\U0001f51f',
)

CHAR_EMOTES = (
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
    '\U0001f1f0',
    '\U0001f1f1',
    '\U0001f1f2',
    '\U0001f1f3',
    '\U0001f1f4',
    '\U0001f1f5',
    '\U0001f1f6',
    '\U0001f1f7',
    '\U0001f1f8',
    '\U0001f1f9',
    '\U0001f1fa',
    '\U0001f1fb',
    '\U0001f1fc',
    '\U0001f1fd',
    '\U0001f1fe',
    '\U0001f1ff',
)


def owner_bypass(time: int):
    """return a function that returns a Cooldown of time length, except for the owner"""

    def cooldown_func(
        message: discord.Message | discord.Interaction,
    ) -> discord.app_commands.Cooldown | None:
        if (
            isinstance(message, discord.Message)
            and message.author.id == config.owner_id
        ):
            return None
        if (
            isinstance(message, discord.Interaction)
            and message.user.id == config.owner_id
        ):
            return None
        return discord.app_commands.Cooldown(1, time)

    return cooldown_func


def justice(
    *args: Sequence[Any],
    fillchar: str = ' ',
    ljust_fn: Callable[[str, int, str], str] = lambda s, w, f: s.ljust(w, f),
    cjust_fn: Callable[[str, int, str], str] = lambda s, w, f: s.center(w, f),
    rjust_fn: Callable[[str, int, str], str] = lambda s, w, f: s.rjust(w, f),
) -> tuple[tuple[str, ...], ...]:
    """Justify elements of multiple iterables in relation to eachother.

    For each index of the iterables, the elements are casted to string and padded using string
    justifying methods with fillchar to the length of the longest of the elements of that index.
    """
    ls = tuple(tuple(str(e) for e in seq) for seq in args)
    max_lens = [0 for _ in range(len(ls[0]))]
    for l in ls:
        for k, v in enumerate(l):
            if len(v) > max_lens[k]:
                max_lens[k] = len(v)
    return tuple(
        (
            ljust_fn(t[0], max_lens[0], fillchar),
            *(cjust_fn(m, max_lens[n + 1], fillchar) for n, m in enumerate(t[1:-1])),
            rjust_fn(t[-1], max_lens[-1], fillchar),
        )
        for t in ls
    )


def horizontal_join(
    *args: str, sep: str = ' ', fillval: str = ' ', fillchar: str = ' '
) -> str:
    """Make multiple multiline strings into one string."""
    return '\n'.join(
        sep.join(lines)
        for lines in justice(
            *zip_longest(*(s.splitlines() for s in args), fillvalue=fillval),
            fillchar=fillchar,
            cjust_fn=(lambda s, w, f: s.ljust(w, f)),
            rjust_fn=(lambda s, w, f: s.ljust(w, f)),
        )
    )


class _TimeZoneInfo(datetime.tzinfo):
    def utcoffset(self, __dt: datetime.datetime | None):
        return datetime.timedelta(hours=-5)

    def dst(self, __dt: datetime.datetime | None):
        return datetime.timedelta(
            0
        )  # FIXME timezone, or wait until the last cycle of daylight

    def tzname(self, __dt: datetime.datetime | None) -> str | None:
        return 'central time'


tzi = _TimeZoneInfo()


class Database:
    def __init__(self, con: aiosqlite.Connection, csr: aiosqlite.Cursor) -> None:
        self.connection = con
        self.cursor = csr

    def __str__(self) -> str:
        return f'{self.connection} {self.cursor}'

    async def set_games_winloss(
        self, winner_id: int, loser_id: int, game: str, tie: bool = False
    ):
        indexdict = {
            'tictactoe': [1, 2, 3],
            'connectfour': [4, 5, 6],
            'reversi': [7, 8, 9],
            'weiqi': [10, 11, 12],
            'battleship': [13, 14],
        }
        game_rows = indexdict[game]
        await self.cursor.execute(
            'INSERT INTO userwins VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(user_id) DO NOTHING',
            (winner_id, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        )
        await self.cursor.execute(
            'INSERT INTO userwins VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(user_id) DO NOTHING',
            (loser_id, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        )
        winnerpast = await self.get_user_winloss(winner_id)
        loserpast = await self.get_user_winloss(loser_id)
        if not tie:
            await self.cursor.execute(
                f'UPDATE userwins SET {game}_wins=? WHERE user_id=?',
                (winnerpast[game_rows[0]] + 1, winner_id),
            )
            await self.cursor.execute(
                f'UPDATE userwins SET {game}_loss=? WHERE user_id=?',
                (loserpast[game_rows[1]] + 1, loser_id),
            )
            await self.connection.commit()
        else:
            await self.cursor.execute(
                f'UPDATE userwins SET {game}_ties=? WHERE user_id=?',
                (winnerpast[game_rows[2]] + 1, winner_id),
            )
            await self.cursor.execute(
                f'UPDATE userwins SET {game}_ties=? WHERE user_id=?',
                (loserpast[game_rows[2]] + 1, loser_id),
            )
            await self.connection.commit()

    async def get_games_winloss(self) -> list[tuple[int, ...]]:
        await self.cursor.execute('SELECT * FROM userwins')
        return cast(list[tuple[int, ...]], await self.cursor.fetchall())

    async def get_user_winloss(self, uid: int) -> tuple[int, ...]:
        await self.cursor.execute('SELECT * FROM userwins WHERE user_id=?', (uid,))
        return cast(tuple[int, ...], await self.cursor.fetchone())

    async def create_games_table(self):
        """create the table 'userwins'"""
        await self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS userwins (
            user_id integer PRIMARY KEY,
            tictactoe_wins integer,
            tictactoe_loss integer,
            tictactoe_ties integer,
            connectfour_wins integer,
            connectfour_loss integer,
            connectfour_ties integer,
            reversi_wins integer,
            reversi_loss integer,
            reversi_ties integer,
            weiqi_wins integer,
            weiqi_loss integer,
            weiqi_ties integer,
            battleship_wins integer,
            battleship_loss integer
            )'''
        )
        await self.connection.commit()

    async def get_wotd_yesterday(self) -> tuple[int, str]:
        await self.cursor.execute('SELECT * FROM wotd ORDER BY day DESC LIMIT 1')
        return cast(tuple[int, str], await self.cursor.fetchone())

    async def set_wotd_newday(self, word: str):
        yesterday = await self.get_wotd_yesterday()
        await self.cursor.execute(
            'INSERT INTO wotd VALUES (?, ?)', (yesterday[0] + 1, word)
        )
        await self.connection.commit()

    async def create_wotd_table(self):
        """create the table 'wotd' with day, word"""
        await self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS wotd (
            day integer PRIMARY KEY,
            word text
            )'''
        )
        await self.cursor.execute(
            'INSERT INTO wotd VALUES (?, ?) ON CONFLICT DO NOTHING', (0, 'amogus')
        )
        await self.connection.commit()

    async def create_channels_table(self):
        await self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS channels (
            guild integer PRIMARY KEY,
            option integer,
            general integer,
            announcements integer
            )'''
        )
        await self.connection.commit()

    async def get_channel(self, guild: int) -> tuple[int, int, int, int]:
        await self.cursor.execute('SELECT * FROM channels WHERE guild=?', (guild,))
        return cast(tuple[int, int, int, int], await self.cursor.fetchone())

    async def get_all_channels(self) -> list[tuple[int, int, int, int]]:
        await self.cursor.execute('SELECT * FROM channels')
        return cast(list[tuple[int, int, int, int]], await self.cursor.fetchall())

    async def all_general_channels(self) -> list[int]:
        await self.cursor.execute('SELECT * FROM channels')
        return [
            id
            for id in [
                row[2]
                for row in [guild_info for guild_info in await self.cursor.fetchall()]
            ]
        ]

    async def all_announcement_channels(self) -> list[int]:
        await self.cursor.execute('SELECT * FROM channels')
        return [
            id
            for id in [
                row[3]
                for row in [guild_info for guild_info in await self.cursor.fetchall()]
            ]
        ]

    async def set_channels(
        self, guild: int, option: int, general: int, announcements: int
    ) -> None:
        await self.cursor.execute(
            'INSERT OR REPLACE INTO channels VALUES (?, ?, ?, ?)',
            (guild, option, general, announcements),
        )


class ANSIColors:
    TEXT_COLORS = {
        '': '',
        'GRAY_': '30',
        'RED_': '31',
        'GREEN_': '32',
        'YELLOW_': '33',
        'BLUE_': '34',
        'PINK_': '35',
        'CYAN_': '36',
        'WHITE_': '37',
    }
    FORMATS = {'': '0', 'BOLD_': '1', 'UNDERLINE_': '4'}
    HIGHLIGHT_COLORS = {
        '': '',
        'H_DARK_BLUE': '40',
        'H_ORANGE': '41',
        'H_MARBLE_BLUE': '42',
        'H_GREY_TURQUOISE': '43',
        'H_GRAY': '44',
        'H_INDIGO': '45',
        'H_LIGHT_GRAY': '46',
        'H_WHITE': '47',
    }

    BEGIN = '```ansi\n'
    END = '```'
    B = '```ansi\n'
    E = '```'
    NOCLR = '\u001b[0m'

    @classmethod
    def generate_formats(cls):
        for color in cls.TEXT_COLORS:
            for highlight in cls.HIGHLIGHT_COLORS:
                for format in cls.FORMATS:
                    for format2 in cls.FORMATS:
                        attr_name = f'{format}{format2}{color}{highlight}'.removesuffix(
                            '_'
                        )
                        attr_val = (
                            f'\u001b[0m\u001b['
                            f'{cls.FORMATS[format]};'
                            f'{cls.FORMATS[format2]};'
                            f'{cls.TEXT_COLORS[color]};'
                            f'{cls.HIGHLIGHT_COLORS[highlight]}'.removesuffix(';') + 'm'
                        )
                        if hasattr(cls, attr_name):
                            continue
                        if attr_name == '0':
                            continue
                        if format == format2 and format != '':
                            continue
                        if format == 'UNDERLINE_' and format2 == 'BOLD_':
                            continue
                        setattr(cls, attr_name, attr_val)

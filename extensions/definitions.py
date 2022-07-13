from __future__ import annotations

import datetime

import aiosqlite
import discord
from typing import cast

import config


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
    '🔟',
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


# fmt: off
holidays = {
    (1, 1): ("New Year's Day", 'FF3333', 'https://upload.wikimedia.org/wikipedia/commons/e/eb/Mexico_City_New_Years_2013%21_%288333128248%29.jpg'),
    (1, 22): ("Chinese New Year", 'FF0000', 'https://upload.wikimedia.org/wikipedia/commons/d/d1/Kung_Hei_Fat_Choi%21_%286834861529%29.jpg'),  # c
    (2, 2): ("Groundhog Day (Holiday)", '784212', 'https://upload.wikimedia.org/wikipedia/commons/e/ee/Groundhog-Standing2.jpg'),
    (2, 14): ("Valentine's Day", 'FF6BF4', 'https://upload.wikimedia.org/wikipedia/commons/1/11/Persian_Valentine%27s_Day_Karaji_%2850957801252%29_-_Edited.jpg'),
    (3, 1): ("Saint Patrick's Day", '2ECC71', 'https://upload.wikimedia.org/wikipedia/commons/0/0c/Irish_clover.jpg'),
    (3, 8): ("Holi (Holiday)", 'FF6E33', 'https://upload.wikimedia.org/wikipedia/commons/b/bd/Holi_shop.jpg'),  # c
    (3, 22): ("Ramadan", '85C1E9', 'https://upload.wikimedia.org/wikipedia/commons/0/00/%D9%87%D9%84%D8%A7%D9%84_%D8%B1%D9%85%D8%B6%D8%A7%D9%86.jpg'),  # c
    (3, 29): ("Memorial Day (Holiday):", '2980B9', 'https://upload.wikimedia.org/wikipedia/commons/e/e3/Graves_at_Arlington_on_Memorial_Day.JPG'),
    (4, 5): ("Passover (Holiday)", 'D7FF33', 'https://upload.wikimedia.org/wikipedia/commons/b/b4/Israel%27s_Escape_from_Egypt.jpg'),  # c
    (4, 9): ("Easter (Holiday) (Easter)", 'E3A6E9', 'https://upload.wikimedia.org/wikipedia/commons/1/10/Easter_eggs_-_straw_decoration.jpg'),  # c
    (4, 21): ("Eid al-Fitr", '3D884E', 'https://upload.wikimedia.org/wikipedia/commons/8/81/1984_%22Fetr_Feast%22_stamp_of_Iran.jpg'),  # c
    (4, 22): ("Earth Day (Holiday) (Earth)", '248727', 'https://upload.wikimedia.org/wikipedia/commons/4/41/Earth_Day_Flag.jpg'),
    (5, 5): ("Cinco de Mayo (Holiday)", 'D9E5DC', 'https://upload.wikimedia.org/wikipedia/commons/c/c0/Batalla_de_Puebla.png'),
    (5, 14): ("Mother's Day (mother)", 'EC7063', 'https://upload.wikimedia.org/wikipedia/commons/1/1f/Northern_Pacific_Railway_Mother%27s_Day_postcard_1916.JPG'),  # c
    (6, 14): ("Flag Day (United States)", '3498DB', 'https://upload.wikimedia.org/wikipedia/en/a/a4/Flag_of_the_United_States.svg'),
    (6, 18): ("Father's Day (Holiday)", '2980B9', 'https://upload.wikimedia.org/wikipedia/commons/7/79/BritaAndI_Selfportrait.jpg'),
    (7, 4): ("Fourth of July (Holiday)", 'E74C3C', 'https://upload.wikimedia.org/wikipedia/commons/6/68/Fourth_of_July_fireworks_behind_the_Washington_Monument%2C_1986.jpg'),
    (7, 9): ("Eid al-Adha", 'E9E74C', 'https://upload.wikimedia.org/wikipedia/commons/d/de/The_Badshahi_in_all_its_glory_during_the_Eid_Prayers.JPG'),  # c
    (9, 4): ("Labor Day (Holiday)", '154360', 'https://upload.wikimedia.org/wikipedia/commons/9/90/Labor_Day_parade_on_Pennsylvania_Avenue%2C_Washington%2C_D.C._LCCN2017645684.jpg'),  # c
    (10, 4): ("Yom Kippur", 'FDFEFE', 'https://upload.wikimedia.org/wikipedia/commons/1/1e/Maurycy_Gottlieb_-_Jews_Praying_in_the_Synagogue_on_Yom_Kippur.jpg'),  # c
    (10, 12): ("Columbus Day (Holiday)", '85C1E9', 'https://upload.wikimedia.org/wikipedia/commons/d/d5/Desembarco_de_Col%C3%B3n_de_Di%C3%B3scoro_Puebla.jpg'),
    (10, 24): ("Diwali (Holiday)", 'BA0BAA', 'https://upload.wikimedia.org/wikipedia/commons/2/2f/Fireworks_Diwali_Chennai_India_November_2013_b.jpg'),  # c
    (10, 30): ("Halloween", 'DC7633', 'https://upload.wikimedia.org/wikipedia/commons/a/a2/Jack-o%27-Lantern_2003-10-31.jpg'),
    (11, 1): ("Day of the Dead (Holiday)", 'FF91ED', 'https://upload.wikimedia.org/wikipedia/commons/6/68/Catrina_3.jpg'),
    (11, 11): ("Armistice Day", 'E74C3C', 'https://upload.wikimedia.org/wikipedia/commons/2/26/Veterans_Day_poster_2018.jpg'),
    (11, 23): ("Thanksgiving (United States)", 'CA6F1E', 'https://upload.wikimedia.org/wikipedia/commons/9/98/Thanksgiving-Brownscombe.jpg'),  # c
    (12, 3): ("Advent", '8E44AD', 'https://upload.wikimedia.org/wikipedia/commons/5/58/Adventwreath.jpg'),  # c
    (12, 5): ("Saint Nicholas Day", 'FF0000', 'https://upload.wikimedia.org/wikipedia/commons/7/7d/Sinterklaas_2007.jpg'),
    (12, 7): ("Hanukkah", '85C1E9', 'https://upload.wikimedia.org/wikipedia/commons/8/86/Hanukkah_%D7%97%D7%92_%D7%97%D7%A0%D7%95%D7%9B%D7%94.jpg'),
    (12, 24): ("Christmas Eve (Holiday) (Eve)", '27AE60', 'https://upload.wikimedia.org/wikipedia/commons/6/62/Gifts_xmas.jpg'),
    (12, 25): ("Christmas Day", '2ECC71', 'https://upload.wikimedia.org/wikipedia/commons/8/8f/NativityChristmasLights2.jpg'),
    (12, 31): ("New Year's Eve", 'E74C3C', 'https://upload.wikimedia.org/wikipedia/commons/c/c9/MALAM_TAHUN_BARU_%285309956791%29.jpg'),
    (7, 6): ("New Year's Eve", 'E74C3C', 'https://upload.wikimedia.org/wikipedia/commons/c/c9/MALAM_TAHUN_BARU_%285309956791%29.jpg'),
}
# fmt: on

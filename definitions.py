from __future__ import annotations

import discord
import aiosqlite

import config


class InteractionContextAdapter:
    def __init__(self, interaction: discord.Interaction) -> None:
        self.author = interaction.user
        self.channel = interaction.channel
        self.isend = interaction.response.send_message
        self._calltimes = 0

    async def send(self, message):
        if self._calltimes:
            await self.channel.send(message)
        else:
            await self.isend(message)
            self._calltimes = 1


def owner_bypass(time: int) -> function:
    """return a function that returns a Cooldown of time length, except for the owner"""

    def cooldown_func(
        message: discord.Message | discord.Interaction,
    ) -> discord.app_commands.Cooldown:
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


class Database:
    def __init__(self, con: aiosqlite.Connection, csr: aiosqlite.Cursor) -> None:
        self.connection = con
        self.cursor = csr

    def __str__(self) -> str:
        return f'{self.connection}, {self.cursor}'

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

    async def get_games_winloss(self):
        await self.cursor.execute('SELECT * FROM userwins')
        return await self.cursor.fetchall()

    async def get_user_winloss(self, uid: int):
        await self.cursor.execute('SELECT * FROM userwins WHERE user_id=?', (uid,))
        return await self.cursor.fetchone()

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
        return await self.cursor.fetchone()

    async def set_wotd_newday(self, word):
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
                        if (format == format2) and format != '':
                            continue
                        setattr(cls, attr_name, attr_val)


ANSIColors.generate_formats()

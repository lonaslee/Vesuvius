from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import aiosqlite
import discord
from discord.ext import commands

import config
from extensions import definitions


async def main():
    bot = Bot()
    async with bot:
        await bot.start(config.token)


class Bot(commands.Bot):
    def __init__(self) -> None:
        bot_intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or('`'),
            help_command=None,
            intents=bot_intents,
            status=discord.Status.dnd,
            activity=discord.Game('among us'),
        )

        self.start_time: datetime = None
        self.files = config.files_dict.copy()

        self.database: definitions.Database = None
        self._db_cursor: aiosqlite.Cursor = None
        self._db_connnection: aiosqlite.Connection = None
        self._tpexecutor = ThreadPoolExecutor(1)

    async def run_in_tpexec(self, func):
        return await asyncio.get_event_loop().run_in_executor(self._tpexecutor, func)

    async def setup_hook(self) -> None:
        await super().setup_hook()
        await self.load_extension('commands')
        await self.load_extension('events')
        await self.load_extension('features')
        await self.load_extension('games')
        await self.load_extension('testing')

    async def start(self, *args, **kwargs):
        async with aiosqlite.connect(self.files['database']) as conn:
            self._db_connnection = conn
            self._db_cursor = await self._db_connnection.cursor()
            self.database = definitions.Database(self._db_connnection, self._db_cursor)
            await self.database.create_games_table()
            await self.database.create_wotd_table()
            print("DATABASE connected with", self.database)
            await super().start(*args, **kwargs)

    async def on_ready(self):
        if not self.start_time:
            self.start_time = datetime.now()
        print(f'LOGGED ON: as {self.user}')
        print(f'AT: {datetime.now().strftime("%m/%d/%y, %H:%M:%S")}')
        print('IN GUILDS:', ', '.join([g.name for g in self.guilds]))

    async def on_guild_join(self, guild):
        print(f'ADDED to guild {guild.name}')


if __name__ == '__main__':
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(
        filename=config.files_dict['discord_log'].as_posix(), encoding='utf-8', mode='w'
    )
    handler.setFormatter(
        logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
    )
    logger.addHandler(handler)

    asyncio.run(main())

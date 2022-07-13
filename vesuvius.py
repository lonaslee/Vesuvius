from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable, Literal, TypeVar

import aiosqlite
import discord
from discord.ext import commands

import config
from extensions.definitions import Database


async def main():
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(
        filename=config.files_dict['discord_log'].as_posix(), encoding='utf-8', mode='w'
    )
    handler.setFormatter(
        logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
    )
    logger.addHandler(handler)

    async with Vesuvius(logger) as bot:
        await bot.start(config.token)


class Vesuvius(commands.Bot):
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        bot_intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or('`'),
            help_command=None,
            intents=bot_intents,
            status=discord.Status.online,
            activity=discord.Streaming(
                name='among us', url='https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            ),
        )

        self.start_time = datetime.now()
        self.files = config.files_dict.copy()
        self.last_reload: Literal[
            'all', 'commands', 'events', 'features', 'games', 'testing'
        ] = 'all'

        self.database: Database = None  # type: ignore
        self._tpexecutor: ThreadPoolExecutor = ThreadPoolExecutor(1)

    R = TypeVar('R')

    async def run_in_tpexec(self, func: Callable[..., R], *args: Any) -> R:
        return await self.loop.run_in_executor(self._tpexecutor, func, *args)

    async def setup_hook(self) -> None:
        await super().setup_hook()
        await self.load_extension('commands')
        await self.load_extension('events')
        await self.load_extension('features')
        await self.load_extension('games')
        await self.load_extension('testing')

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        async with aiosqlite.connect(self.files['database']) as conn:
            self.database = Database(conn, await conn.cursor())
            await self.database.create_channels_table()
            print("DATABASE connected with", self.database)
            await super().start(token, reconnect=reconnect)

    async def on_ready(self) -> None:
        print(f'LOGGED ON: as {self.user}')
        print(f'AT: {datetime.now().strftime("%m/%d/%y, %H:%M:%S")}')
        print('IN GUILDS:', ', '.join([g.name for g in self.guilds]))

    async def on_guild_join(self, guild: discord.Guild) -> None:
        print(f'ADDED to guild {guild.name}')


if __name__ == '__main__':
    asyncio.run(main())

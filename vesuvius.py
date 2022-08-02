from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from functools import partial
from typing import Callable, Literal, ParamSpec, TypeVar

import aiosqlite
import discord
from discord.ext import commands

import config
from extensions.utils import Database


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

    async with Vesuvius(logger=logger) as bot:
        await bot.start(config.token)


class Vesuvius(commands.Bot):
    def __init__(self, *, logger: logging.Logger) -> None:
        self.logger = logger
        bot_intents = discord.Intents.default()
        bot_intents.message_content = True
        bot_intents.members = True
        super().__init__(
            command_prefix=commands.when_mentioned_or('`'),
            help_command=None,
            intents=bot_intents,
            status=config.status,
            activity=config.activity,
        )

        self.start_time = datetime.now()
        self.files = config.files_dict.copy()
        self.last_reload: Literal[
            'all', 'commands', 'events', 'features', 'games', 'testing'
        ] = 'all'

        self.database: Database = None  # type: ignore

    _P = ParamSpec('_P')
    _R = TypeVar('_R')

    async def run_in_tpexec(
        self, func: Callable[_P, _R], *args: _P.args, **kwargs: _P.kwargs
    ) -> _R:
        return await self.loop.run_in_executor(None, partial(func, *args, **kwargs))

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

    async def on_guild_remove(self, guild: discord.Guild):
        print(f'REMOVED from guild {guild.name}')


if __name__ == '__main__':
    asyncio.run(main())

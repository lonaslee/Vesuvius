import asyncio
import discord
import logging
import aiosqlite
import vsvs_config
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from discord.ext import commands


async def main():
    d = {}
    for c in (65, 97):
        for i in range(26):
            d[chr(i + c)] = chr((i + 13) % 26 + c)
    token = ''.join([d.get(c, c) for c in vsvs_config.tokenc])
    bot = Bot()
    async with bot:
        await bot.start(token)


class Bot(commands.Bot):
    def __init__(self) -> None:
        bot_intents = discord.Intents.all()
        super().__init__(command_prefix='`', help_command=None, intents=bot_intents)
        self.files = vsvs_config.files_dict.copy()
        self.timezoneinfo = vsvs_config.TZI()
        self.database = None
        self._db_cursor = None
        self._db_connnection = None
        self._tpexecutor = ThreadPoolExecutor(1)

    async def run_in_tpexec(self, func):
        return await asyncio.get_event_loop().run_in_executor(self._tpexecutor, func)

    async def setup_hook(self) -> None:
        await super().setup_hook()
        await self.load_extension('vsvs_commands')
        await self.load_extension('vsvs_events')
        await self.load_extension('vsvs_features')
        await self.load_extension('vsvs_games')
        await self.load_extension('vsvs_testing')

    async def start(self, *args, **kwargs):
        async with aiosqlite.connect(self.files['database']) as conn:
            self._db_connnection = conn
            self._db_cursor = await self._db_connnection.cursor()
            self.database = vsvs_config.Database(self._db_connnection, self._db_cursor)
            await self.database.create_games_table()
            await self.database.create_wotd_table()
            print("DATABASE connected with", self.database)
            await super().start(*args, **kwargs)

    async def on_ready(self):
        print(f'LOGGED ON: as {self.user}')
        print(f'AT: {datetime.now().strftime("%m/%d/%y, %H:%M:%S")}')
        print('IN GUILDS:', ', '.join([g.name for g in self.guilds]))

    async def on_guild_join(self, guild):
        print(f'ADDED to guild {guild.name}')


if __name__ == '__main__':
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(
        filename=vsvs_config.files_dict['discord_log'].as_posix(),
        encoding='utf-8',
        mode='w',
    )
    handler.setFormatter(
        logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
    )
    logger.addHandler(handler)

    asyncio.run(main())

import asyncio
import discord
import logging
import vsvs_config
from datetime import datetime
from discord.ext import commands


def main():
    logging.basicConfig(level=logging.WARNING)

    d = {}
    for c in (65, 97):
        for i in range(26):
            d[chr(i + c)] = chr((i + 13) % 26 + c)
    token = ''.join([d.get(c, c) for c in vsvs_config.token])

    bot_intents = discord.Intents.default()
    bot_intents.members = True

    bot = commands.Bot(command_prefix='`', intents=bot_intents, help_command=None)
    bot.load_extension('vsvs_commands')
    bot.load_extension('vsvs_events')
    bot.load_extension('vsvs_features')
    bot.load_extension('vsvs_testing')

    @bot.event
    async def on_ready():
        print(f'LOGGED ON: as {bot.user}')
        print(f'AT: {datetime.now().strftime("%m/%d/%y, %H:%M:%S")}')
        print('IN GUILDS:', ', '.join([g.name for g in bot.guilds]))

    bot.run(token)


if __name__ == '__main__':
    main()

import asyncio
import logging
import pathlib
import sys

import aiosqlite
import discord

import config
from bot import OliviaBot


match sys.argv:
    case [_, arg] if arg.lower() == "prod":
        prod = True
    case [_]:
        prod = False
    case _:
        relative = pathlib.Path(__file__).relative_to(pathlib.Path.cwd())
        print(f"Usage: python3 {relative} [prod]")
        exit(1)


async def main():
    print("Running the bot in", "production" if prod else "development", "mode:")

    if prod:
        handler = logging.FileHandler("discord.log", encoding="utf-8")
        discord.utils.setup_logging(handler=handler, level=logging.INFO)
    else:
        discord.utils.setup_logging(level=logging.INFO)

    async with (
        aiosqlite.connect(config.database_path, isolation_level=None) as db,
        OliviaBot(
            prod=prod,
            db=db,
            testing_guild_id=config.testing_guild_id,
            testing_channel_id=config.testing_channel_id,
            webhook_url=config.webhook_url,
            tester_bot_id=config.tester_bot_id,
            tester_bot_token=config.tester_bot_token,
            qwd_id=config.qwd_id,
        ) as oliviabot,
    ):
        try:
            await oliviabot.start()
        except asyncio.CancelledError:
            pass
        finally:
            logging.info("Shutting down...")


asyncio.run(main())

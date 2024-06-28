import asyncio
import logging

import aiosqlite
import discord

import config
import bot


async def main():
    initial_extensions = ["jishaku", "cogs.testing", "cogs.gadgets", "cogs.meta"]
    discord.utils.setup_logging(level=logging.INFO)

    async with aiosqlite.connect(
        config.database_path, autocommit=True
    ) as db, bot.OliviaBot(
        db=db,
        initial_extensions=initial_extensions,
        testing_guild_id=config.testing_guild_id,
        testing_channel_id=config.testing_channel_id,
        webhook_url=config.webhook_url,
        tester_bot_id=config.tester_bot_id,
        tester_bot_token=config.tester_bot_token,
    ) as oliviabot:
        try:
            await oliviabot.start(config.bot_token)
        except asyncio.CancelledError:
            logging.info("Shutting down...")
            await oliviabot.close()
            await db.close()


asyncio.run(main())

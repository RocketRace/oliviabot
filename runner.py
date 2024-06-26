import asyncio
import logging

import aiosqlite
import discord

import config
import bot


async def main():
    startup_extensions = ["jishaku", "cogs.testing", "cogs.gadgets"]
    discord.utils.setup_logging(level=logging.INFO)

    async with aiosqlite.connect(
        config.database_path, autocommit=True
    ) as db, bot.OliviaBot(
        db=db,
        startup_extensions=startup_extensions,
        testing_guild_id=config.testing_guild_id,
        webhook_url=config.webhook_url,
    ) as oliviabot:
        try:
            await oliviabot.start(config.bot_token)
        except asyncio.CancelledError:
            logging.info("Shutting down...")
            await oliviabot.close()
            await db.close()


asyncio.run(main())

import asyncio
import logging
from discord.ext import commands
import aioconsole

from context import OliviaBot


class Reloader(commands.Cog):
    """Automatic bot reloading, to replace the Terminal cog in prod"""

    async def reload_loop(self) -> None:
        while True:
            try:
                line: str = await aioconsole.ainput("Cog actions: ")
            except asyncio.CancelledError:
                logging.info("Stopping reloader loop")
                return

            for chunk in line.split(","):
                action, extension = chunk.split(" ")
                try:
                    if action == "load":
                        await self.bot.load_extension(extension)
                    elif action == "reload":
                        await self.bot.reload_extension(extension)
                    elif action == "unload":
                        await self.bot.unload_extension(extension)

                except commands.ExtensionError as e:
                    logging.error(f"Failed to {action} extension {extension}: {e}")

    async def cog_load(self):
        logging.info("Starting reloader loop")
        self.task = asyncio.create_task(self.reload_loop())

    async def cog_unload(self):
        self.task.cancel()

    def __init__(self, bot: OliviaBot):
        self.bot = bot


async def setup(bot: OliviaBot):
    await bot.add_cog(Reloader(bot))

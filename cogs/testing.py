import asyncio
from discord.ext import commands
import discord
import aioconsole
import discord.http

from bot import OliviaBot


class Testing(commands.Cog):
    """Terminal-based command execution for rapid local testing"""

    async def test_loop(self) -> None:
        while True:
            line = await aioconsole.ainput("> ", loop=self.bot.loop)
            await self.tester.http.send_message(
                12345,
                params=discord.http.MultipartParameters({"content": line}, None, None),
            )

    async def cog_load(self):
        await self.tester.login(self.bot.tester_bot_token)
        self.task = asyncio.create_task(self.test_loop())

    async def cog_unload(self):
        self.task.cancel()

    def __init__(self, bot: OliviaBot):
        self.bot = bot
        self.tester = discord.Client(intents=discord.Intents.none())


async def setup(bot: OliviaBot):
    await bot.add_cog(Testing(bot))

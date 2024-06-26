import asyncio
from typing import Coroutine
from discord.ext import commands
import discord
import aioconsole

from bot import OliviaBot


class MockMessage:
    def __init__(self, bot: OliviaBot, content: str) -> None:
        self.__bot = bot

        self.content = content
        self.id = 12345
        self.channel = discord.Object(12345)

    @property
    def author(self):
        return discord.Object(self.__bot.owner_id)


class MockContext(commands.Context[OliviaBot]):
    async def send(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, content: str | None = None, /, *args, **kwargs
    ) -> MockMessage:
        await aioconsole.aprint(content)

        return MockMessage(self.bot, content or "")


class Testing(commands.Cog):
    """Terminal-based command execution for rapid local testing"""

    async def event_loop(self) -> None:
        line = await aioconsole.ainput()
        ctx = await self.bot.get_context(
            MockMessage(
                self.bot,
                line,
            ),  # pyright: ignore[reportArgumentType]
            cls=MockContext,
        )
        await self.bot.invoke(ctx)

    async def cog_load(self):
        self.task = asyncio.create_task(self.event_loop())

    async def cog_unload(self):
        self.task.cancel()

    def __init__(self, bot: OliviaBot):
        self.bot = bot


async def setup(bot: OliviaBot):
    await bot.add_cog(Testing(bot))

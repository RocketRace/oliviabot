import asyncio
import contextlib
import logging
from typing import Any

import aiosqlite
import discord
from discord.ext import commands

from config import tester_bot_id
import config


class OliviaBot(commands.Bot):
    owner_ids: set[int]
    ctx_class: type[commands.Context]
    terminal_cog_interrupted: bool

    def __init__(
        self,
        *,
        prod: bool,
        db: aiosqlite.Connection,
        testing_guild_id: int,
        testing_channel_id: int,
        webhook_url: str,
        tester_bot_id: int,
        tester_bot_token: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            commands.when_mentioned_or("+"),
            intents=discord.Intents.all(),
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                roles=False,
            ),
            **kwargs,
        )
        self.initial_extensions = [
            # external libraries
            "jishaku",
            # cogs
            "cogs.context",
            "cogs.gadgets",
            "cogs.meta",
        ]
        if not prod:
            # development cogs
            self.initial_extensions.append("cogs.terminal")

        self.db = db
        self.testing_guild_id = testing_guild_id
        self.testing_channel_id = testing_channel_id
        self.webhook_url = webhook_url
        self.tester_bot_id = tester_bot_id
        self.tester_bot_token = tester_bot_token
        self.ctx_class = commands.Context
        self.terminal_cog_interrupted = False

    async def get_context(self, message, *, cls: type[commands.Context] | None = None):
        if cls is None:
            cls = self.ctx_class
        return await super().get_context(message, cls=cls)

    async def on_ready(self) -> None:
        assert self.user
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")

    async def setup_hook(self) -> None:
        self.webhook = discord.Webhook.from_url(self.webhook_url, client=self)

        owner_id = (await self.application_info()).owner.id
        self.owner_ids = {  # pyright: ignore[reportIncompatibleVariableOverride]
            owner_id,
            tester_bot_id,
        }

        for extension in self.initial_extensions:
            await self.load_extension(extension)

        guild = discord.Object(self.testing_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


@contextlib.asynccontextmanager
async def init(*, prod: bool):
    handler = logging.FileHandler("discord.log", encoding="utf-8")
    discord.utils.setup_logging(handler=handler, level=logging.INFO)

    stack = contextlib.AsyncExitStack()

    db = await stack.enter_async_context(
        aiosqlite.connect(config.database_path, autocommit=True)
    )

    bot = await stack.enter_async_context(
        OliviaBot(
            prod=prod,
            db=db,
            testing_guild_id=config.testing_guild_id,
            testing_channel_id=config.testing_channel_id,
            webhook_url=config.webhook_url,
            tester_bot_id=config.tester_bot_id,
            tester_bot_token=config.tester_bot_token,
        )
    )

    try:
        yield bot
    finally:
        await stack.aclose()

import logging
from typing import Any

import aiosqlite
import discord
from discord.ext import commands

from config import tester_bot_id


class OliviaBot(commands.Bot):
    owner_ids: set[int]
    ctx_class: type[commands.Context]
    terminal_cog_interrupted: bool

    def __init__(
        self,
        initial_extensions: list[str],
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

        self.initial_extensions = initial_extensions
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

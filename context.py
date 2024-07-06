import logging
from typing import Any, Coroutine

import aiosqlite
import discord
from discord.ext import commands

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
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            commands.when_mentioned_or("+"),
            intents=intents,
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                roles=False,
            ),
            **kwargs,
        )
        self.activated_extensions = [
            # external libraries
            "jishaku",
            # cogs
            "cogs.gadgets",
            "cogs.errors",
            "cogs.meta",
        ]
        if prod:
            # prod cogs
            pass
            # self.activated_extensions.append("cogs.reload")
        else:
            # development cogs
            self.activated_extensions.append("cogs.terminal")

        self.db = db
        self.testing_guild_id = testing_guild_id
        self.testing_channel_id = testing_channel_id
        self.webhook_url = webhook_url
        self.tester_bot_id = tester_bot_id
        self.tester_bot_token = tester_bot_token
        self.ctx_class = commands.Context
        self.terminal_cog_interrupted = False

    def start(self, *args, **kwargs) -> Coroutine[Any, Any, None]:
        return super().start(config.bot_token, *args, **kwargs)

    async def get_context(self, message, *, cls: type[commands.Context] | None = None):
        if cls is None:
            cls = self.ctx_class
        return await super().get_context(message, cls=cls)

    async def on_ready(self) -> None:
        assert self.user
        open(".build-success", "w")
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")

    async def setup_hook(self) -> None:
        self.webhook = discord.Webhook.from_url(self.webhook_url, client=self)

        owner_id = (await self.application_info()).owner.id
        self.owner_ids = {  # pyright: ignore[reportIncompatibleVariableOverride]
            owner_id,
            config.tester_bot_id,
        }

        for extension in self.activated_extensions:
            await self.load_extension(extension)

        guild = discord.Object(self.testing_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


class Context(commands.Context[OliviaBot]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_handled = False

import logging
import re
from typing import Any, Dict, List

import aiosqlite
import discord
from discord.ext import commands
from discord.ext.commands.view import StringView

# resolve dependency cycle without strings
type OliviaBotAlias = OliviaBot


class Context(commands.Context[OliviaBotAlias]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_handled = False


class OliviaBot(commands.Bot):
    def __init__(
        self,
        startup_extensions: list[str],
        db: aiosqlite.Connection,
        testing_guild_id: int,
        webhook_url: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            commands.when_mentioned,
            intents=discord.Intents.all(),
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                roles=False,
            ),
            **kwargs,
        )

        self.webhook_url = webhook_url
        self.db = db
        self.testing_guild_id = testing_guild_id
        self.initial_extensions = startup_extensions

    async def on_ready(self) -> None:
        assert self.user
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")

    async def setup_hook(self) -> None:
        self.webhook = discord.Webhook.from_url(self.webhook_url, client=self)

        def regexp(pattern: str, string: str) -> bool:
            return re.match(pattern, string) is not None

        await self.db.create_function("regexp", 2, regexp, deterministic=True)

        for extension in self.initial_extensions:
            await self.load_extension(extension)

        guild = discord.Object(self.testing_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def get_context(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, message, *, cls=Context
    ):
        return await super().get_context(message, cls=cls)

import logging
from typing import Any

import aiosqlite
import discord
from discord.ext import commands

# resolve dependency cycle without strings
type OliviaBotAlias = OliviaBot


class Context(commands.Context[OliviaBotAlias]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_handled = False


class TestContext(Context):
    async def send(self, content: str | None = None, **kwargs):
        if content:
            print("->", content)
        return await super().send(content, **kwargs)


class OliviaBot(commands.Bot):
    owner_id: int

    def __init__(
        self,
        startup_extensions: list[str],
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

        self.initial_extensions = startup_extensions
        self.db = db
        self.testing_guild_id = testing_guild_id
        self.testing_channel_id = testing_channel_id
        self.webhook_url = webhook_url
        self.tester_bot_id = tester_bot_id
        self.tester_bot_token = tester_bot_token

    async def process_commands(self, message: discord.Message) -> None:
        if message.author.id == self.tester_bot_id:
            ctx = await self.get_context(message, cls=TestContext)
            await self.invoke(ctx)
        else:
            if message.author.bot:
                return

            ctx = await self.get_context(message)
            await self.invoke(ctx)

    async def get_context(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, message, *, cls=Context
    ):
        return await super().get_context(message, cls=cls)

    async def on_ready(self) -> None:
        assert self.user
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")

    async def setup_hook(self) -> None:
        self.webhook = discord.Webhook.from_url(self.webhook_url, client=self)

        owner_id = (await self.application_info()).owner.id
        self.owner_id = owner_id  # type: ignore

        for extension in self.initial_extensions:
            await self.load_extension(extension)

        guild = discord.Object(self.testing_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

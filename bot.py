from __future__ import annotations
import logging
from typing import Any, Coroutine

import aiosqlite
import discord
from discord.ext import commands

import config


def qwd_only():
    async def predicate(ctx: Context) -> bool:
        if ctx.author.id in ctx.bot.owner_ids:
            return True
        if ctx.guild and ctx.guild.id == ctx.bot.qwd_id:
            return True
        return False

    return commands.check(predicate)


class OliviaBot(commands.Bot):
    owner_ids: set[int]
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
        qwd_id: int,
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
            "cogs.louna",
            "cogs.vore",
            "cogs.errors",
            "cogs.meta",
        ]
        if prod:
            # prod cogs
            pass  # self.activated_extensions.append("cogs.reload")
        else:
            # development cogs
            self.activated_extensions.append("cogs.terminal")

        self.db = db
        self.testing_guild_id = testing_guild_id
        self.testing_channel_id = testing_channel_id
        self.webhook_url = webhook_url
        self.tester_bot_id = tester_bot_id
        self.tester_bot_token = tester_bot_token
        self.qwd_id = qwd_id
        self.terminal_cog_interrupted = False

    def start(self, *args, **kwargs) -> Coroutine[Any, Any, None]:
        return super().start(config.bot_token, *args, **kwargs)

    async def get_context(self, message, *, cls: type[commands.Context] | None = None):
        return await super().get_context(message, cls=cls or Context)

    async def on_ready(self) -> None:
        assert self.user
        webhook = discord.Webhook.from_url(self.webhook_url, client=self)
        msg = f"Logged in as {self.user} (ID: {self.user.id})"
        logging.info(msg)
        await webhook.send(msg)

    async def perform_migrations(self):
        async with self.db.cursor() as cur:
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS params(
                    last_neofetch_update INTEGER
                );
                CREATE TABLE IF NOT EXISTS neofetch(
                    distro TEXT NOT NULL,
                    suffix TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    mobile_width INTEGER NOT NULL,
                    color_index INTEGER NOT NULL,
                    color_rgb TEXT NOT NULL,
                    logo TEXT NOT NULL
                );
                """
            )
            await cur.execute(
                """CREATE TABLE IF NOT EXISTS vore(
                    timestamp INTEGER PRIMARY KEY,
                    channel_id INTEGER,
                    message_id INTEGER
                );
                """
            )
            try:
                await cur.execute(
                    """ALTER TABLE params ADD COLUMN louna_command_count INTEGER DEFAULT 0;
                    ALTER TABLE params ADD COLUMN louna_emoji_count INTEGER DEFAULT 0;
                    """
                )
            except aiosqlite.OperationalError:
                pass

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

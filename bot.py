from __future__ import annotations
import asyncio
import contextlib
import logging
from typing import Any, Coroutine

import aiosqlite
import aiosqlite.context
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
            description="Hi! I'm oliviabot, an automated version of Olivia!\nI try my best to bring you joy.",
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
            "cogs.meta",
            "cogs.errors",
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

    async def is_proxied(self, user: discord.abc.User) -> bool:
        async with self.cursor() as cur:
            await cur.execute(
                "SELECT EXISTS (SELECT * FROM proxiers WHERE user_id = ?);",
                [user.id],
            )
            result = await cur.fetchone()
        return bool(result and result[0])

    async def process_commands(self, message: discord.Message) -> None:
        if await self.is_proxied(message.author):
            try:
                new_message = await self.wait_for(
                    "message",
                    timeout=2.0,
                    check=lambda new_message: (
                        new_message.author.bot
                        and new_message.channel == message.channel
                        and new_message.content in message.content
                    ),
                )
                ctx = await self.get_context(new_message)
                ctx.author = message.author
            except asyncio.TimeoutError:
                ctx = await self.get_context(message)

            await self.invoke(ctx)
        else:
            await super().process_commands(message)
            if not message.author.bot:
                try:
                    new_message = await self.wait_for(
                        "message",
                        timeout=2.0,
                        check=lambda new_message: (
                            new_message.author.bot
                            and new_message.channel == message.channel
                            and new_message.content in message.content
                            and message.content.startswith("+")
                        ),
                    )
                    # hack for better ux
                    if not new_message.content.startswith("+proxy"):
                        await message.channel.send(
                            "Hint: You can enable proxy mode using `+proxy enable`, "
                            "which lets this bot respond to your proxy messages."
                        )
                except asyncio.TimeoutError:
                    pass

    async def on_ready(self) -> None:
        assert self.user
        webhook = discord.Webhook.from_url(self.webhook_url, client=self)
        msg = f"Logged in as {self.user} (ID: {self.user.id})"
        logging.info(msg)
        await webhook.send(msg)

    async def perform_migrations(self):
        async with self.cursor() as cur:
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS params(
                    last_neofetch_update INTEGER
                );
                """
            )
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS neofetch(
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
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS vore(
                    timestamp INTEGER PRIMARY KEY,
                    channel_id INTEGER,
                    message_id INTEGER
                );
                """
            )
            try:
                await cur.executescript(
                    """ALTER TABLE params ADD COLUMN louna_command_count INTEGER DEFAULT 0;
                    ALTER TABLE params ADD COLUMN louna_emoji_count INTEGER DEFAULT 0;
                    """
                )
            except aiosqlite.OperationalError:
                pass
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS proxiers(
                    user_id INTEGER PRIMARY KEY
                )
                """
            )

    async def setup_hook(self) -> None:
        self.webhook = discord.Webhook.from_url(self.webhook_url, client=self)

        app_info = await self.application_info()
        owner_id = app_info.owner.id
        self.owner_ids = {  # pyright: ignore[reportIncompatibleVariableOverride]
            owner_id,
            config.tester_bot_id,
        }

        await self.perform_migrations()

        for extension in self.activated_extensions:
            await self.load_extension(extension)

        guild = discord.Object(self.testing_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    def cursor(self) -> aiosqlite.context.Result[aiosqlite.Cursor]:
        """Returns a context manager to a cursor object."""
        return self.db.cursor()


class Cog(commands.Cog):
    bot: OliviaBot


class Context(commands.Context[OliviaBot]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_handled = False

    def cursor(self) -> aiosqlite.context.Result[aiosqlite.Cursor]:
        """Returns a context manager to a cursor object."""
        return self.bot.cursor()

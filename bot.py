from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
import logging
from pathlib import Path
import re
from typing import Any, Callable

import aiosqlite
import aiosqlite.context
import discord
from discord.ext import commands

import config

class OliviaBot(commands.Bot):
    owner_ids: set[int]
    terminal_cog_interrupted: bool
    qwd: discord.Guild
    person_aliases: dict[str, list[int]]
    inv_person_aliases: dict[int, list[str]]

    def __init__(
        self,
        *,
        prod: bool,
        db: aiosqlite.Connection,
        chitter_db: aiosqlite.Connection,
        testing_guild_id: int,
        testing_channel_id: int,
        webhook_url: str,
        tester_bot_id: int,
        tester_bot_token: str,
        qwd_id: int,
        real_olivia_id: int,
        allowed_webhook_channel_id: int,
        louna_id: int,
        bot_chitter_id: int,
        **kwargs: Any,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
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
            "cogs.utilities",
            "cogs.chitter"
        ]
        if prod:
            # prod cogs
            self.activated_extensions.append("cogs.reload")
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
        self.louna_id = louna_id
        self.real_olivia_id = real_olivia_id
        self.allowed_webhook_channel_id = allowed_webhook_channel_id
        self.bot_chitter_id = bot_chitter_id
        self.terminal_cog_interrupted = False
        self.person_aliases = {}
        self.inv_person_aliases = {}

    async def start(self, *args, **kwargs):
        return await super().start(config.bot_token, *args, **kwargs)

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

    async def on_ready(self) -> None:
        assert self.user
        await self.webhook.send(f"Logged in as {self.user} (ID: {self.user.id})")
    
    async def webhook_send(self, message: str) -> None:
        assert self.user
        webhook = discord.Webhook.from_url(self.webhook_url, client=self)
        msg = f"Logged in as {self.user} (ID: {self.user.id})"
        logging.info(msg)
        await webhook.send(msg)

    async def perform_migrations(self):
        async with self.cursor() as cur:
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS params(
                    last_neofetch_update INTEGER NOT NULL
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
                    channel_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL
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
                );
                """
            )
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS likers(
                    user_id INTEGER PRIMARY KEY,
                    enabled_after REAL NOT NULL
                );
                """
            )
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS auto_olivias(
                    user_id INTEGER PRIMARY KEY
                );
                """
            )
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS tempemoji(
                    emoji_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    delete_at REAL NOT NULL
                );
                """
            )
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS louna_emojis(
                    emoji TEXT PRIMARY KEY,
                    weight REAL NOT NULL DEFAULT 0
                );
                """
            )
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS person_aliases(
                    alias TEXT PRIMARY KEY,
                    id INTEGER NOT NULL
                );
                """
            )
            # huge shuffle just to change the primary key fr
            try:
                await cur.executescript(
                    """ALTER TABLE params ADD COLUMN using_new_person_aliases INTEGER DEFAULT 0;
                    """
                )
            except aiosqlite.OperationalError:
                pass
            await cur.execute(
                """SELECT using_new_person_aliases FROM params;
                """
            )
            [[using_new_person_aliases]] = list(await cur.fetchall())
            if not using_new_person_aliases:
                await cur.executescript(
                    """CREATE TABLE IF NOT EXISTS new_person_aliases(
                        alias TEXT NOT NULL,
                        id INTEGER NOT NULL,
                        PRIMARY KEY(alias, id)
                    );
                    INSERT INTO new_person_aliases SELECT * FROM person_aliases;
                    DROP TABLE person_aliases;
                    ALTER TABLE new_person_aliases RENAME TO person_aliases;
                    UPDATE params SET using_new_person_aliases = 1;
                    """
                )
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS ticker_hashes(
                    command TEXT NOT NULL,
                    hash INTEGER NOT NULL,
                    delete_at REAL NOT NULL,
                    PRIMARY KEY(command, hash)
                )"""
            )
            try:
                await cur.executescript(
                    """ALTER TABLE likers ADD COLUMN enabled_in_cw INTEGER DEFAULT 0;
                    """
                )
            except aiosqlite.OperationalError:
                pass
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS user_stacks(
                    user_id INTEGER NOT NULL,
                    idx INTEGER NOT NULL,
                    value TEXT NOT NULL,
                    type TEXT NOT NULL,
                    PRIMARY KEY(user_id, idx)
                )"""
            )
            try:
                await cur.executescript(
                    """ALTER TABLE person_aliases ADD COLUMN chitter_message_id INTEGER DEFAULT NULL;
                    """
                )
            except aiosqlite.OperationalError:
                pass
            # await cur.executescript(
            #     """CREATE TABLE IF NOT EXISTS user_settings(
            #         id INTEGER PRIMARY KEY,
            #         proxied INTEGER NOT NULL DEFAULT 0,
            #         autoliking_after REAL,
            #         cw_allowed INTEGER NOT NULL DEFAULT 0,
            #     )"""
            # )

    async def backup_database(self):
        backup_dir = Path.cwd() / "backups"
        backup_dir.mkdir(exist_ok=True)
        previous_backups = sorted(list(backup_dir.glob("backup-*.db")))
        now = datetime.now()
        # skip if the last backup was less than 24 hours ago
        if previous_backups:
            _, _, iso = previous_backups[-1].stem.partition("-")
            last_backup = datetime.fromisoformat(iso)
            if last_backup + timedelta(days=1) > now:
                logging.info(f"Skipping backup as one exists from {last_backup}")
                return
        # allow only 8 live backups at a time
        for i in range(len(previous_backups) - 7):
            old_backup = previous_backups[i]
            old_backup.unlink()
        # create new backup
        backup_ts = now.isoformat(timespec="seconds")
        new_backup = backup_dir / f"backup-{backup_ts}.db"
        logging.info(f"creating backup at {new_backup}")
        async with aiosqlite.connect(new_backup) as conn:
            await self.db.backup(conn)
        logging.info("backup successful")
        await self.webhook.send(file=discord.File(new_backup))

    async def refresh_aliases(self):
        self.person_aliases = {}
        self.inv_person_aliases = {}
        async with self.cursor() as cur:
            await cur.execute("""SELECT alias, id FROM person_aliases;""")
            aliases = await cur.fetchall()
            for alias, user_id in aliases:
                self.person_aliases.setdefault(alias, []).append(user_id)
                self.inv_person_aliases.setdefault(user_id, []).append(alias)

    async def setup_hook(self) -> None:
        self.webhook = discord.Webhook.from_url(self.webhook_url, client=self)

        app_info = await self.application_info()
        owner_id = app_info.owner.id
        self.owner_ids = {  # pyright: ignore[reportIncompatibleVariableOverride]
            owner_id,
            config.tester_bot_id,
        }

        await self.backup_database()
        await self.perform_migrations()

        async with self.cursor() as cur:
            await cur.execute("""SELECT user_id FROM auto_olivias;""")
            olivias = await cur.fetchall()
            for [olivia] in olivias:
                self.owner_ids.add(olivia)
        
        await self.refresh_aliases()

        for extension in self.activated_extensions:
            await self.load_extension(extension)

        guild = discord.Object(self.testing_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


    def cursor(self) -> aiosqlite.context.Result[aiosqlite.Cursor]:
        """Returns a context manager to a cursor object."""
        return self.db.cursor()
    
    # These will be overridden by the chitter cog
    async def chitter_send(self, table_name: str, *args: Any) -> int | None: ...
    async def chitter_edit(self, table_name: str, message_id: int, *args: Any): ...
    async def chitter_delete(self, table_name: str, message_id: int): ...


class Cog(commands.Cog):
    bot: OliviaBot


class Context(commands.Context[OliviaBot]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_handled = False

    def cursor(self) -> aiosqlite.context.Result[aiosqlite.Cursor]:
        """Returns a context manager to a cursor object."""
        return self.bot.cursor()
    
    async def ack(self, message: str | None = None, emoji: str = "🫶") -> None:
        if message:
            await self.send(message)
        await self.message.add_reaction(emoji)

    async def send(self, content: str | None = None, **kwargs) -> discord.Message:
        # - under 2000 is unchanged
        # - over 2000 is cropped down to fit the suffix at exactly 2000 chars
        limit = 2000
        if content and len(content) > limit:
            suffix = " [... I have so much to say!]"
            content = content[:limit - len(suffix)] + suffix
        return await super().send(content, **kwargs)

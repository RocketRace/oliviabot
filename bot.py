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

def qwd_only():
    async def predicate(ctx: Context) -> bool:
        if ctx.author.id in ctx.bot.owner_ids:
            return True
        if ctx.guild and ctx.guild.id == ctx.bot.qwd_id:
            return True
        raise NotQwd

    return commands.check(predicate)


def louna_only():
    async def predicate(ctx: Context) -> bool:
        if ctx.author.id != ctx.bot.louna_id:
            raise NotLouna
        return True
    return commands.check(predicate)

class NotQwd(commands.CheckFailure):
    pass

class NotLouna(commands.CheckFailure):
    pass


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
        testing_guild_id: int,
        testing_channel_id: int,
        webhook_url: str,
        tester_bot_id: int,
        tester_bot_token: str,
        qwd_id: int,
        real_olivia_id: int,
        allowed_webhook_channel_id: int,
        louna_id: int,
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

AnyUser = discord.User | discord.Member | discord.ClientUser

class QwdieConverter(commands.Converter[AnyUser]):
    def try_find_user(self, bot: OliviaBot, key, mapper: Callable[[discord.User]]):
        return discord.utils.find(
            lambda user: mapper(user) == key,
            bot.users
        )

    async def convert(self, ctx: commands.Context[OliviaBot], argument: str):
        choices: list[AnyUser | None] = []
        # id, mention and username are all unique
        if re.match(r"[0-9]{15,20}", argument):
            choices.append(ctx.bot.get_user(int(argument)))
        mention_match = re.match(r"<@!?([0-9]{15,20})>$", argument)
        if mention_match:
            choices.append(ctx.bot.get_user(int(mention_match.group(1))))
        discrim_match = re.match(r"(.+)#([0-9]{4})", argument)
        if discrim_match:
            choices.append(discord.utils.get(
                ctx.bot.users,
                name=discrim_match.group(1),
                discriminator=discrim_match.group(2)
            ))
        # okay technically the username is nonunique because bots still don't have pomelo
        choices.extend([
            user for user in ctx.bot.users
            if user.name.lower() == argument.lower()
        ])
        # global name and guild nickname are not unique, so scan all the options
        # this may change later for performance purposes but I only have 100ish users
        choices.extend([
            user for user in ctx.bot.users
            if user.global_name and user.global_name.lower() == argument.lower()
        ])
        if ctx.guild:
            choices.extend([
                member for member in ctx.guild.members
                if member.nick and member.nick.lower() == argument.lower()
            ])
        # aliases
        choices.extend(ctx.bot.get_user(id) for id in ctx.bot.person_aliases.get(argument.lower(), []))
        # special results
        if argument.lower() in ("me", "🪟"):
            choices.append(ctx.author)
        everyone = ""
        if argument.lower() in ("@everyone", "🪩"):
            everyone = " (you have to pick one sorry)"
            if ctx.guild:
                choices.extend(ctx.guild.members)
            else:
                choices.extend([ctx.author, ctx.me])
        # finally resolve the user
        valid_choices = list(set(filter(None, choices)))
        if len(valid_choices) == 1:
            return valid_choices[0]
        elif len(valid_choices) >= 2:
            # disambiguate between choices
            valid_choices = sorted(valid_choices, key=lambda user: str(user).lower())
            content = f"which {argument.lower()}?{everyone}"
            view = QwdieDisambiguator(
                target=ctx.author,
                choices=valid_choices,
                whole_guild=set(valid_choices) == set(ctx.guild and ctx.guild.members or [ctx.author, ctx.me])
            )
            msg = await ctx.send(content, view=view)
            await view.wait()
            if view.selected is None:
                for child in view.children:
                    assert isinstance(child, (QwdieButton, QwdieSelect, QwdieUserSelect))
                    child.disabled = True
                await msg.edit(view=view)
                raise TimeoutError
            else:
                return view.selected
        else:
            raise commands.UserNotFound(argument)

class QwdieButton(discord.ui.Button['QwdieDisambiguator']):
    def __init__(self, user: AnyUser):
        # A bit kludgey
        super().__init__(style=discord.ButtonStyle.gray, label=f"@{user}")
        self.user = user
    
    async def callback(self, interaction: discord.Interaction):
        assert self.view
        view: QwdieDisambiguator = self.view
        view.selected = self.user
        for child in view.children:
            assert isinstance(child, QwdieButton)
            child.disabled = True
        self.style = discord.ButtonStyle.green
        await interaction.response.edit_message(view=view)
        view.stop()

def first_difference_at(a: str, b: str) -> int:
    i = 0
    for i, (x, y) in enumerate(zip(a, b)):
        # technically can cause issues due to unicode case folding
        if x.lower() != y.lower():
            return i
    return i + 1

class QwdieSelect(discord.ui.Select['QwdieDisambiguator']):
    def __init__(
            self,
            previous: AnyUser | None,
            users: list[AnyUser],
            next: AnyUser | None
        ):
        # when previous is None, users is 25 long
        # when next is None, users may be as short as 1 long
        start = str(users[0])[
            :first_difference_at(
                *(str(users[0]), str(users[1]))
                if previous is None
                else (str(previous), str(users[0]))
            ) + 1
        ]
        if len(users) > 1:
            end = str(users[-1])[
                :first_difference_at(
                    *(str(users[-2]), str(users[-1]))
                    if next is None else
                    (str(users[-1]), str(next))
                ) + 1
            ]
            placeholder = f"Select ({start.upper()} –- {end.upper()})"
        else:
            placeholder = f"Select ({start.upper()})"
        super().__init__(
            placeholder=placeholder,
            options=[
                discord.SelectOption(label=f"@{user}", value=str(i))
                for i, user in enumerate(users)
            ]
        )
        self.users = users
    
    async def callback(self, interaction: discord.Interaction):
        assert self.view
        view: QwdieDisambiguator = self.view
        view.selected = self.users[int(self.values[0])]
        for child in view.children:
            assert isinstance(child, QwdieSelect)
            child.disabled = True
        self.placeholder = f"@{view.selected}"
        await interaction.response.edit_message(view=view)
        view.stop()

class QwdieUserSelect(discord.ui.UserSelect['QwdieDisambiguator']):
    def __init__(self) -> None:
        super().__init__(placeholder = "Select user")

    async def callback(self, interaction: discord.Interaction):
        assert self.view
        view: QwdieDisambiguator = self.view
        view.selected = self.values[0]
        self.placeholder = f"@{view.selected}"
        self.disabled = True
        await interaction.response.edit_message(view=view)
        view.stop()

class QwdieDisambiguator(discord.ui.View):
    def __init__(self, *, target: AnyUser, choices: list[AnyUser], whole_guild: bool):
        super().__init__()
        self.target = target
        self.selected: AnyUser | None = None
        self.msg: discord.Message
        if whole_guild:
            self.add_item(QwdieUserSelect())
        elif len(choices) <= 25:
            for choice in choices:
                self.add_item(QwdieButton(choice))
        elif len(choices) <= 125:
            max = len(choices)
            for i in range(0, max, 25):
                self.add_item(QwdieSelect(
                    choices[i - 1] if i != 0 else None,
                    choices[i : i + 25],
                    choices[i + 25] if i + 25 < max else None
                ))
        else:
            raise RuntimeError("i don't know what to do here")

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.target:
            await interaction.response.send_message("not for you!", ephemeral=True)
            return False
        else:
            return True

import datetime
import logging
import re
from typing import Any, Callable, TypeVar, overload

import aiosqlite
from discord.ext import commands
import discord

from bot import OliviaBot, Context

T = TypeVar("T")

def get_partial_message(bot: OliviaBot, guild_id: int, channel_id: int, message_id: int) -> discord.PartialMessage:
    return bot.get_partial_messageable(channel_id, guild_id=guild_id).get_partial_message(message_id)

class Null:
    pass
null = Null()

AnyValue = str | float | discord.Object | discord.PartialMessage | discord.PartialEmoji | datetime.datetime | bool | Null

class BotChitter(commands.Cog):
    def __init__(self, bot: OliviaBot):
        self.bot = bot
        self.own_tables = {123: self.serialize_generic_row}
        self.known_tables = {123: self.parse_generic_row}
        self.table_aliases = { "aliases": 123 }
        # TODO initialize
        self.raw_chitter_store: dict[int, dict[int, list[AnyValue]]] = {}

    async def cog_load(self) -> None:
        chitter = self.bot.get_channel(self.bot.bot_chitter_id)
        if not isinstance(chitter, discord.ForumChannel):
            logging.warning("bot-chitter channel is not a forum channel")
            return
        
        for thread in chitter.threads:
            await self.assign_history(thread)

        self.original_chitter_send = self.bot.chitter_send
        self.original_chitter_edit = self.bot.chitter_edit
        self.original_chitter_delete = self.bot.chitter_delete
        self.bot.chitter_send = self.chitter_send
        self.bot.chitter_edit = self.chitter_edit
        self.bot.chitter_delete = self.chitter_delete

    async def cog_unload(self) -> None:
        self.bot.chitter_send = self.original_chitter_send
        self.bot.chitter_edit = self.original_chitter_edit
        self.bot.chitter_delete = self.original_chitter_delete

    async def chitter_send(self, table_name: str, *args: Any) -> int:
        table_id = self.table_aliases[table_name]
        serialized = self.own_tables[table_id](list(args))
        thread = self.bot.get_channel(table_id)
        if not isinstance(thread, discord.Thread):
            raise RuntimeError("Bad table?")
        msg = await thread.send(serialized)
        return msg.id

    async def chitter_edit(self, table_name: str, message_id: int, *args: Any):
        table_id = self.table_aliases[table_name]
        serialized = self.own_tables[table_id](list(args))
        thread = self.bot.get_channel(table_id)
        if not isinstance(thread, discord.Thread):
            raise RuntimeError("Bad table?")
        await thread.get_partial_message(message_id).edit(content = serialized)
        
    async def chitter_delete(self, table_name: str, message_id: int):
        table_id = self.table_aliases[table_name]
        thread = self.bot.get_channel(table_id)
        if not isinstance(thread, discord.Thread):
            raise RuntimeError("Bad table?")
        await thread.get_partial_message(message_id).delete()

    def parse_string(self, string: str, transformer: Callable[[str], T] = lambda x: x) -> tuple[T, str] | None:
        escapes = r'\\[^a-zA-Z0-9]|\\[nrt0]|\\x[0-7][0-9a-fA-F]'
        pattern = fr'`*"((?:[^\\"]|{escapes})*)"`*'
        if match := re.match(pattern, string):
            def unescaper(m: re.Match[str]) -> str:
                match list(m.group()):
                    case ["\\", "n"]: return "\n"
                    case ["\\", "r"]: return "\r"
                    case ["\\", "t"]: return "\t"
                    case ["\\", "0"]: return "\0"
                    case ["\\", "x", hi, lo]: return chr(int(hi + lo, 16))
                    case ["\\", other]: return other
                    case _: raise RuntimeError("unreachable")
            return transformer(re.sub(escapes, unescaper, match.group(1))), string[match.end():]

    def parse_number(self, string: str, transformer: Callable[[str], T] = float) -> tuple[T, str] | None:
        if match := re.match(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', string):
            return transformer(match.group()), string[match.end():]

    def parse_channel(self, string: str, transformer: Callable[[int], T] = lambda x: discord.Object(x, type=discord.abc.GuildChannel)) -> tuple[T, str] | None:
        if match := re.match(r'<#([0-9]+)>', string):
            return transformer(int(match.group(1))), string[match.end():]

    def parse_user(self, string: str, transformer: Callable[[int], T] = lambda x: discord.Object(x, type=discord.User)) -> tuple[T, str] | None:
        if match := re.match(r'<@([0-9]+)>', string):
            return transformer(int(match.group(1))), string[match.end():]

    def parse_role(self, string: str, transformer: Callable[[int], T] = lambda x: discord.Object(x, type=discord.Role)) -> tuple[T, str] | None:
        if match := re.match(r'<@&([0-9]+)>', string):
            return transformer(int(match.group(1))), string[match.end():]

    def parse_message(self, string: str, transformer: Callable[[OliviaBot, int, int, int], T] = get_partial_message) -> tuple[T, str] | None:
        if match := re.match(r'https://discord.com/channels/([0-9]+)/([0-9]+)/([0-9]+)', string):
            return transformer(self.bot, *map(int, match.group(1, 2, 3))), string[match.end():]

    def parse_emoji(self, string: str, transformer: Callable[[str], T] = discord.PartialEmoji.from_str) -> tuple[T, str] | None:
        if match := re.match(r'<a?:[a-zA-Z_0-9]+:[0-9]+>', string):
            return transformer(match.group()), string[match.end():]

    def parse_timestamp(self, string: str, transformer: Callable[[int], T] = lambda t: datetime.datetime.fromtimestamp(t, tz=datetime.UTC)) -> tuple[T, str] | None:
        if match := re.match(r'<t:([0-9]+)(?::[dDtTfFR])?>', string):
            return transformer(int(match.group(1))), string[match.end():]

    def parse_boolean(self, string: str) -> tuple[bool, str] | None:
        if string.startswith("✅") or string.startswith("❌"):
            return string[0] == "✅", string[1:]
    
    def parse_null(self, string: str) -> tuple[Null, str] | None:
        if string.startswith("🦖"):
            return null, string[1:]

    def parse_generic_row(self, row: str) -> list[AnyValue] | None:
        results = []
        while row:
            row = row.lstrip(" \r\n\t")
            parsed = None
            for option in [
                self.parse_string,
                self.parse_number,
                self.parse_channel,
                self.parse_user,
                self.parse_role,
                self.parse_message,
                self.parse_emoji,
                self.parse_timestamp,
                self.parse_boolean,
                self.parse_null
            ]:
                val = option(row)
                if val is not None:
                    parsed, row = val
                    break
            if parsed is None:
                return None
            else:
                results.append(parsed)
        # A row must have 1 or more values
        if len(results) == 0:
            return None
        return results

    def serialize_string(self, string: str, backticks = 0) -> str:
        contents = string.translate({
            ord('"'): '\\"',
            ord('\\'): '\\\\',
            ord('\n'): '\\n',
            ord('\r'): '\\r',
            ord('\t'): '\\t',
            ord('\0'): '\\0',
        } | {
            # things that may or may not be relevant for discord 
            ord(c): '\\' + c
            for c in "*_`|~-@#<>[]()/:"
        })
        return f'{backticks * "`"}"{contents}"{backticks * "`"}'
    
    serialize_bool = lambda _, b: "❌✅"[b]
    serialize_number = str
    def serialize_channel(self, c: discord.abc.Snowflake): return f"<#{c.id}>"
    def serialize_user(self, u: discord.abc.Snowflake): return f"<@{u.id}>"
    def serialize_role(self, r: discord.abc.Snowflake): return f"<@&{r.id}>"
    def serialize_message(self, m: discord.PartialMessage | discord.Message): return m.jump_url
    serialize_emoji = str
    def serialize_timestamp(self, dt: datetime.datetime): return discord.utils.format_dt(dt)
    serialize_null = lambda _, _n: "🦖"

    def serialize_generic_row(self, items: list[AnyValue]) -> str:
        '''This is meant to be used for rows parsed with parse_generic_row.
        '''
        parts: list[str] = []
        for item in items:
            match item:
                case str():
                    parts.append(self.serialize_string(item))
                case bool(): # this needs to be before the int() case, due to:
                    parts.append(self.serialize_bool(item))
                case float() | int(): # note: seems like the `float` in the type alias actually desugared to `float | int`
                    parts.append(self.serialize_number(item))
                case discord.Object():
                    if item.type == discord.abc.GuildChannel:
                        parts.append(self.serialize_channel(item))
                    elif item.type == discord.User:
                        parts.append(self.serialize_user(item))
                    elif item.type == discord.Role:
                        parts.append(self.serialize_role(item))
                    else:
                        raise RuntimeError("unreachable")
                case discord.PartialMessage():
                    parts.append(self.serialize_message(item))
                case discord.PartialEmoji():
                    parts.append(self.serialize_emoji(item))
                case datetime.datetime():
                    parts.append(self.serialize_timestamp(item))
                case Null():
                    parts.append(self.serialize_null(item))

        return " ".join(parts)
    
    def serialize_alias(self, user: discord.User, alias: str):
        return " ".join([self.serialize_user(user), self.serialize_string(alias)])

    async def assign_history(self, thread: discord.Thread):
        async for message in thread.history(limit=None):
            await self.assign_row(thread.id, message)

    async def assign_row(self, table_id: int, message: discord.Message):
        row = self.parse_generic_row(message.content)
        if row is None:
            # 
            if table_id in self.known_tables:
                # A bot has sent an invalid row. Inform them of this, in case it's a bug
                try:
                    await message.add_reaction("\N{EXCLAMATION QUESTION MARK}")
                except discord.HTTPException:
                    pass
            return 
        
        # Add the message to the default store
        self.raw_chitter_store.setdefault(table_id, {})[message.id] = row
        # TODO custom

    async def remove_row(self, table_id: int, message_id: int):
        del self.raw_chitter_store[table_id][message_id]
        # TODO custom

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.author.bot:
            return
        if not isinstance(message.channel, discord.Thread):
            return
        if message.channel.parent_id != self.bot.bot_chitter_id:
            return
        await self.assign_row(message.channel.id, message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if payload.channel_id not in self.raw_chitter_store:
            return
        if payload.message_id not in self.raw_chitter_store[payload.channel_id]:
            return
        await self.assign_row(payload.channel_id, payload.message)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.channel_id not in self.raw_chitter_store:
            return
        if payload.message_id not in self.raw_chitter_store[payload.channel_id]:
            return
        await self.remove_row(payload.channel_id, payload.message_id)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if thread.parent_id != self.bot.bot_chitter_id:
            return
        
        self.raw_chitter_store[thread.id] = {}
        # can't be in the known tables unless by an act of clairvoyance?

    @commands.Cog.listener()
    async def on_raw_thread_update(self, payload: discord.RawThreadUpdateEvent):
        if payload.parent_id != self.bot.bot_chitter_id:
            return
        thread = payload.thread
        if thread is None:
            return
        if thread.locked:
            if thread.id not in self.raw_chitter_store:
                return
            del self.raw_chitter_store[thread.id]
            # TODO need for custom?
        else:
            if thread.id in self.raw_chitter_store:
                return
            # TODO need for custom?
            await self.assign_history(thread)

    @commands.Cog.listener()
    async def on_raw_thread_delete(self, payload: discord.RawThreadDeleteEvent):
        if payload.parent_id != self.bot.bot_chitter_id:
            return
        thread = payload.thread
        if thread is None:
            return
        if thread.id not in self.raw_chitter_store:
            return
        del self.raw_chitter_store[thread.id]
        # TODO custom

    @commands.is_owner()
    @commands.group(invoke_without_command=True)
    async def table(self, ctx: Context):
        '''Administrative commands for handling #bot-chitter tables'''
        # TODO show information on followed & stored tables

    @commands.is_owner()
    @table.command()
    async def refresh(self, ctx: Context, table: str):
        '''Fetches all the data for the given table, accounting for any newly defined handlers'''
        # TODO

async def setup(bot: OliviaBot):
    await bot.add_cog(BotChitter(bot))

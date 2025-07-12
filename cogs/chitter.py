import datetime
import re
from typing import Callable, TypeVar

import aiosqlite
from discord.ext import commands
import discord

from bot import OliviaBot, Context

T = TypeVar("T")

def get_partial_message(bot: OliviaBot, guild_id: int, channel_id: int, message_id: int) -> discord.PartialMessage:
    return bot.get_partial_messageable(channel_id, guild_id=guild_id).get_partial_message(message_id)

class Null:
    pass

AnyValue = str | float | discord.Object | discord.PartialMessage | discord.PartialEmoji | datetime.datetime | bool | Null

class BotChitter(commands.Cog):
    def __init__(self, bot: OliviaBot):
        self.bot = bot
        self.bot_chitter_id = self.bot.bot_chitter_id

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
            return Null(), string[1:]

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
        return results

    def escape_string(self, string: str) -> str:
        return string.translate({
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

    def serialize_generic_row(self, items: list[AnyValue]) -> str:
        '''This is meant to be used for rows parsed with parse_generic_row.
        For rows with custom transformers, it 
        '''
        parts: list[str] = []
        for item in items:
            match item:
                case str():
                    parts.append(f'``"{self.escape_string(item)}"``')
                case bool(): # this needs to be before the int() case, due to:
                    parts.append("❌✅"[item])
                case float() | int(): # note: seems like the `float` in the type alias actually desugared to `float | int`
                    parts.append(str(item))
                case discord.Object():
                    if item.type == discord.abc.GuildChannel:
                        parts.append(f"<#{item.id}>")
                    elif item.type == discord.User:
                        parts.append(f"<@{item.id}>")
                    elif item.type == discord.Role:
                        parts.append(f"<@&{item.id}>")
                    else:
                        raise RuntimeError("unreachable")
                case discord.PartialMessage():
                    parts.append(item.jump_url)
                case discord.PartialEmoji():
                    parts.append(str(item))
                case datetime.datetime():
                    parts.append(discord.utils.format_dt(item))
                case Null():
                    parts.append("🦖")

        return " ".join(parts)


    @commands.is_owner()
    @commands.group(invoke_without_command=True)
    async def table(self, ctx: Context):
        '''Administrative commands for handling #bot-chitter tables'''
        # TODO

    @commands.is_owner()
    @commands.command()
    async def refresh(self, ctx: Context, table: str):
        '''Fetches all the data for the given table, accounting for any newly defined handlers'''
        # TODO

async def setup(bot: OliviaBot):
    await bot.add_cog(BotChitter(bot))

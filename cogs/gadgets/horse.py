from __future__ import annotations

import re

import discord
from discord import app_commands
from discord.ext import commands

from bot import Context, Cog

mapping = {
    "g": "🐴",
    "m": "🐑",
    "i": "<:pleading:1133073270304931980>",
    "l": "🦔",
    "f": "🦊",
    "a": "<:Blobhaj:1133053397940052071>",
    "b": "🐇",
    ":": "🤓",
    "d": "🐬",
}
cased = mapping | {
    c.upper(): emoji for c, emoji in mapping.items() if 'a' <= c <= 'z'
}
pattern = re.compile(r"<:\w+:\d+>|" + "|".join(re.escape(c) for c in mapping))

unmapping = {
    emoji: c for c, emoji in mapping.items()
}
alted = unmapping | {
    "🐎": "g",
    "🥺": "i",
    "🦈": "a",
}
unpattern = re.compile("|".join(re.escape(emoji) for emoji in alted))

def horsify(text: str):
    # leave custom emojis as they are
    return re.sub(pattern, lambda match: match.group() if match.group().startswith("<:") else cased[match.group()], text) or "\u200b"

def unhorsify(text: str):
    # we don't want to recurse e.g. <:plead<:pleading:1133073270304931980>ng:1133073270304931980>
    return re.sub(unpattern, lambda match: alted[match.group()], text) or "\u200b"

def get_reply_content(ctx: Context):
    ref = ctx.message.reference
    if ref is not None:
        if isinstance(ref.resolved, discord.Message):
            return ref.resolved.content

class Horse(Cog):
    async def horse_help(self, ctx: Context):
        fmt = "\n".join([f"{emoji}: `{c}`" for emoji, c in unmapping.items()])
        await ctx.send(f"horse dictionary:\n{fmt}")

    async def horse_cog_load(self):
        self.bot.tree.add_command(horse_menu)
        self.bot.tree.add_command(unhorse_menu)

    @commands.command()
    async def horse(self, ctx: Context, *, text: str | None = None):
        """Translates a message into 🐴
        
        Parameters
        -----------
        text: str | None
            The text / reply to be translated.
        """
        if text is None:
            text = get_reply_content(ctx)
        if text is None:
            return await self.horse_help(ctx)
        await ctx.send(horsify(text))

    @commands.command()
    async def unhorse(self, ctx: Context, *, text: str | None = None):
        """Translates a 🐴 message back to normal
        
        Parameters
        -----------
        text: str | None
            The text / reply to be translated.
        """
        if text is None:
            text = get_reply_content(ctx)
        if text is None:
            return await self.horse_help(ctx)
        await ctx.send(unhorsify(text))

@app_commands.context_menu(name = "🐴 Horse")
async def horse_menu(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_message(horsify(message.content), ephemeral=True)

@app_commands.context_menu(name = "🐴 Unhorse")
async def unhorse_menu(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_message(unhorsify(message.content), ephemeral=True)

from __future__ import annotations
import re

import discord
from discord.ext import commands

from bot import Context, Cog, OliviaBot, qwd_only

class QwdieConverter(commands.Converter[discord.User]):
    async def convert(self, ctx: commands.Context[OliviaBot], argument: str):
        try:
            return await commands.UserConverter().convert(ctx, argument)
        except commands.MemberNotFound:
            # try again
            argument = argument.lower()
        try:
            return await commands.UserConverter().convert(ctx, argument)
        except commands.MemberNotFound:
            # todo add aliases (i'd copy from esobot but that's gpl3)
            raise

class Swish(Cog):
    @qwd_only()
    @commands.command()
    async def swish(
        self,
        ctx: Context,
        user: discord.User = commands.parameter(converter=QwdieConverter),
        items: str = commands.parameter(), # blank param for syntax
        message: str | None = None
        ):
        """swisha mig 100 000 kronor"""
        match = re.match(r"(\d*)(.*)", items)
        assert match
        amount, thing = match.groups()
        if not amount:
            amount = "1"
        await ctx.send(
            f"✅ Swished **{amount} {thing}** to {user.mention}! 🌀**",
            allowed_mentions=discord.AllowedMentions.none()
        )
        if message is None:
            await user.send(f"🌀 Received **{amount} {thing}** from {ctx.author}!")
        else:
            await user.send(f"🌀 Received **{amount} {thing}** from {ctx.author} with message:\n>>> {message}")

from __future__ import annotations
import re

import discord
from discord.ext import commands

from bot import Context, Cog, qwd_only


class Swish(Cog):
    @qwd_only()
    @commands.command()
    async def swish(self, ctx: Context, user: discord.Member | discord.User, items: str, message: str | None = None):
        """swish mig 100 000 kronor"""
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
        
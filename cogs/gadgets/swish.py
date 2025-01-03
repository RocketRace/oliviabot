from __future__ import annotations
import re

import discord
from discord.ext import commands

from bot import Context, Cog, OliviaBot, qwd_only

class QwdieConverter(commands.Converter[discord.Member | discord.User]):
    async def convert(self, ctx: commands.Context[OliviaBot], argument: str):
        try:
            return await commands.MemberConverter().convert(ctx, argument)
        except commands.MemberNotFound:
            # try again with some lax
            result = discord.utils.find(
                lambda user: user.name.lower() == argument.lower(),
                ctx.bot.users
            )
            if result is not None:
                return result
            result = discord.utils.find(
                lambda user: user.global_name and user.global_name.lower() == argument.lower(),
                ctx.bot.users
            )
            if result is not None:
                return result
            raise

class Swish(Cog):
    @qwd_only()
    @commands.command()
    async def swish(
        self,
        ctx: Context,
        user: discord.Member | discord.User = commands.parameter(converter=QwdieConverter),
        items: str = commands.parameter(), # blank param for syntax
        *,
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
            await user.send(f"🌀 Received **{amount} {thing}** from {ctx.author.mention} ({ctx.message.jump_url})!")
        else:
            await user.send(f"🌀 Received **{amount} {thing}** from {ctx.author.mention} ({ctx.message.jump_url}) with message:\n>>> {message}")

from __future__ import annotations
import re

import discord
from discord.ext import commands

from bot import Context, Cog, QwdieConverter

class Swish(Cog):
    @commands.command()
    async def swish(
        self,
        ctx: Context,
        user: discord.Member | discord.User = commands.parameter(converter=QwdieConverter),
        items: str = commands.parameter(), # blank param for syntax
        *,
        message: str | None = None
    ):
        """swisha mig 100 000 kronor
        
        Parameters
        -----------
        user: discord.Member
            Who to send to?
        items: str
            What to send?
        message: str | None
            Optional message :)
        """
        match = re.match(r"([-+]?\d*(?:\.\d+)?)\s*(.*)", items)
        assert match
        amount, thing = match.groups()
        if not amount:
            amount = "1"
        if not thing:
            thing = "1"
        
        if message is None:
            sender = f"✅ Swished **{amount} {thing}** to {user.mention}! 🌀"
            sendee = f"🌀 Received **{amount} {thing}** from {ctx.author.mention}! ({ctx.message.jump_url})"
        else:
            sender = f"✅ Swished **{amount} {thing}** to {user.mention}! 🌀\n>>> {message}"
            sendee = f"🌀 Received **{amount} {thing}** from {ctx.author.mention} ({ctx.message.jump_url}) with message:\n>>> {message}"

        await ctx.send(
            sender,
            allowed_mentions=discord.AllowedMentions.none()
        )
        if user.id != ctx.me.id and not user.bot:
            await user.send(sendee)
    
    @swish.error
    async def swish_error(self, ctx: Context, error: commands.CommandError):
        match error:
            case commands.MemberNotFound():
                await ctx.send("Swish failed... recepient not found! :(")
                ctx.error_handled = True
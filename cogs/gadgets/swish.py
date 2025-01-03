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
            # i'd copy aliases from esobot but i'm lazy and also gpl3

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

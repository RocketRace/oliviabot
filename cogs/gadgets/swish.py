from __future__ import annotations
import re

import discord
from discord.ext import commands

from bot import Context, Cog
from qwd import QwdieConverter, AnyUser

class Swish(Cog):
    @commands.command()
    async def swish(
        self,
        ctx: Context,
        user: AnyUser = commands.parameter(converter=QwdieConverter),
        items: str = commands.parameter(), # blank param for syntax
        first_word_of_message_or_items_it_depends_on_context: str | None = None,
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
            if first_word_of_message_or_items_it_depends_on_context:
                thing = first_word_of_message_or_items_it_depends_on_context
                first_word_of_message_or_items_it_depends_on_context = None
            else:
                thing = "1"
        six_seven = amount in {"67", "6.7", "+67", "+6.7"} or (amount in {"6", "+6"} and thing == "7")
        anti_six_seven = amount in {"-67", "-6.7"} or (amount == "-6" and thing == "7")
        attachment1 = discord.File("67.png") if six_seven else discord.File("-67.png") if anti_six_seven else None
        attachment2 = discord.File("67.png") if six_seven else discord.File("-67.png") if anti_six_seven else None
        
        if first_word_of_message_or_items_it_depends_on_context:
            message = (first_word_of_message_or_items_it_depends_on_context + " " + (message or "")).strip()

        if isinstance(ctx.channel, discord.DMChannel):
            source = ""
        else:
            source = f" ({ctx.message.jump_url}))"

        if not message:
            sender = f"✅ Swished **{amount} {thing}** to {user.mention}! 🌀"
            sendee = f"🌀 Received **{amount} {thing}** from {ctx.author.mention}!{source}"
        else:
            sender = f"✅ Swished **{amount} {thing}** to {user.mention}! 🌀\n>>> {message}"
            sendee = f"🌀 Received **{amount} {thing}** from {ctx.author.mention}{source} with message:\n>>> {message}"

        await ctx.send(
            sender,
            allowed_mentions=discord.AllowedMentions.none(),
            file=attachment1,
        )
        if not user.bot and not isinstance(user, discord.ClientUser):
            await user.send(content=sendee, files=[attachment2] if attachment2 is not None else [])
    
    @swish.error
    async def swish_error(self, ctx: Context, error: commands.CommandError):
        match error:
            case commands.MemberNotFound():
                await ctx.send("Swish failed... recepient not found! :(")
                ctx.error_handled = True
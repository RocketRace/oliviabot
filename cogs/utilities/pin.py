from __future__ import annotations
import random

import discord
from discord.ext import commands

from bot import Context, Cog

def default_message_target(ctx: Context):
    if ctx.message.reference is None:
        return None
    resolved = ctx.message.reference.resolved
    if not isinstance(resolved, discord.Message):
        return None
    return resolved

class Pin(commands.Cog):
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def pin(
        self,
        ctx: Context,
        msg: discord.Message | None = commands.parameter(default = default_message_target)
    ):
        """Pins a message to the current channel.
        
        Parameters
        -----------
        msg: discord.Message
            Reply or message link to pin
        """
        if msg is None:
            return await ctx.send("I need a valid message target to pin")
        await msg.pin(reason=f"+pin by {ctx.author}")
        pins = ["📌", "📍", "🧷", "🎳"]
        pin = random.choice(pins)
        result = await ctx.send(f"{pin} {msg.jump_url} (<loading> / 50 pins)")
        all_pins = len(await ctx.channel.pins())
        await result.edit(content=f"{pin} {msg.jump_url} ({all_pins} / 50 pins)")

    @pin.error
    async def pin_error(self, ctx: Context, error: commands.CommandError):
        match error:
            case commands.CommandInvokeError(original=discord.HTTPException()):
                all_pins = len(await ctx.channel.pins())
                if all_pins == 50:
                    await ctx.send("I couldn't pin that message. There's already 50 here.")
                else:
                    await ctx.send("I couldn't pin that message -- this is probably a random error, so try again")

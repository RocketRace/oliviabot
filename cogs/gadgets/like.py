from __future__ import annotations

import asyncio
import datetime
import random
import re

import discord
from discord.ext import commands

from bot import Context, Cog


class Like(Cog):
    pattern = re.compile(r"\blike$")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.pattern.search(message.content):
            return
        active_after = await self.like_enabled_after(message.author.id)
        now = datetime.datetime.now()
        if now > active_after:
            await asyncio.sleep(random.random())
            await message.add_reaction("\N{THUMBS UP SIGN}")

    async def like_enabled_after(self, user_id: int):
        async with self.bot.cursor() as cur:
            await cur.execute(
                "SELECT enabled_after FROM likers WHERE user_id = ?;",
                [user_id],
            )
            result = await cur.fetchone()
        if not result:
            return datetime.datetime.max
        return datetime.datetime.fromtimestamp(result[0])

    async def set_like_enabled_after(self, user_id: int, dt: datetime.datetime):
        async with self.bot.cursor() as cur:
            await cur.execute(
                """INSERT INTO likers(user_id, enabled_after) VALUES(?, ?)
                ON CONFLICT(user_id) DO
                UPDATE SET enabled_after=excluded.enabled_after;
                """,
                [user_id, dt.timestamp()],
            )

    async def like_status(self, ctx: Context):
        active_after = await self.like_enabled_after(ctx.author.id)
        now = datetime.datetime.now()
        if active_after == datetime.datetime.max:
            status = "not enabled"
        elif now > active_after:
            status = "enabled"
        else:
            timestring = discord.utils.format_dt(active_after, "R")
            status = f"enabled but chilling, back {timestring}"
        return status

    @commands.group(invoke_without_command=True)
    async def like(self, ctx: Context):
        """auto\N{THUMBS UP SIGN} messages that end with "like"

        Run this command with no arguments to see your current settings.
        """
        status = await self.like_status(ctx)
        await ctx.message.add_reaction("\N{THUMBS UP SIGN}")
        await ctx.send(
            f"Auto\N{THUMBS UP SIGN}ing is {status}. "
            "You can enable or disable it using `+like enable` or `+like disable`."
        )

    @like.command(name="enable")
    async def enable_like(self, ctx: Context):
        """Enable auto\N{THUMBS UP SIGN}ing"""
        status = await self.like_status(ctx)
        now = datetime.datetime.now(datetime.UTC)
        await self.set_like_enabled_after(ctx.author.id, now)
        await ctx.message.add_reaction("\N{THUMBS UP SIGN}")
        await ctx.send(
            f"You have enabled auto\N{THUMBS UP SIGN}ing (previously {status})"
        )

    @like.command(name="disable")
    async def disable_like(self, ctx: Context):
        """Disable auto\N{THUMBS UP SIGN}ing"""
        status = await self.like_status(ctx)
        async with ctx.cursor() as cur:
            await cur.execute(
                """DELETE FROM likers WHERE user_id = ?;""", [ctx.author.id]
            )
        await ctx.message.add_reaction("\N{THUMBS UP SIGN}")
        await ctx.send(
            f"You have disabled auto\N{THUMBS UP SIGN}ing (previously {status})"
        )

    @like.command()
    async def chill(self, ctx: Context):
        """Chill out my auto\N{THUMBS UP SIGN}ing for a few hours B)"""
        active_after = await self.like_enabled_after(ctx.author.id)
        if active_after == datetime.datetime.max:
            return await ctx.send("I'm already chilling for you B)")

        now = datetime.datetime.now()
        if now >= active_after:
            hours = random.randint(1, 24)
            dt = ctx.message.created_at + datetime.timedelta(hours=hours)
            await self.set_like_enabled_after(ctx.author.id, dt)
            timestring = discord.utils.format_dt(dt, "R")
            await ctx.send(f"Okay then, I'll be back {timestring} B)")
        else:
            timestring = discord.utils.format_dt(active_after, "R")
            await ctx.send(f"I'm already chilling, I'll be back {timestring} B)")

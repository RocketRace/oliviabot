from __future__ import annotations
import math
from typing import Literal

import discord
from discord.ext import commands

from bot import Context, Cog

class Threads(commands.Cog):
    @commands.command()
    @commands.guild_only()
    async def threads(self, ctx: Context, mode: Literal["recent", "popular", "popular_db"] = "recent", limit: int | Literal["all"] = 20):
        """Shows a list of the threads in the server.
        
        Parameters
        -----------
        mode: Literal["recent", "popular"] = "popular"
            Either "recent" or "popular",
            sorting the list by most recent / most total activity
        limit: int | Literal["all"]
            How many threads to show (default: 20).
            Use "all" to show all threads.
        """
        assert ctx.guild
        threads = [
            t for t in ctx.guild.threads 
            if not t.is_private() and not t.locked and not t.archived and t.parent and t.parent.name != "cw"
        ]
        if not threads:
            await ctx.reply("no public threads!")
        limit_num = len(threads) if limit == "all" else limit

        if mode == "recent":
            threads.sort(
                key=lambda t: discord.utils.snowflake_time(t.last_message_id or 0),
                reverse=True
            )
            await ctx.reply(
                f"{limit} recently active threads:\n"
                + "\n".join(
                    f"{t.mention}: {discord.utils.format_dt(discord.utils.snowflake_time(t.last_message_id or 0), 'R')}"
                    for t in threads[:limit_num]
                ))
        else:
            threads.sort(key=lambda t: t.message_count, reverse=True)

            def fmt(t: discord.Thread):
                reference_signal = threads[0].message_count
                if mode == "popular":
                    return f"{t.mention}: {t.message_count} messages"
                elif mode == "popular_db":
                    db = 10 * math.log10(t.message_count / reference_signal)
                    return f"{t.mention}: {db:.3}dB messages"
                else:
                    raise RuntimeError("invalid mode")

            await ctx.reply(
                f"{limit} popular threads:\n"
                + "\n".join(fmt(t) for t in threads[:limit_num])
            )

from __future__ import annotations
from typing import Literal

import discord
from discord.ext import commands

from bot import Context, Cog

class Marbles(Cog):
    @commands.command()
    async def hello(self, ctx: Context):
        """Hi!"""
        await ctx.send(f"hi! I'm {ctx.me}!")

    @commands.command()
    async def howdy(self, ctx: Context):
        """Howdy pardner"""
        await ctx.send(f"howdy to you too! I'm {ctx.me.display_name} 🤠")
    
    @commands.command()
    @commands.guild_only()
    async def threads(self, ctx: Context, mode: Literal["recent", "popular"] = "popular"):
        """Shows a list of the threads in the server.
        
        Parameters
        -----------
        mode: "recent" | "popular" = "popular"
            either "recent" or "popular",
            sorting the list by most recent / most total activity
        """
        assert ctx.guild
        threads = [
            t for t in ctx.guild.threads 
            if t.invitable and not t.locked and not t.archived and t.parent and t.parent.name != "cw"
        ]
        threads.sort(
            key=lambda t: discord.utils.snowflake_time(t.last_message_id or 0) if mode == "recent" else t.message_count,
            reverse=True
        )
        if not threads:
            await ctx.reply("no threads!")
        else:
            await ctx.reply(f"{mode} threads:\n" + "\n".join(t.mention for t in threads))

    async def change_nickname(self, ctx: Context):
        automated = [
            "\N{COMBINING LATIN SMALL LETTER A}",
            "\N{COMBINING LATIN SMALL LETTER U}",
            "\N{COMBINING LATIN SMALL LETTER T}",
            "\N{COMBINING LATIN SMALL LETTER O}",
            "\N{COMBINING LATIN SMALL LETTER M}",
            "\N{COMBINING LATIN SMALL LETTER A}",
            "\N{COMBINING LATIN SMALL LETTER T}",
            "\N{COMBINING LATIN SMALL LETTER E}",
            "\N{COMBINING LATIN SMALL LETTER D}",
        ]

        assert isinstance(ctx.author, discord.Member)
        assert isinstance(ctx.me, discord.Member)

        segments = ctx.author.display_name.split(" ")
        for i, segment in enumerate(segments):
            if len(segment) >= 9:
                segments[i] = segment[:-9] + "".join(
                    a + b for a, b in zip(segment[-9:], automated)
                )
                break
        else:
            for i, segment in enumerate(segments):
                if len(segment) >= 4:
                    segments[i] = segment[:-4] + "".join(
                        a + b for a, b in zip(segment[-4:], automated)
                    )
                    break
            else:
                return await ctx.send("the nickname too short for my taste")

        nick = " ".join(segments)
        if len(nick) > 32:
            return await ctx.send("that nikcname is too long! it & my personal touch can't combined be more than 32 characters")
        await ctx.me.edit(nick=nick)
        await ctx.ack()

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def nick(self, ctx: Context):
        """Update my nickname"""
        await self.change_nickname(ctx)
    
    @nick.error
    async def nick_error(self, ctx: Context, error: commands.CommandError):
        match error:
            case commands.NotOwner():
                await ctx.send("well you're not olivia... but I like you so I'll do it :)")
                await self.change_nickname(ctx)
                ctx.error_handled = True

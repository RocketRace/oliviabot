from __future__ import annotations

import random

from discord.ext import commands

from bot import Context, Cog


class Louna(Cog):
    @commands.group(invoke_without_command=True)
    async def louna(self, ctx: Context):
        """l\u200bouna"""
        emojis = self.bot.louna_emojis.copy()
        # secret derachification beam
        if random.random() < 1 / 10:
            emojis.append("<:racher1:1229156537155584102>")
            emojis.append("<:racher4:1229156542381686895>")
            emojis.append("<:euler1:1193568742978883764>")
            emojis.append("<:euler4:1193568751631736873>")
        if random.random() < 1 / 25:
            k = 4
        else:
            k = random.randint(2, 3)
        choices = "".join(random.choices(emojis, k=k))
        await ctx.send(f"l\u200bouna {choices}")
        async with ctx.cursor() as cur:
            await cur.execute(
                """UPDATE params SET louna_command_count = louna_command_count + 1;"""
            )
            await cur.execute(
                """UPDATE params SET louna_emoji_count = louna_emoji_count + ?;""", [k]
            )

    @louna.command()
    async def stats(self, ctx: Context):
        """how many l\u200bouna?"""
        async with ctx.cursor() as cur:
            await cur.execute(
                """SELECT louna_command_count, louna_emoji_count FROM params;"""
            )
            result = await cur.fetchone()
            assert result
            command_count, emoji_count = result

        msg = "\n".join(
            [
                "BORN TO SPAM",
                "WORLD IS A MJAU",
                f"鬼神 Love Em All {command_count}",
                "I am l\u200bouna ^_^",
                f"{emoji_count} MEANINGFUL EMOTICONS",
            ]
        )
        await ctx.send(msg)

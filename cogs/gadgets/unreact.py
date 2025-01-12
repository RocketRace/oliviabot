from __future__ import annotations

import random

from discord.ext import commands

from bot import Context, Cog


class Unreact(Cog):
    @commands.command()
    async def unreact(self, ctx: Context):
        """YOUreact"""
        # fmt: off
        triangle = [
            "🪞", "🪞", "🪞",
            "🪟", "🪟", "🪟",
            "🔎", "🔎", 
            "🥄", "🥄", 
            "🪩", "🪩", 
            "🆔",
        ]
        k = random.choice([
            1, 1, 1,
            2, 2, 2, 2,
            3, 3, 
            4,
        ])
        # fmt: on
        choices = "⚪".join(random.choices(triangle, k=k))
        await ctx.send(f"-# {choices}")

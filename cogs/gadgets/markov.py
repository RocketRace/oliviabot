from __future__ import annotations

import discord
from discord.ext import commands
import numpy as np

from bot import Context, Cog


class Chain(Cog):
    @commands.is_owner()
    # @commands.command()
    async def chain(
        self,
        ctx: Context,
        start: str | None = None,
    ):
        """Generate a random chain of words interactively!

        Parameters
        -----------
        start: str | None
            The first word of the chain
        """
        tokens = [" ", "hello", "world"]
        token_ids = {" ": 0, "hello": 1, "world": 2}
        counts = np.array([[0, 1, 1], [2, 0, 0], [2, 0, 0]])
        weights = counts / counts.T.sum(0)
        await ctx.send("acked")

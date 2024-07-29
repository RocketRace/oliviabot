from __future__ import annotations

import discord
from discord.ext import commands

from bot import Context, Cog


class Chain(Cog):
    async def chain_cog_load(self):
        pass

    @commands.is_owner()
    @commands.hybrid_command()
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

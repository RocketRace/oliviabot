from __future__ import annotations

from discord.ext import commands

from bot import Context, Cog


class Xenia(Cog):
    @commands.command()
    @commands.is_owner()
    async def xeniaclinic(self, ctx: Context, *, operation: str):
        pass

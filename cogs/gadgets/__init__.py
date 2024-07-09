from __future__ import annotations


from bot import OliviaBot
from cogs.gadgets.louna import Louna
from cogs.gadgets.neofetch import Neofetch
from cogs.gadgets.vore import Vore


class Gadgets(Louna, Neofetch, Vore):
    """Various gadgets and gizmos"""

    def __init__(self, bot: OliviaBot):
        self.bot = bot

    async def cog_load(self):
        await self.neofetch_cog_load()


async def setup(bot: OliviaBot):
    await bot.add_cog(Gadgets(bot))

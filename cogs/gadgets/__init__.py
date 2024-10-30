from __future__ import annotations


from bot import OliviaBot
from .like import Like
from .louna import Louna
from .neofetch import Neofetch
from .vore import Vore
from .markov import Chain
from .unreact import Unreact
from .horse import Horse


class Gadgets(Louna, Neofetch, Vore, Like, Chain, Unreact, Horse):
    """Various gadgets and gizmos"""

    def __init__(self, bot: OliviaBot):
        self.bot = bot

    async def cog_load(self):
        await self.neofetch_cog_load()
        await self.chain_cog_load()
        await self.horse_cog_load()


async def setup(bot: OliviaBot):
    await bot.add_cog(Gadgets(bot))

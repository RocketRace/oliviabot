from __future__ import annotations

from bot import OliviaBot
from .alias import Alias
from .admin import Admin
from .info import Info
from .marbles import Marbles

class Meta(Alias, Admin, Info, Marbles):
    """Commands related to the behavior of the bot itself"""

    def __init__(self, bot: OliviaBot):
        self.bot = bot

    async def cog_load(self):
        await self.info_cog_load()
    
    async def cog_unload(self) -> None:
        pass

async def setup(bot: OliviaBot):
    await bot.add_cog(Meta(bot))

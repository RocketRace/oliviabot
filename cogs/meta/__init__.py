from __future__ import annotations

from bot import OliviaBot
from .alias import Alias
from .admin import Admin
from .info import Info
from .marbles import Marbles
from .ticker import Ticker
from .proxy import Proxy

class Meta(Alias, Admin, Info, Marbles, Ticker, Proxy):
    """Commands related to the behavior of the bot itself"""
    def __init__(self, bot: OliviaBot):
        self.bot = bot

async def setup(bot: OliviaBot):
    await bot.add_cog(Meta(bot))

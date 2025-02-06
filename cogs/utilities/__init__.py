from __future__ import annotations

from bot import OliviaBot
from .pin import Pin
from .threads import Threads

class Utilities(Pin, Threads):
    """Useful commands for daily use in a server"""
    def __init__(self, bot: OliviaBot):
        self.bot = bot

async def setup(bot: OliviaBot):
    await bot.add_cog(Utilities(bot))

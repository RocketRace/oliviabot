from __future__ import annotations


from bot import OliviaBot
from .like import Like
from .louna import Louna
from .neofetch import Neofetch
from .vore import Vore
from .markov import Chain
from .unreact import Unreact
from .horse import Horse
from .tempemoji import TempEmoji
from .swish import Swish


class Gadgets(Louna, Neofetch, Vore, Like, Chain, Unreact, Horse, TempEmoji, Swish):
    """Various gadgets and gizmos"""
    def __init__(self, bot: OliviaBot):
        self.bot = bot

async def setup(bot: OliviaBot):
    await bot.add_cog(Gadgets(bot))

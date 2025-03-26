from __future__ import annotations

import discord
from discord.ext import commands

from bot import Context, Cog

class Stickerboard(Cog):    
    @commands.group(invoke_without_command=True, aliases=["sticker"], enabled=False)
    async def stickerboard(self, ctx: Context):
        '''View the collaborative sticker board and leave your own stickers!'''


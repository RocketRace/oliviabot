from __future__ import annotations

import discord
from discord.ext import commands

from bot import Context, Cog

class Stack(Cog):
    @commands.command(enabled=False)
    async def push(self, ctx: Context):
        '''pass'''
    

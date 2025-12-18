from __future__ import annotations
import re

import discord
from discord.ext import commands

from bot import Context, Cog

class Mjau(Cog):
    @commands.Cog.listener("on_message")
    async def mjau_detector(self, msg: discord.Message):
        if msg.content.startswith("+"):
            for mjau in self.mjau_set:
                print(mjau)
                match = re.match(f"\\+{re.escape(mjau)}\b(.*)", msg.content)
                if match:
                    msg.content = f"+mjau{match.group(1)}"
                    return await self.bot.process_commands(msg)
                match = re.match(f"\\+new{re.escape(mjau)}\b(.*)", msg.content)
                if match:
                    msg.content = f"+newmjau{match.group(1)}"
                    return await self.bot.process_commands(msg)
                match = re.match(f"\\+no{re.escape(mjau)}\b(.*)", msg.content)
                if match:
                    msg.content = f"+nomjau{match.group(1)}"
                    return await self.bot.process_commands(msg)
                match = re.match(f"\\+{re.escape(mjau)}s\b(.*)", msg.content)
                if match:
                    msg.content = f"+mjaus{match.group(1)}"
                    return await self.bot.process_commands(msg)

    @commands.command()
    async def mjau(self, ctx: Context):
        """:mjau:
        """
        await ctx.send(f"<a:meow:1236434880238456933>")
    
    @commands.command()
    async def mjaus(self, ctx: Context):
        """List of mjaus
        """
        await ctx.send(
            f"list of {ctx.invoked_with} <a:mjau:1236434880238456933>\n" + 
            "\n".join(f"- {mjau} <a:meow:1236434880238456933>" for mjau in ["mjau", *self.mjau_set])
        )

    async def cog_load(self):
        await super().cog_load()
        async with self.bot.cursor() as cur:
            await cur.execute("""SELECT * FROM mjaus;""")
            results = [str(row[0]) for row in await cur.fetchall()]
            self.mjau_set = set(results)

    @commands.command()
    async def newmjau(self, ctx: Context, mjau: str):
        """Define a new mjau
        
        Parameters
        -----------
        mjau: str
            the new mjau
        """
        async with ctx.cursor() as cur:
            await cur.execute("""INSERT INTO mjaus VALUES(?);""", [mjau])
            self.mjau_set.add(mjau)
        await ctx.send(f"+{mjau} <a:meow:1236434880238456933>")
    
    @commands.command()
    @commands.is_owner()
    async def nomjau(self, ctx: Context, mjau: str):
        """Remove an old mjau
        
        Parameters
        -----------
        mjau: str
            the old mjau
        """
        async with ctx.cursor() as cur:
            await cur.execute("""DELETE FROM mjaus WHERE mjau = ?;""", [mjau])
            self.mjau_set.remove(mjau)
        await ctx.send(f"<:nomeow:1309094454904487966>")
    

from __future__ import annotations

import discord
from discord.ext import commands

from bot import Context, Cog

class Mjau(Cog):
    def set_mjauers(self, cmd: commands.Command, pattern: str, mjaus: list[str]):
        cmd.aliases = [pattern.format(mjau) for mjau in mjaus]
    def append_mjauer(self, cmd: commands.Command, pattern: str, mjau: str):
        cmd.aliases = [*cmd.aliases, pattern.format(mjau)]
    def remove_mjauer(self, cmd: commands.Command, pattern: str, mjau: str):
        cmd.aliases = [mjauu for mjauu in cmd.aliases if mjauu != pattern.format(mjau)]

    @commands.command()
    async def mjau(self, ctx: Context):
        """:mjau:
        """
        await ctx.send(f"<a:{ctx.invoked_with}:1236434880238456933>")
    
    @commands.command()
    async def mjaus(self, ctx: Context):
        """List of mjaus
        """
        await ctx.send(
            "list of mjaus <a:mjau:1236434880238456933>\n" + 
            "\n".join(f"- {mjau} <a:{mjau}:1236434880238456933>" for mjau in ["mjau", *self.mjau.aliases])
        )

    async def cog_load(self):
        await super().cog_load()
        async with self.bot.cursor() as cur:
            await cur.execute("""SELECT * FROM mjaus;""")
            results = [str(row[0]) for row in await cur.fetchall()]
            self.set_mjauers(self.mjau, "{}", results)
            self.set_mjauers(self.newmjau, "new{}", results)
            self.set_mjauers(self.nomjau, "no{}", results)
            self.set_mjauers(self.mjaus, "{}s", results)

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
            self.append_mjauer(self.mjau, "{}", mjau)
            self.append_mjauer(self.newmjau, "new{}", mjau)
            self.append_mjauer(self.nomjau, "no{}", mjau)
            self.append_mjauer(self.mjaus, "{}s", mjau)
        await ctx.send(f"+{mjau} <a:{mjau}:1236434880238456933>")
    
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
            self.remove_mjauer(self.mjau, "{}", mjau)
            self.remove_mjauer(self.newmjau, "new{}", mjau)
            self.remove_mjauer(self.nomjau, "no{}", mjau)
            self.remove_mjauer(self.mjaus, "{}s", mjau)
        await ctx.send(f"<:nomeow:1309094454904487966>")
    

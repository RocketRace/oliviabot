from __future__ import annotations


import discord
from discord.ext import commands

from bot import Context, Cog, QwdieConverter

class HelpCommand(commands.DefaultHelpCommand):
    async def send_pages(self) -> None:
        destination = self.get_destination()
        for page in self.paginator.pages:
            # antihighlightification
            page = page.replace("louna", "l\u200bouna")
            await destination.send(page)

class Admin(Cog):
    async def admin_cog_load(self):
        self.original_help = self.bot.help_command
        self.bot.help_command = HelpCommand()
        self.bot.help_command.cog = self
    
    async def cog_unload(self):
        self.bot.help_command = self.original_help

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx: Context):
        """Reload cogs"""
        for extension in self.bot.activated_extensions:
            await self.bot.reload_extension(extension)
        await ctx.ack("Loaded all extensions")
    
    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: Context):
        """Sync application commands"""
        await self.bot.tree.sync()
        await ctx.ack()

    @commands.command(aliases=['strql'])
    @commands.is_owner()
    async def sql(self, ctx: Context, *, command: str):
        """Execute SQL commands on the running database
        
        Parameters
        -----------
        command: str
            The SQL query to execute
        """
        async with ctx.cursor() as cur:
            await cur.execute(command)
            return await ctx.send(
                "\n".join(["".join([str(item) for item in row]) if ctx.invoked_with == "strql" else str(row) for row in await cur.fetchall()])[:2000]
                or "<no result>"
            )

    @commands.command()
    @commands.is_owner()
    async def oliviafy(self, ctx: Context, user: discord.User = commands.parameter(converter=QwdieConverter)):
        '''You too can become olivia
        
        Parameters
        -----------
        user: discord.User
            The user to oliviafy
        '''
        self.bot.owner_ids.add(user.id)
        await ctx.ack(f"{user.mention} hi, olivia")

    @commands.command()
    @commands.is_owner()
    async def unoliviafy(self, ctx: Context, user: discord.User = commands.parameter(converter=QwdieConverter)):
        '''You too can stop becoming olivia
        
        Parameters
        -----------
        user: discord.User
            The user to unoliviafy
        '''
        if user.id == 156021301654454272:
            return await ctx.send("what no I'm not doing that")
        self.bot.owner_ids.remove(user.id)
        await ctx.send(f"{user.mention} bye bye... it was nice knowing you as olivia")

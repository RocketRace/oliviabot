from __future__ import annotations


import discord
from discord.ext import commands

from bot import Context, Cog, QwdieConverter, AnyUser

class Alias(Cog):
    @commands.group(invoke_without_command=True)
    async def alias(self, ctx: Context, alias: str | None = None):
        """See your current aliases
        
        Parameters
        -----------
        alias: str | None = None
            The alias to create (but consider `+alias add` instead)
        """
        if alias:
            return await self.alias_addition(ctx, alias, ctx.author, True)
        aliases = sorted(self.bot.inv_person_aliases.get(ctx.author.id, []))
        if not aliases:
            return await ctx.send("You don't have any aliases set")
        l = "\n".join([f"- {alias}" for alias in aliases])
        return await ctx.send(f"Your aliases:\n{l}")
    
    async def alias_addition(self, ctx: Context, alias: str, user: AnyUser, extra: bool = False):
        alias = alias.lower()
        if alias in self.bot.inv_person_aliases.get(ctx.author.id, []):
            return await ctx.send("already got that one!")
        async with self.bot.cursor() as cur:
            await cur.execute(
                """INSERT INTO person_aliases VALUES(?, ?);""",
                [alias, user.id]
            )
        msg = f"{user.mention} hi {alias} :)"
        if extra:
            msg += "\n-# consider `+alias add` next time"
        await ctx.send(
            msg,
            allowed_mentions=discord.AllowedMentions.none()
        )
        await self.bot.refresh_aliases()

    async def alias_deletion(self, ctx: Context, alias: str, user: AnyUser):
        alias = alias.lower()
        if alias not in self.bot.inv_person_aliases.get(ctx.author.id, []):
            return await ctx.send("don't have that one!")
        async with self.bot.cursor() as cur:
            await cur.execute(
                """DELETE FROM person_aliases WHERE alias = ? AND id = ?;""",
                [alias, user.id]
            )
        await ctx.send(
            f"{alias} no more :)",
            allowed_mentions=discord.AllowedMentions.none()
        )
        await self.bot.refresh_aliases()

    @alias.command(name="add", aliases=["new"])
    async def add_alias(self, ctx: Context, alias: str):
        """Add a new alias for yourself
        
        Parameters
        -----------
        alias: str
            The alias to create
        """
        await self.alias_addition(ctx, alias, ctx.author)

    @alias.command(name="delete", aliases=["remove"])
    async def delete_alias(self, ctx: Context, alias: str):
        """Delete one of your aliases
        
        Parameters
        -----------
        alias: str
            The alias to delete
        """
        await self.alias_deletion(ctx, alias, ctx.author)

    @alias.group(name="override", invoke_without_command=True)
    @commands.is_owner()
    async def alias_override(self, ctx: Context):
        """Olivia can override aliases"""
        await ctx.send_help("alias override")

    @alias_override.command(name="add", aliases=["new"])
    @commands.is_owner()
    async def add_override_alias(self, ctx: Context, alias: str, *, user: AnyUser = commands.parameter(converter=QwdieConverter)):
        """Add a new person alias
        
        Parameters
        -----------
        alias: str
            The alias to create
        user: AnyUser
            The person to link it to
        """
        await self.alias_addition(ctx, alias, user)
    
    @alias_override.command(name="delete", aliases=["remove"])
    @commands.is_owner()
    async def delete_override_alias(self, ctx: Context, alias: str, *, user: AnyUser = commands.parameter(converter=QwdieConverter)):
        """Delete a person alias
        
        Parameters
        -----------
        alias: str
            The alias to delete
        user: AnyUser
            The person to delete it from
        """
        await self.alias_deletion(ctx, alias, user)

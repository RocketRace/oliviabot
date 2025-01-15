from __future__ import annotations

from discord.ext import commands

from bot import Context, Cog

class Proxy(Cog):
    @commands.group(invoke_without_command=True)
    async def proxy(self, ctx: Context, value: bool | None = None):
        """Configure this bot to respond to proxy messages.

        Run this command with no arguments to see your current settings.

        Parameters
        -----------
        value: bool | None
            ("enable" / "disable") Whether to enable or disable proxy mode.
        """
        negation = "" if await self.bot.is_proxied(ctx.author) else " not"
        await ctx.send(
            f"You have{negation} enabled proxy mode. "
            "You can enable or disable it using `+proxy enable` or `+proxy disable`."
        )
    
    @proxy.command(name="enable", aliases=["on", "optin"])
    async def proxy_enable(self, ctx: Context):
        negation = "" if await self.bot.is_proxied(ctx.author) else " not"
        async with ctx.cursor() as cur:
            await cur.execute(
                """INSERT OR IGNORE INTO proxiers VALUES(?);""", [ctx.author.id]
            )
        await ctx.send(
            f"You have enabled proxy mode (previously{negation} enabled)"
        )

    @proxy.command(name="disable", aliases=["off", "optout"])
    async def proxy_disable(self, ctx: Context):
        negation = "" if await self.bot.is_proxied(ctx.author) else " not"
        async with ctx.cursor() as cur:
            await cur.execute(
                """DELETE FROM proxiers WHERE user_id = ?;""", [ctx.author.id]
            )
        await ctx.send(
            f"You have disabled proxy mode (previously{negation} enabled)"
        )

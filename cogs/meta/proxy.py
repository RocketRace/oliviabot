from __future__ import annotations

from discord.ext import commands

from bot import Context, Cog

class Proxy(Cog):
    @commands.command()
    async def proxy(self, ctx: Context, value: bool | None = None):
        """Configure this bot to respond to proxy messages.

        Run this command with no arguments to see your current settings.

        Parameters
        -----------
        value: bool | None
            ("enable" / "disable") Whether to enable or disable proxy mode.
        """
        proxied = await self.bot.is_proxied(ctx.author)
        negation = "" if proxied else " not"
        if value is None:
            await ctx.send(
                f"You have{negation} enabled proxy mode. "
                "You can enable or disable it using `+proxy enable` or `+proxy disable`."
            )
        else:
            async with ctx.cursor() as cur:
                if value:
                    await cur.execute(
                        """INSERT OR IGNORE INTO proxiers VALUES(?);""", [ctx.author.id]
                    )
                else:
                    await cur.execute(
                        """DELETE FROM proxiers WHERE user_id = ?;""", [ctx.author.id]
                    )
            action = "enabled" if value else "disabled"
            await ctx.send(
                f"You have {action} proxy mode (previously{negation} enabled)"
            )

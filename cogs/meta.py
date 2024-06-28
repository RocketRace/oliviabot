from discord.ext import commands

from _types import OliviaBot, Context


class Meta(commands.Cog):
    """Commands related to the behavior of the bot itself"""

    @commands.command()
    async def hello(self, ctx: Context):
        await ctx.send(f"Hello! I'm {ctx.me}!")

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx: Context):
        for extension in self.bot.initial_extensions:
            await self.bot.reload_extension(extension)
        await ctx.send("Loaded all extensions")

    def __init__(self, bot: OliviaBot):
        self.bot = bot


async def setup(bot: OliviaBot):
    await bot.add_cog(Meta(bot))

from discord.ext import commands

from _types import OliviaBot


class Context(commands.Context[OliviaBot]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_handled = False


class CustomContext(commands.Cog):
    """Custom context handler, in a cog for easier hot-loading"""

    async def cog_load(self):
        self.bot.ctx_class = Context

    async def cog_unload(self):
        self.bot.ctx_class = commands.Context

    def __init__(self, bot: OliviaBot):
        self.bot = bot


async def setup(bot: OliviaBot):
    await bot.add_cog(CustomContext(bot))

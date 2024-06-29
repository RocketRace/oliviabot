from __future__ import annotations

from typing import TYPE_CHECKING
from discord.ext import commands

# break import cycles by force
type OliviaBotAlias = OliviaBot
if TYPE_CHECKING:
    from _types import OliviaBot


class Context(commands.Context[OliviaBotAlias]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_handled = False


async def setup(bot: OliviaBot):
    bot.ctx_class = Context


async def teardown(bot: OliviaBot):
    bot.ctx_class = commands.Context

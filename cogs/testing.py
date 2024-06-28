import asyncio
import logging
from discord.ext import commands
import discord
import aioconsole
import discord.http

from _types import Context, OliviaBot


class TestContext(Context):
    async def send(self, content: str | None = None, **kwargs):
        if content:
            print("->", content)
        return await super().send(content, **kwargs)


class Testing(commands.Cog):
    """Terminal-based command execution for rapid local testing"""

    async def test_loop(self) -> None:
        while True:
            try:
                line = await aioconsole.ainput("Enter command: ", loop=self.bot.loop)
                _, (_, pending) = await asyncio.gather(
                    # Note: uses undocumented APIs, because we don't need gateway events for the tester
                    self.tester.http.send_message(
                        self.bot.testing_channel_id,
                        params=discord.http.MultipartParameters(
                            {"content": line}, None, None
                        ),
                    ),
                    asyncio.wait(
                        {
                            asyncio.create_task(
                                self.bot.wait_for(
                                    "command_completion",
                                    check=lambda ctx: ctx.author.id
                                    == self.bot.tester_bot_id,
                                )
                            ),
                            asyncio.create_task(
                                self.bot.wait_for(
                                    "command_error",
                                    check=lambda ctx, _: ctx.author.id
                                    == self.bot.tester_bot_id,
                                )
                            ),
                        },
                        timeout=10.0,
                        return_when=asyncio.FIRST_COMPLETED,
                    ),
                )
                if len(pending) == 2:
                    raise asyncio.TimeoutError()
            except asyncio.TimeoutError:
                print("<No response>")
            except Exception:
                logging.exception("Unhandled exception in console loop")
            except asyncio.CancelledError:
                print("<test loop stopped>")
                raise

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id != self.bot.tester_bot_id:
            return

        ctx = await self.bot.get_context(message, cls=TestContext)
        await ctx.reinvoke()

    async def cog_load(self):
        self.tester = discord.Client(intents=discord.Intents.none())
        await self.tester.login(self.bot.tester_bot_token)
        self.task = asyncio.create_task(self.test_loop())

    async def cog_unload(self):
        self.task.cancel()
        await self.tester.close()

    def __init__(self, bot: OliviaBot):
        self.bot = bot


async def setup(bot: OliviaBot):
    await bot.add_cog(Testing(bot))

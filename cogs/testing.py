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


class LogSuppressor:
    def __init__(self):
        self.logger = logging.getLogger("discord")

    def __enter__(self):
        self.old_level = self.logger.level
        self.logger.setLevel(logging.ERROR)

    def __exit__(self, et, ev, tb):
        self.logger.setLevel(self.old_level)


class Testing(commands.Cog):
    """Terminal-based command execution for rapid local testing"""

    async def test_loop(self) -> None:
        while True:
            try:
                line = await aioconsole.ainput("Enter command: ", loop=self.bot.loop)
                # Don't set timeouts, as asyncio.wait won't propagate them anyway
                completion = asyncio.create_task(
                    self.bot.wait_for(
                        "command_completion",
                        check=lambda ctx: ctx.author.id == self.bot.tester_bot_id,
                    ),
                    name="completion",
                )
                error = asyncio.create_task(
                    self.bot.wait_for(
                        "command_error",
                        check=lambda ctx, _: ctx.author.id == self.bot.tester_bot_id,
                    ),
                    name="error",
                )
                any_response = asyncio.create_task(
                    asyncio.wait(
                        [completion, error],
                        timeout=10.0,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                )
                # Note: uses undocumented APIs, because we don't really want gateway events for the tester
                request = self.tester.http.send_message(
                    self.bot.testing_channel_id,
                    params=discord.http.MultipartParameters(
                        {"content": line}, None, None
                    ),
                )
                try:
                    _, (done, pending) = await asyncio.gather(request, any_response)
                except Exception:
                    logging.exception("Unhandled exception in command trigger")
                    any_response.cancel()
                    continue

                for task in pending:
                    task.cancel()
                if done:
                    match done.pop().get_name():
                        case "completion":
                            print("Command succeeded")
                        case "error":
                            print("Command errored")
                else:
                    print("No reponse")

            except asyncio.CancelledError:
                logging.info("Stopping terminal loop")
                raise

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id != self.bot.tester_bot_id:
            return

        ctx = await self.bot.get_context(message, cls=TestContext)
        await self.bot.invoke(ctx)

    async def cog_load(self):
        with LogSuppressor():
            self.tester = discord.Client(intents=discord.Intents.none())
            await self.tester.login(self.bot.tester_bot_token)

        logging.info("Starting terminal loop")
        self.task = asyncio.create_task(self.test_loop())

    async def cog_unload(self):
        self.task.cancel()
        await self.tester.close()

    def __init__(self, bot: OliviaBot):
        self.bot = bot


async def setup(bot: OliviaBot):
    await bot.add_cog(Testing(bot))

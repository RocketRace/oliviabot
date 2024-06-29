import asyncio
from dataclasses import dataclass
import logging
from typing import Any
from discord.ext import commands
import discord
import aioconsole
import discord.http

from _types import Context, OliviaBot


class TestContext(Context):
    async def send(self, content: str | None = None, **kwargs):
        if content:
            print("Out:", content)
        return await super().send(content, **kwargs)


class LogSuppressor:
    def __init__(self):
        self.logger = logging.getLogger("discord")

    def __enter__(self):
        self.old_level = self.logger.level
        self.logger.setLevel(logging.ERROR)

    def __exit__(self, et, ev, tb):
        self.logger.setLevel(self.old_level)


class Terminal(commands.Cog):
    """Terminal-based command execution for rapid local testing"""

    def wait_for_response(self):
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
        return asyncio.create_task(
            asyncio.wait(
                [completion, error],
                timeout=10.0,
                return_when=asyncio.FIRST_COMPLETED,
            )
        )

    def handle_response(
        self,
        done: set[asyncio.Task[Any]],
        pending: set[asyncio.Task[Any]],
        *,
        possibly_skipped: bool,
    ):
        for task in pending:
            task.cancel()
        if done:
            match done.pop().get_name():
                case "completion":
                    print("Command succeeded")
                case "error":
                    print("Command errored")
        elif possibly_skipped:
            print("No reponse (possibly skipped)")
        else:
            print("No reponse")

    async def test_loop(self) -> None:
        if self.bot.terminal_cog_interrupted:
            done, pending = await self.wait_for_response()
            self.handle_response(done, pending, possibly_skipped=True)
            self.bot.terminal_cog_interrupted = False
        while True:
            attempted = False
            try:
                line = await aioconsole.ainput("In: ")
                # Note: uses undocumented APIs, because we don't really want gateway events for the tester
                request = self.tester.http.send_message(
                    self.bot.testing_channel_id,
                    params=discord.http.MultipartParameters(
                        {"content": line}, None, None
                    ),
                )
                response = self.wait_for_response()
                try:
                    attempted = True
                    _, (done, pending) = await asyncio.gather(request, response)
                except Exception:
                    logging.exception("Unhandled exception in command trigger")
                    response.cancel()
                    continue

                self.handle_response(done, pending, possibly_skipped=False)

            except asyncio.CancelledError:
                logging.info("Stopping terminal loop")
                if attempted:
                    self.bot.terminal_cog_interrupted = True
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
    await bot.add_cog(Terminal(bot))

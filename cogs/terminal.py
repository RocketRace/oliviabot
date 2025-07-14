import asyncio
import logging
from typing import Any

from discord.ext import commands
import discord
import aioconsole
import discord.http
import parse_discord
import parse_discord.formatting

from bot import Context, OliviaBot, Cog


def sgr(*ns: int) -> str:
    return f"\x1b[{';'.join(str(n) for n in ns)}m"


def colored(inner: str, *colors: int) -> str:
    return f"{sgr(*colors)}{inner}{sgr(39, 49)}"


def mention(inner: str) -> str:
    return colored(inner, 44, 96)


class TestContext(Context):
    def format_node(self, node: parse_discord.Node) -> str:
        match node:
            case parse_discord.Text():
                return node.text
            case parse_discord.Bold():
                return sgr(1) + self.format_markup(node.inner) + sgr(22)
            case parse_discord.Italic():
                return sgr(3) + self.format_markup(node.inner) + sgr(23)
            case parse_discord.Underline():
                return sgr(4) + self.format_markup(node.inner) + sgr(24)
            case parse_discord.Strikethrough():
                return sgr(9) + self.format_markup(node.inner) + sgr(29)
            case parse_discord.Spoiler():
                return colored(self.format_markup(node.inner), 37, 48, 5, 243)
            case parse_discord.Quote():
                return indent(self.format_markup(node.inner), colored("> ", 37))
            case parse_discord.Header():
                return indent(
                    self.format_markup(node.inner),
                    colored("#" * node.level + " ", 37),
                )
            case parse_discord.List():
                out = []
                if node.start:
                    for i, item in enumerate(node.items):
                        bullet = f"{node.start + i}. "
                        out.append(
                            indent(
                                f"{bullet}{self.format_markup(item)}",
                                " " * len(bullet),
                            )
                        )
                else:
                    for item in node.items:
                        out.append(
                            indent(
                                f"- {self.format_markup( item)}",
                                "  ",
                            )
                        )

                return "\n".join(out)
            case parse_discord.Link():
                text = node.title if node.title else node.display_target
                # hyperlink, limited terminal support
                return f"\x1b[]8;;{node.target}\x1b\\{text}\x1b[]8;;\x1b\\"
            case parse_discord.InlineCode():
                return colored(node.content, 48, 5, 243)
            case parse_discord.Codeblock():
                # TODO
                if node.language:
                    return colored(f"```{node.language}\n{node.content}```", 48, 5, 243)
                else:
                    return colored(f"```\n{node.content}```", 48, 5, 243)
            case parse_discord.UserMention():
                if self.guild:
                    member = self.guild.get_member(node.id)
                    if member:
                        return mention(f"@{member.nick}")
                user = self.bot.get_user(node.id)
                if user:
                    return mention(f"@{user.name}")
                return mention(f"<@{node.id}>")
            case parse_discord.ChannelMention():
                channel = self.bot.get_channel(node.id)
                if channel and isinstance(
                    channel, (discord.abc.GuildChannel, discord.Thread)
                ):
                    return mention(f"#{channel.name}")
                return mention(f"<#{node.id}>")
            case parse_discord.RoleMention():
                if self.guild:
                    role = self.guild.get_role(node.id)
                    if role:
                        name = role.name
                        r, g, b = role.color.to_rgb()
                        return colored(f"@{name}", 38, 2, r, g, b)
                return mention(f"<@&{node.id}>")
            case parse_discord.Everyone():
                return mention("@everyone")
            case parse_discord.Here():
                return mention("@here")
            case parse_discord.CustomEmoji():
                return f":{node.name}:"
            case parse_discord.UnicodeEmoji():
                return node.char
            case parse_discord.Timestamp():
                try:
                    datetime = node.as_datetime()
                    return mention(datetime.strftime("%Y-%m-%d %H:%M:%S"))
                except OverflowError:
                    pass
                if node.format:
                    return mention(f"<t:{node.timestamp}:{node.format}>")
                else:
                    return mention(f"<t:{node.timestamp}>")

            case other:
                return parse_discord.formatting.format_markup(
                    parse_discord.Markup([other])
                )

    def format_markup(self, markup: parse_discord.Markup) -> str:
        formatted = ""
        for node in markup.nodes:
            formatted += self.format_node(node)

        return formatted

    async def send(self, content: str | None = None, **kwargs):
        if content:
            markup = parse_discord.parse(content)
            formatted = self.format_markup(markup)
            print("Out:", formatted)
        return await super().send(content, **kwargs)


class LogSuppressor:
    def __init__(self):
        self.logger = logging.getLogger("discord")

    def __enter__(self):
        self.old_level = self.logger.level
        self.logger.setLevel(logging.ERROR)

    def __exit__(self, et, ev, tb):
        self.logger.setLevel(self.old_level)


def indent(content: str, prefix: str) -> str:
    return "".join(f"{prefix}{line}\n" for line in content.split("\n"))


class Terminal(Cog):
    """Terminal-based command execution for rapid local testing"""

    def __init__(self, bot: OliviaBot):
        self.bot = bot

    async def cog_load(self):
        with LogSuppressor():
            self.tester = discord.Client(intents=discord.Intents.none())
            await self.tester.login(self.bot.tester_bot_token)

        logging.info("Starting terminal loop")
        self.task = asyncio.create_task(self.test_loop())

    async def cog_unload(self):
        self.task.cancel()
        await self.tester.close()

    async def wait_for_response(self):
        try:
            await self.bot.wait_for(
                "command",
                check=lambda ctx: ctx.author.id == self.bot.tester_bot_id,
                timeout=3.0,
            )
        except asyncio.TimeoutError:
            return None
        else:
            print("Ack")
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
            return await asyncio.wait(
                [completion, error],
                timeout=15.0,
                return_when=asyncio.FIRST_COMPLETED,
            )

    def handle_response(
        self,
        response: tuple[set[asyncio.Task[Any]], set[asyncio.Task[Any]]] | None,
        *,
        potentially_skipped: bool = False,
    ):
        if response is None:
            if potentially_skipped:
                print("No response (possibly skipped)")
            else:
                print("Timed out")
            return
        else:
            done, pending = response
        for task in pending:
            task.cancel()
        if done:
            match done.pop().get_name():
                case "completion":
                    print("Command succeeded")
                case "error":
                    print("Command errored")

    async def test_loop(self) -> None:
        if self.bot.terminal_cog_interrupted:
            response = await self.wait_for_response()
            self.handle_response(response, potentially_skipped=True)
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
                    _, resp = await asyncio.gather(request, response)
                except Exception:
                    logging.exception("Unhandled exception in command trigger")
                    continue

                self.handle_response(resp)

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


async def setup(bot: OliviaBot):
    await bot.add_cog(Terminal(bot))

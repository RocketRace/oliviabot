from __future__ import annotations

import asyncio
import csv
import datetime
import io
import itertools
import logging
import random
import re
from typing import Awaitable, Callable, Literal, TypedDict
import discord
from discord.ext import commands
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from bot import OliviaBot, Context, qwd_only


def dedent(s: str) -> str:
    """textwrap.dedent behaves unexpectedly"""

    tucked = False
    if s.startswith("\n"):
        s = s[1:]
        tucked = True

    lines = s.splitlines()

    if not lines:
        return ""

    def width(line: str) -> int:
        width = 0
        while line[width:].startswith(" "):
            width += 1
        return width

    widths = [width(line) for line in lines]

    if widths[0] == 0 and not tucked:
        common_width = min(widths[1:])
        return "\n".join([lines[0], *[line[common_width:] for line in lines[1:]]])
    else:
        common_width = min(widths)
        return "\n".join(line[common_width:] for line in lines)


class Gadgets(commands.Cog):
    """Various gadgets and gizmos"""

    def __init__(self, bot: OliviaBot):
        self.bot = bot

    async def cog_load(self):
        def regexp(pattern: str, string: str) -> bool:
            return re.match(pattern, string) is not None

        await self.bot.db.create_function("regexp", 2, regexp, deterministic=True)
        await self.init_neofetch()
        await self.init_vore()

    @commands.group(invoke_without_command=True)
    async def louna(self, ctx: Context):
        """l\u200bouna"""
        # fmt: off
        emojis = [
            "✂️", "❤️‍🔥", "🌍", "🌚", "🌞", "🌸", "🌺", "🍉", 
            "🍙", "🎺", "🏩", "🏳️‍⚧️", "🏳️‍🌈", "🐀", "🐄", "🐇", 
            "🐈", "🐊", "🐌", "🐐", "🐑", "🐕", "🐖", "🐗", 
            "🐛", "🐝", "🐩", "🐫", "🐴", "🐸", "👄", "👩‍❤️‍💋‍👩", 
            "👩‍💻", "👰‍♀️", "👹", "💅", "💓", "💕", "💖", "💗", 
            "💘", "💝", "💣", "💸", "💹", "📈", "📸", "🔪", 
            "🕊️", "🗿", "🤠", "🤡", "🤩", "🥺", "🦊", "🦌", 
            "🦒", "🦔", "🦕", "🦘", "🦙", "🦝", "🦟", "🦡", 
            "🦢", "🦤", "🦥", "🦩", "🦫", "🦮", "🧘‍♀️", "🧚‍♂️", 
            "🧝‍♀️", "🧠", "🧸", "🪿", "🫒", "🫡", "🫣", "🫵", 
            "😇", "😭", "😳", "😼", "🙏", "🚀", "🚲", "🛀",
            "<:bottomemoji:1163608118375235655>",
            "<:kaboom:1134083088725573743>",
            "<:sus:1133050350832721960>",
            "<:racher3:1229156540477345863>",
            "<:helloboi:1235910150418731101>",
            "<:stimmy:1236300904152563743>",
            "<:t42:1134085866189508608>",
            "<:sillygroove:1134083563957014528>",
        ]
        # fmt: on
        k = random.randint(2, 3)
        choices = "".join(random.choices(emojis, k=k))
        await ctx.send(f"l\u200bouna {choices}")
        async with ctx.bot.db.cursor() as cur:
            await cur.execute(
                """UPDATE params SET louna_command_count = louna_command_count + 1;"""
            )
            await cur.execute(
                """UPDATE params SET louna_emoji_count = louna_emoji_count + ?;""", [k]
            )

    @louna.command()
    async def stats(self, ctx: Context):
        """how many l\u200bouna?"""
        async with ctx.bot.db.cursor() as cur:
            await cur.execute(
                """SELECT louna_command_count, louna_emoji_count FROM params;"""
            )
            result = await cur.fetchone()
            assert result
            command_count, emoji_count = result

        msg = "\n".join(
            [
                "BORN TO SPAM",
                "WORLD IS A MJAU",
                f"鬼神 Love Em All {command_count}",
                "I am l\u200bouna ^_^",
                f"{emoji_count} MEANINGFUL EMOTICONS",
            ]
        )
        await ctx.send(msg)

    @louna.error
    async def louna_error(self, ctx: Context, error: commands.CommandError):
        match error:
            case commands.RangeError():
                ctx.error_handled = True
                await ctx.send(
                    f"Value must be an integer between {error.minimum} and {error.maximum} (you said {error.value}...)"
                )
            case commands.BadArgument():
                ctx.error_handled = True
                await ctx.send("Value must be an integer")

    async def recent_vore(self):
        async with self.bot.db.cursor() as cur:
            await cur.execute("""SELECT * FROM vore ORDER BY timestamp DESC LIMIT 1;""")
            result = await cur.fetchone()
            if not result:
                return None
        timestamp: int
        channel_id: int
        message_id: int
        timestamp, channel_id, message_id = result
        timestring = discord.utils.format_dt(
            datetime.datetime.fromtimestamp(timestamp, datetime.UTC), "R"
        )
        channel = self.bot.get_channel(channel_id)
        assert isinstance(channel, discord.abc.Messageable)
        message = channel.get_partial_message(message_id)
        jump = message.jump_url
        return f"Last seen {timestring} ({jump})"

    @qwd_only()
    @commands.group(invoke_without_command=True)
    async def vore(self, ctx: Context):
        """How long has it been since the last mention?"""
        recent = await self.recent_vore()
        if recent is None:
            return await ctx.send("It has never been mentioned before, we're saved!")
        return await ctx.send(recent)

    @qwd_only()
    @vore.command(name="0", aliases=["reset"])
    async def zero(self, ctx: Context):
        """Damn it, they did it again"""
        recent = await self.recent_vore()
        async with self.bot.db.cursor() as cur:
            await cur.execute(
                """INSERT INTO vore VALUES(?, ?, ?);""",
                [
                    int(ctx.message.created_at.timestamp()),
                    ctx.channel.id,
                    ctx.message.id,
                ],
            )
        if recent is None:
            return await ctx.send("It had never been mentioned before... before you...")
        await ctx.send("Yum! " + recent)
        await self.update_cached_graph()

    async def update_cached_graph(self):
        async with self.bot.db.cursor() as cur:
            await cur.execute("""SELECT timestamp FROM vore;""")
            dts = [
                datetime.datetime.fromtimestamp(timestamp, datetime.UTC)
                for [timestamp] in await cur.fetchall()
            ]
        fig, ax = plt.subplots()
        ax.eventplot(dts, orientation="horizontal")
        ax.set_title("All events across time")
        ax.set_yticks([])
        ax.xaxis.set_major_locator(ticker.LinearLocator(5))
        file = io.BytesIO()
        fig.savefig(file)
        file.seek(0)
        self.cached_graph = discord.File(
            file,
            filename="graph.png",
            description="Graph of event occurrences across time",
        )

    @qwd_only()
    @commands.is_owner()
    @vore.command()
    async def graph(self, ctx: Context):
        """More details"""
        await ctx.send(file=self.cached_graph)

    @vore.command()
    @commands.is_owner()
    async def scan(self, ctx: Context, after: discord.Object | None):
        if not after:
            await ctx.send("Searching all of history. Are you sure? [yes/no]")

            def check(message: discord.Message):
                return message.author == ctx.author

            try:
                confirm = await self.bot.wait_for("message", check=check)
            except asyncio.TimeoutError:
                return await ctx.send("Not scanning")
            if confirm.content == "yes":
                await ctx.send("Then we shall commence")
            else:
                return await ctx.send("Then no")

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                """SELECT timestamp FROM vore ORDER BY timestamp ASC LIMIT 1;"""
            )
            result = await cur.fetchone()
            if not result:
                before_dt = ctx.message.created_at
            else:
                before_dt = datetime.datetime.fromtimestamp(result[0], datetime.UTC)

        before = discord.Object(discord.utils.time_snowflake(before_dt))

        qwd = self.bot.get_guild(self.bot.qwd_id)
        assert qwd
        results: list[tuple[int, int, int]] = []
        for channel in qwd.channels:
            if not isinstance(channel, discord.abc.Messageable):
                continue
            try:
                async for msg in channel.history(
                    limit=None, after=after, before=before
                ):
                    if msg.content in [
                        "!vore 0",
                        "!dayssincevore 0",
                        "!voredays 0",
                        "!vore update",
                        "!dayssincevore update",
                        "!voredays update",
                        ";vore 0",
                    ]:
                        timestamp = int(msg.created_at.timestamp())
                        channel_id = msg.channel.id
                        message_id = msg.id
                        results.append((timestamp, channel_id, message_id))

                        if len(results) % 10 == 0:
                            await ctx.send(
                                f"{len(results)} instances found so far, updating database"
                            )
            except discord.Forbidden:
                # no permission to read channel history
                continue

        if not results:
            await ctx.send("Found no results.")
        else:
            await ctx.send(f"Found {len(results)} results. Updating the database!")
            async with self.bot.db.cursor() as cur:
                await cur.executemany("""INSERT INTO vore VALUES(?, ?, ?);""", results)

    async def init_vore(self):
        async with self.bot.db.cursor() as cur:
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS vore(
                    timestamp INTEGER PRIMARY KEY,
                    channel_id INTEGER,
                    message_id INTEGER
                );
                """
            )
        await self.update_cached_graph()

    class DistroNotFound(Exception):
        """Valid neofetch distro not found"""

        def __init__(self, query: str, mobile: bool, *args: object) -> None:
            super().__init__(*args)
            self.mobile = mobile
            self.query = query

    async def generate_neofetch(
        self, ctx: Context, distro: str | None = None, is_mobile: bool = False
    ):
        async with self.bot.db.cursor() as cur:
            if is_mobile:
                await cur.execute(
                    """SELECT distro, color_index, color_rgb, logo FROM neofetch
                    WHERE mobile_width IS TRUE AND (
                        :distro IS NULL OR lower(:distro) REGEXP lower(pattern) OR (lower(:distro) || suffix) REGEXP lower(pattern)
                    );
                    """,
                    {"distro": distro},
                )
            else:
                await cur.execute(
                    """SELECT distro, color_index, color_rgb, logo FROM neofetch
                    WHERE :distro IS NULL OR lower(:distro) REGEXP lower(pattern);
                    """,
                    {"distro": distro},
                )

            results = list(await cur.fetchall())
            if not results:
                raise self.DistroNotFound(distro or "<none>", is_mobile)

        distro_found: str
        color_index: int
        color_rgb: str
        logo: str
        distro_found, color_index, color_rgb, logo = random.choice(results)

        r, g, b = bytes.fromhex(color_rgb)
        embed_color = discord.Color.from_rgb(r, g, b)

        accent = lambda s: f"\x1b[{color_index}m{s}\x1b[0m"

        if ctx.guild:
            hostname = ctx.guild.name
        else:
            hostname = "Direct Messages"

        if isinstance(ctx.channel, discord.DMChannel | discord.PartialMessageable):
            terminal = f"direct message with {ctx.author}"
        else:
            terminal = ctx.channel.name

        description = dedent(
            f"""```ansi
            {{}}
            ```
            ```ansi
            {accent(f"{ctx.author}@{hostname}")}
            {accent("OS:")} {distro_found}
            {accent("Host:")} Discord
            {accent("Terminal:")} {terminal}
            ```
            """
        ).format(logo)

        return discord.Embed(
            description=description,
            color=embed_color,
            timestamp=self.neofetch_updated,
        ).set_footer(text="Neofetch data last updated")

    @commands.hybrid_command()
    async def neofetch(
        self,
        ctx: Context,
        mobile: Literal["mobile"] | None = None,
        *,
        distro: str | None = None,
    ):
        """Randomly fetch a neofetch icon

        Parameters
        -----------
        mobile: Literal["mobile"] | None
            Only return icons that fit on a mobile screen
        distro: str | None
            The distro to query for, if given
        """
        if isinstance(ctx.author, discord.Member) and mobile is None:
            is_mobile = ctx.author.mobile_status != discord.Status.offline
        else:
            is_mobile = mobile == "mobile" or False

        embed = await self.generate_neofetch(ctx, distro, is_mobile)

        async def regenerator(is_mobile: bool):
            return await self.generate_neofetch(ctx, None, is_mobile)

        view = self.NeofetchFixer(embed, ctx.author.id, regenerator)
        view.message = await ctx.reply(embed=embed, mention_author=False, view=view)

    @neofetch.autocomplete("distro")
    async def distro_autocomplete(
        self, interaction: discord.Interaction, query: str
    ) -> list[discord.app_commands.Choice]:
        async with self.bot.db.cursor() as cur:
            await cur.execute(
                """SELECT DISTINCT distro FROM neofetch
                WHERE instr(lower(distro), lower(:query))
                ORDER BY distro
                LIMIT 25;
                """,
                {"query": query},
            )

            return [
                discord.app_commands.Choice(name=row[0], value=row[0])
                for row in await cur.fetchall()
            ]

    @neofetch.error
    async def neofetch_error(self, ctx: Context, error: commands.CommandError):
        logging.warn(f"Neofetch error: {error}")
        match error:
            case commands.CommandInvokeError(
                original=self.DistroNotFound(query=query, mobile=mobile)
            ):
                msg = f"I couldn't find a distro for the query '{query}'"
                if mobile:
                    msg += (
                        " that's narrow enough to see on mobile! "
                        "Put `mobile: false` at the end of your command to search all distros."
                    )
                else:
                    msg += "!"
                await ctx.send(msg)
                ctx.error_handled = True

    class NeofetchFixer(discord.ui.View):
        message: discord.Message

        def __init__(
            self,
            embed: discord.Embed,
            author_id: int,
            regenerator: Callable[[bool], Awaitable[discord.Embed]],
        ):
            super().__init__(timeout=120.0)
            self.regenerator = regenerator
            self.embed = embed
            self.author_id = author_id
            self.embed_mode = True

        async def interaction_check(
            self, interaction: discord.Interaction[discord.Client]
        ) -> bool:
            if interaction.user.id == self.author_id:
                return True
            else:
                await interaction.response.send_message(
                    "That's not your button to touch", ephemeral=True
                )
                return False

        def fix_fixer(self):
            fixer = self.children[0]
            if isinstance(fixer, discord.ui.Button):
                if len(self.embed.description or "") > 2000:
                    fixer.disabled = True
                    self.embed_mode = False
                    fixer.label = "Embed only (>2000 chars)"
                else:
                    fixer.disabled = False
                    fixer.label = "Without embed" if self.embed_mode else "With embed"

        @discord.ui.button(label="Without embed", style=discord.ButtonStyle.secondary)
        async def fixup(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            if self.embed_mode:
                button.label = "With embed"
                await interaction.response.edit_message(
                    content=self.embed.description or "", embeds=[], view=self
                )
                self.embed_mode = False
            else:
                button.label = "Without embed"
                await interaction.response.edit_message(
                    content=None, embed=self.embed, view=self
                )
                self.embed_mode = True

        async def regenerate_with(
            self, interaction: discord.Interaction, is_mobile: bool
        ):
            self.embed = await self.regenerator(is_mobile)
            self.fix_fixer()
            if self.embed_mode:
                await interaction.response.edit_message(embed=self.embed, view=self)
            else:
                await interaction.response.edit_message(
                    content=self.embed.description or "", embeds=[], view=self
                )

        @discord.ui.button(
            label="Regenerate (full width)", style=discord.ButtonStyle.primary
        )
        async def regenerate(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            await self.regenerate_with(interaction, False)

        @discord.ui.button(
            label="Regenerate (mobile-width)", style=discord.ButtonStyle.primary
        )
        async def regenerate_mobile(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            await self.regenerate_with(interaction, True)

        async def on_timeout(self) -> None:
            self.clear_items()
            await self.message.edit(view=self)

        @discord.ui.button(label="Stop", style=discord.ButtonStyle.red)
        async def halt(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            self.stop()
            if self.embed_mode:
                await interaction.response.edit_message(embed=self.embed, view=None)
            else:
                await interaction.response.edit_message(
                    content=self.embed.description or "", embeds=[], view=None
                )

    class NeofetchEntry(TypedDict):
        distro: str
        suffix: str
        pattern: str
        mobile_width: bool
        color_index: int
        color_rgb: str
        logo: str

    def typed_neofetch_row(self, row: dict[str, str]) -> NeofetchEntry:
        return {
            "distro": row["distro"],
            "suffix": row["suffix"],
            "pattern": row["pattern"],
            "mobile_width": row["mobile_width"] == "1",
            "color_index": int(row["color_index"]),
            "color_rgb": row["color_rgb"],
            "logo": row["logo"],
        }

    async def init_neofetch(self):
        async with self.bot.db.cursor() as cur:
            await cur.executescript(
                """CREATE TABLE IF NOT EXISTS neofetch(
                    distro TEXT NOT NULL,
                    suffix TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    mobile_width INTEGER NOT NULL,
                    color_index INTEGER NOT NULL,
                    color_rgb TEXT NOT NULL,
                    logo TEXT NOT NULL
                );
                """
            )

            with open("data/neofetch_updated") as f:
                timestamp = int(f.read())
                self.neofetch_updated = datetime.datetime.fromtimestamp(
                    timestamp, datetime.UTC
                )
                await cur.execute("""SELECT last_neofetch_update FROM params;""")
                last_neofetch_update = await cur.fetchone()
                if last_neofetch_update is None or last_neofetch_update[0] != timestamp:
                    with open("data/neofetch.csv") as f:
                        rows = [
                            self.typed_neofetch_row(row) for row in csv.DictReader(f)
                        ]
                        await cur.executemany(
                            """INSERT INTO neofetch VALUES (
                                :distro, :suffix, :pattern, :mobile_width, :color_index, :color_rgb, :logo
                            );
                            """,
                            rows,
                        )
                if last_neofetch_update is None:
                    await cur.execute(
                        """INSERT INTO params(last_neofetch_update) VALUES(?);""",
                        [timestamp],
                    )
                else:
                    await cur.execute(
                        """UPDATE params SET last_neofetch_update = ?;""", [timestamp]
                    )

            with open("data/neofetch_updated") as f:
                self.neofetch_updated = datetime.datetime.fromtimestamp(
                    int(f.read()), datetime.UTC
                )

        logging.info("Initialized neofetch data")


async def setup(bot: OliviaBot):
    await bot.add_cog(Gadgets(bot))

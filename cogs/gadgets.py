import csv
import datetime
import logging
import random
from utils import dedent
from typing import TypedDict
import discord
from discord.ext import commands

from bot import OliviaBot, Context


class Gadgets(commands.Cog):
    """Various gadgets and gizmos"""

    def __init__(self, bot: OliviaBot):
        self.bot = bot

    async def cog_load(self):
        await self.init_neofetch()

    class DistroNotFound(Exception):
        """Valid neofetch distro not found"""

        def __init__(self, query: str, mobile: bool, *args: object) -> None:
            super().__init__(*args)
            self.mobile = mobile
            self.query = query

    class NeofetchFlags(commands.FlagConverter):
        mobile: bool | None
        distro: str | None = commands.flag(positional=True)

    @commands.hybrid_command()
    async def neofetch(self, ctx: Context, *, flags: NeofetchFlags):
        if isinstance(ctx.author, discord.Member) and flags.mobile is None:
            mobile = ctx.author.mobile_status != discord.Status.offline
        else:
            mobile = flags.mobile or False

        async with self.bot.db.cursor() as cur:
            if mobile:
                await cur.execute(
                    """SELECT distro, color_index, color_rgb, logo FROM neofetch
                    WHERE mobile_width IS TRUE AND (
                        :distro IS NULL OR lower(:distro) REGEXP lower(pattern) OR (lower(:distro) || suffix) REGEXP lower(pattern)
                    );
                    """,
                    {"distro": flags.distro},
                )
            else:
                await cur.execute(
                    """SELECT distro, color_index, color_rgb, logo FROM neofetch
                    WHERE :distro IS NULL OR lower(:distro) REGEXP lower(pattern);
                    """,
                    {"distro": flags.distro},
                )

            results = list(await cur.fetchall())
            if not results:
                raise self.DistroNotFound(flags.distro or "<none>", mobile)

            distro: str
            color_index: int
            color_rgb: str
            logo: str
            distro, color_index, color_rgb, logo = random.choice(results)

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
                {accent("OS:")} {distro}
                {accent("Host:")} Discord
                {accent("Terminal:")} {terminal}
                ```
                """
            ).format(logo)

            embed = discord.Embed(
                description=description,
                color=embed_color,
                timestamp=self.neofetch_updated,
            ).set_footer(text="Neofetch data last updated")

            if len(description) > 2000:
                await ctx.reply(
                    embed=embed, mention_author=False, view=self.DisabledFixer()
                )
            else:
                view = self.NeofetchFixer(description, embed)
                view.message = await ctx.reply(
                    embed=embed, mention_author=False, view=view
                )

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

    class DisabledFixer(discord.ui.View):
        @discord.ui.button(
            label="Embed only (>2000 characters)",
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )
        async def noop(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            pass

    class NeofetchFixer(discord.ui.View):
        message: discord.Message

        def __init__(self, content: str, embed: discord.Embed):
            super().__init__()
            self.embed_mode = True
            self.content = content
            self.embed = embed

        @discord.ui.button(label="Without embed", style=discord.ButtonStyle.secondary)
        async def fixup(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            if self.embed_mode:
                button.label = "With embed"
                await interaction.response.edit_message(
                    content=self.content, embeds=[], view=self
                )
                self.embed_mode = False
            else:
                button.label = "Without embed"
                await interaction.response.edit_message(
                    content=None, embed=self.embed, view=self
                )
                self.embed_mode = True

        async def on_timeout(self) -> None:
            self.clear_items()
            await self.message.edit(view=self)

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
            await self.bot.db.executescript(
                """DROP TABLE IF EXISTS neofetch;
                CREATE TABLE neofetch (
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

            with open("data/neofetch.csv") as f:
                rows = [self.typed_neofetch_row(row) for row in csv.DictReader(f)]
                await cur.executemany(
                    """INSERT INTO neofetch VALUES (
                        :distro, :suffix, :pattern, :mobile_width, :color_index, :color_rgb, :logo
                    );
                    """,
                    rows,
                )

            with open("data/neofetch_updated") as f:
                self.neofetch_updated = datetime.datetime.fromtimestamp(
                    int(f.read()), datetime.UTC
                )

        logging.info("Initialized neofetch data")


async def setup(bot: OliviaBot):
    await bot.add_cog(Gadgets(bot))

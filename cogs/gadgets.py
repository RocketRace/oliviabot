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

    class NeofetchFlags(commands.FlagConverter):
        mobile: bool | None

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

    class DistroNotFound(Exception):
        """Valid neofetch distro not found"""

        def __init__(self, mobile: bool, *args: object) -> None:
            super().__init__(*args)
            self.mobile = mobile

    @commands.hybrid_command()
    async def neofetch(self, ctx: Context, distro: str | None, *, flags: NeofetchFlags):
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
                raise self.DistroNotFound(mobile)

            distro_name: str
            color_index: int
            color_rgb: str
            logo: str
            distro_name, color_index, color_rgb, logo = random.choice(results)

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
                {accent("OS:")} {distro_name}
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

            await ctx.reply(embed=embed)

    @neofetch.autocomplete("distro")
    async def distro_autocomplete(
        self, _interaction: discord.Interaction, query: str
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

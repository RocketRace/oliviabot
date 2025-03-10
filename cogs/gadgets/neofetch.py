from __future__ import annotations

import csv
import datetime
import logging
import random
import re
from typing import Awaitable, Callable, Literal, TypedDict

import discord
from discord.ext import commands

from bot import Context, Cog


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
    async def fixup(self, interaction: discord.Interaction, button: discord.ui.Button):
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

    async def regenerate_with(self, interaction: discord.Interaction, is_mobile: bool):
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
    async def halt(self, interaction: discord.Interaction, button: discord.ui.Button):
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


def typed_neofetch_row(row: dict[str, str]) -> NeofetchEntry:
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

    def __init__(self, query: str, mobile: bool, *args: object) -> None:
        super().__init__(*args)
        self.mobile = mobile
        self.query = query


class Neofetch(Cog):
    async def cog_load(self):
        await super().cog_load()
        def regexp(pattern: str, string: str) -> bool:
            return re.match(pattern, string) is not None

        await self.bot.db.create_function("regexp", 2, regexp, deterministic=True)
        await self.init_neofetch()

    async def generate_neofetch(
        self, ctx: Context, distro: str | None = None, is_mobile: bool = False
    ):
        async with ctx.cursor() as cur:
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
                raise DistroNotFound(distro or "<none>", is_mobile)

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

    # @commands.hybrid_command()
    @commands.command()
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

        view = NeofetchFixer(embed, ctx.author.id, regenerator)
        view.message = await ctx.reply(embed=embed, mention_author=False, view=view)

    # @neofetch.autocomplete("distro")
    async def distro_autocomplete(
        self, interaction: discord.Interaction, query: str
    ) -> list[discord.app_commands.Choice]:
        async with self.bot.cursor() as cur:
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
        logging.warning(f"Neofetch error: {error}")
        match error:
            case commands.CommandInvokeError(
                original=DistroNotFound(query=query, mobile=mobile)
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

    async def init_neofetch(self):
        async with self.bot.cursor() as cur:
            with open("data/neofetch_updated") as f:
                timestamp = int(f.read())
                self.neofetch_updated = datetime.datetime.fromtimestamp(
                    timestamp, datetime.UTC
                )
                await cur.execute("""SELECT last_neofetch_update FROM params;""")
                last_neofetch_update = await cur.fetchone()
                if last_neofetch_update is None or last_neofetch_update[0] != timestamp:
                    with open("data/neofetch.csv") as f:
                        rows = [typed_neofetch_row(row) for row in csv.DictReader(f)]
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

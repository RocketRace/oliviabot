import discord
from discord.ext import commands
import git

from bot import OliviaBot, Context


class HelpCommand(commands.DefaultHelpCommand):
    async def send_pages(self) -> None:
        destination = self.get_destination()
        for page in self.paginator.pages:
            # antihighlightification
            page = page.replace("louna", "l\u200bouna")
            await destination.send(page)


class Meta(commands.Cog):
    """Commands related to the behavior of the bot itself"""

    def __init__(self, bot: OliviaBot):
        self.bot = bot
        self.repo = git.Repo(".")
        self.original_help = bot.help_command
        bot.help_command = HelpCommand()
        bot.help_command.cog = self

    async def cog_unload(self):
        self.bot.help_command = self.original_help

    @commands.command()
    async def hello(self, ctx: Context):
        """Hi!"""
        await ctx.send(f"Hello! I'm {ctx.me}!")

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def nick(self, ctx: Context):
        """Update my nickname"""
        automated = [
            "\N{COMBINING LATIN SMALL LETTER A}",
            "\N{COMBINING LATIN SMALL LETTER U}",
            "\N{COMBINING LATIN SMALL LETTER T}",
            "\N{COMBINING LATIN SMALL LETTER O}",
            "\N{COMBINING LATIN SMALL LETTER M}",
            "\N{COMBINING LATIN SMALL LETTER A}",
            "\N{COMBINING LATIN SMALL LETTER T}",
            "\N{COMBINING LATIN SMALL LETTER E}",
            "\N{COMBINING LATIN SMALL LETTER D}",
        ]

        assert isinstance(ctx.author, discord.Member)
        assert isinstance(ctx.me, discord.Member)
        name = ctx.author.display_name.split()[0]
        if len(name) >= 9:
            nick = name[:-9] + "".join(a + b for a, b in zip(name[-9:], automated))
        elif len(name) >= 4:
            nick = name[:-4] + "".join(a + b for a, b in zip(name[-4:], automated[:4]))
        else:
            return await ctx.send("Nickname too short")

        await ctx.me.edit(nick=nick)
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx: Context, cog: str | None = None):
        """Reload cogs"""
        if cog is None:
            for extension in self.bot.activated_extensions:
                await self.bot.reload_extension(extension)
            await ctx.send("Loaded all extensions")
        else:
            await self.bot.reload_extension(cog)
            await ctx.send(f"Loaded {cog}")

    @commands.command()
    @commands.is_owner()
    async def sql(self, ctx: Context, *, command: str):
        """Execute SQL commands"""
        async with self.bot.db.cursor() as cur:
            await cur.execute(command)
            return await ctx.send(
                "\n".join([str(row) for row in await cur.fetchall()])[:2000]
            )

    @commands.command()
    async def about(self, ctx: Context):
        """About me"""
        lines = []
        for commit in self.repo.iter_commits(max_count=5):
            url = f"[`{commit.hexsha[:7]}`](https://github.com/RocketRace/oliviabot/commit/{commit.hexsha})"
            dt = discord.utils.format_dt(commit.committed_datetime, "R")
            full_summary = (
                bytes(commit.summary).decode("utf-8")
                if not isinstance(commit.summary, str)
                else commit.summary
            )
            limit = 40
            summary = (
                full_summary[: limit - 3] + "..."
                if len(full_summary) > limit
                else full_summary
            )
            # changes = f"`+{commit.stats.total["insertions"]}, -{commit.stats.total["deletions"]}`"
            lines.append(f"{url} {dt} {summary}")
        embed = discord.Embed(description=self.bot.description)
        embed.add_field(name="Recent commits", value="\n".join(lines), inline=False)
        await ctx.send(embed=embed)


async def setup(bot: OliviaBot):
    await bot.add_cog(Meta(bot))

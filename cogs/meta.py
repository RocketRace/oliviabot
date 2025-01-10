import aiosqlite
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
    async def howdy(self, ctx: Context):
        """Howdy pardner"""
        await ctx.send(f"Howdy to you too! I'm {ctx.me} 🤠")

    async def change_nickname(self, ctx: Context):
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

        segments = ctx.author.display_name.split(" ")
        for i, segment in enumerate(segments):
            if len(segment) >= 9:
                segments[i] = segment[:-9] + "".join(
                    a + b for a, b in zip(segment[-9:], automated)
                )
                break
        else:
            for i, segment in enumerate(segments):
                if len(segment) >= 4:
                    segments[i] = segment[:-4] + "".join(
                        a + b for a, b in zip(segment[-4:], automated)
                    )
                    break
            else:
                return await ctx.send("the nickname too short for my taste")

        nick = " ".join(segments)
        if len(nick) > 32:
            return await ctx.send("that nikcname is too long! it & my personal touch can't combined be more than 32 characters")
        await ctx.me.edit(nick=nick)
        await ctx.ack()

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def nick(self, ctx: Context):
        """Update my nickname"""
        await self.change_nickname(ctx)
    
    @nick.error
    async def nick_error(self, ctx: Context, error: commands.CommandError):
        match error:
            case commands.NotOwner():
                await ctx.send("well you're not olivia... but I like you so I'll do it :)")
                await self.change_nickname(ctx)
                ctx.error_handled = True

    @commands.group()
    @commands.is_owner()
    async def alias(self, ctx: Context):
        """Person aliases"""

    @alias.command(name="add", aliases=["new"])
    @commands.is_owner()
    async def add_alias(self, ctx: Context, alias: str, user: discord.User):
        """Add a new person alias"""
        async with self.bot.cursor() as cur:
            await cur.execute(
                """INSERT INTO person_aliases VALUES(?, ?);""",
                [alias, user.id]
            )
        await ctx.send(
            f"{user.mention} hi {alias} :)",
            allowed_mentions=discord.AllowedMentions.none()
        )
        await self.bot.refresh_aliases()
    
    @alias.command(name="delete", aliases=["remove"])
    @commands.is_owner()
    async def delete_alias(self, ctx: Context, alias: str):
        """Delete a person alias"""
        async with self.bot.cursor() as cur:
            await cur.execute(
                """DELETE FROM person_aliases WHERE id = ?;""",
                [alias]
            )
        await ctx.send(
            f"{alias} no more :)",
            allowed_mentions=discord.AllowedMentions.none()
        )
        await self.bot.refresh_aliases()

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx: Context, cog: str | None = None):
        """Reload cogs"""
        if cog is None:
            for extension in self.bot.activated_extensions:
                await self.bot.reload_extension(extension)
            await ctx.ack("Loaded all extensions")
        else:
            await self.bot.reload_extension(cog)
            await ctx.ack(f"Loaded {cog}")
    
    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: Context):
        """Sync application commands"""
        await self.bot.tree.sync()
        await ctx.ack()

    @commands.command(aliases=['strql'])
    @commands.is_owner()
    async def sql(self, ctx: Context, *, command: str):
        """Execute SQL commands"""
        async with ctx.cursor() as cur:
            await cur.execute(command)
            return await ctx.send(
                "\n".join(["".join([str(item) for item in row]) if ctx.invoked_with == "strql" else str(row) for row in await cur.fetchall()])[:2000]
                or "<no result>"
            )

    @commands.command()
    @commands.is_owner()
    async def oliviafy(self, ctx: Context, user: discord.User):
        '''You too can become olivia'''
        self.bot.owner_ids.add(user.id)
        await ctx.ack(f"{user.mention} hi, olivia")

    @commands.command()
    @commands.is_owner()
    async def unoliviafy(self, ctx: Context, user: discord.User):
        '''You too can stop becoming olivia'''
        if user.id == 156021301654454272:
            return await ctx.send("what no I'm not doing that")
        self.bot.owner_ids.remove(user.id)
        await ctx.send(f"{user.mention} bye bye... it was nice knowing you as olivia")

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

    @commands.command()
    async def proxy(self, ctx: Context, value: bool | None = None):
        """Configure this bot to respond to proxy messages.

        Run this command with no arguments to see your current settings.

        Parameters
        -----------
        value: bool | None
            ("enable" / "disable") Whether to enable or disable proxy mode.
        """
        proxied = await self.bot.is_proxied(ctx.author)
        negation = "" if proxied else " not"
        if value is None:
            await ctx.send(
                f"You have{negation} enabled proxy mode. "
                "You can enable or disable it using `+proxy enable` or `+proxy disable`."
            )
        else:
            async with ctx.cursor() as cur:
                if value:
                    await cur.execute(
                        """INSERT OR IGNORE INTO proxiers VALUES(?);""", [ctx.author.id]
                    )
                else:
                    await cur.execute(
                        """DELETE FROM proxiers WHERE user_id = ?;""", [ctx.author.id]
                    )
            action = "enabled" if value else "disabled"
            await ctx.send(
                f"You have {action} proxy mode (previously{negation} enabled)"
            )


async def setup(bot: OliviaBot):
    await bot.add_cog(Meta(bot))

from __future__ import annotations
import inspect
from pathlib import Path
import textwrap


import discord
from discord.ext import commands
import git

from bot import Context, Cog

class Info(Cog):
    async def cog_load(self):
        await super().cog_load()
        self.repo = git.Repo(".")

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
    async def privacy(self, ctx: Context):
        """I respect your privacy, sort of :)"""
        await ctx.send(
            "hi! here's the data I store and for what purposes :)\n"
            
            "1. things you put on discord can be accessed by me (and also olivia), including messages "
            "sent in servers or DMs. you can limit the stuff I have access to using discord's own features.\n"
            
            "2. if you don't interact with me, I won't remember anything about you. it's like in real life\n"
            
            "3. some commands (such as `+like optin`, and `+proxy enable`) will store data about you, "
            "such as your user ID. I need the info for those features to work. you can opt out whenever :)\n"

            "4. some commands (such as `+swish`) will cause your data to be sent to other people. "
            "idk what their privacy policy is sorry\n"

            "5. if a command causes errors, the message will be logged and stored for so I can fix the error. "
            "these error logs are also kinda kept forever because they get sent to a private channel and "
            "it's annoying to delete old messages in discord like that\n"

            "6. sometimes olivia will give me your data, for like, admin purposes I think? such as "
            "teaching me your nickname (I'm bad at those). this technically happens without your consent "
            "but um you can ask her nicely and I'm sure she'll say yes\n"

            "I might change my mind on the privacy policy and tweak it without warning so watch out! "
            "but I'll never do anything creepy so don't worry :) I will do my best to treat everyone kindly!"
        )
    

    @commands.command()
    async def source(self, ctx: Context, *, command: str):
        """Show the source code for a command
        
        Example: `+source vore 0`

        Parameters
        -----------
        command: str
            The name of the command including any subcommands
        """
        cmd = self.bot.get_command(command)
        if cmd is None:
            return await ctx.send(f"couldn't find a command with that name `{command}`")
        fn = cmd.callback

        file = inspect.getfile(fn)
        [lines, lineno] = inspect.getsourcelines(fn)
        path = Path(file).relative_to(Path.cwd())
        # find the last position of the function signature
        end = [i for i, line in enumerate(lines) if line.strip().endswith(":")][0]
        # find the last position of the docstring, if any
        for quote in ["'''", '"""']:
            if lines[end + 1].strip().startswith(quote):
                end = [
                    i for i, line in enumerate(lines[end + 1:], end + 1)
                    if line.strip().endswith(quote)
                ][0]
                break
        rows = 10
        prefix = textwrap.dedent(''.join(lines[end + 1:end + 1 + rows]))
        extra = "\n-# results truncated" if len(lines[end + 1:]) > rows else ""
        await ctx.send(
            f"<https://github.com/RocketRace/oliviabot/blob/main/{path}#L{lineno}-L{lineno+len(lines)-1}>\n"
            f"```py\n{prefix}\n```{extra}"
        )

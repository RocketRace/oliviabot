from __future__ import annotations

import asyncio
import datetime
import io
import random

import aiosqlite
import discord
from discord.ext import commands
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from bot import Context, Cog, qwd_only


class Vore(Cog):
    def extract_from_row(self, row: aiosqlite.Row) -> tuple[str, str]:
        timestamp: int
        channel_id: int
        message_id: int
        timestamp, channel_id, message_id = row
        timestring = discord.utils.format_dt(
            datetime.datetime.fromtimestamp(timestamp, datetime.UTC), "R"
        )
        channel = self.bot.get_channel(channel_id)
        assert isinstance(channel, discord.abc.Messageable)
        message = channel.get_partial_message(message_id)
        jump = message.jump_url
        return timestring, jump

    async def recent_vore(self):
        async with self.bot.cursor() as cur:
            await cur.execute("""SELECT * FROM vore ORDER BY timestamp DESC LIMIT 1;""")
            result = await cur.fetchone()
            if not result:
                return None
        timestring, jump = self.extract_from_row(result)
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
        async with ctx.cursor() as cur:
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

    async def update_cached_graph(self):
        async with self.bot.cursor() as cur:
            await cur.execute("""SELECT timestamp FROM vore;""")
            dts = [
                datetime.datetime.fromtimestamp(timestamp, datetime.UTC)
                for [timestamp] in await cur.fetchall()
            ]
        fig, ax = plt.subplots()
        ax.eventplot(
            dts,  # pyright: ignore[reportArgumentType]
            orientation="horizontal",
        )
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

    @qwd_only()
    @vore.command()
    async def random(self, ctx: Context):
        """Show a random instance"""
        async with ctx.cursor() as cur:
            await cur.execute("""SELECT * FROM vore;""")
            result = list(await cur.fetchall())
        if not result:
            return await ctx.send("No such thing!")
        row = random.choice(result)
        timestring, jump = self.extract_from_row(row)
        await ctx.send(f"From {timestring}: {jump}")

    @commands.is_owner()
    @vore.command()
    async def disqualify(self, ctx: Context):
        """It doesn't count!"""
        async with ctx.cursor() as cur:
            await cur.execute("""DELETE FROM vore ORDER BY timestamp DESC LIMIT 1;""")
            result = list(await cur.fetchall())
        if not result:
            return await ctx.send("No such thing!")
        row = random.choice(result)
        timestring, jump = self.extract_from_row(row)
        await ctx.send(f"From {timestring}: {jump}")

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

        async with ctx.cursor() as cur:
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
            async with ctx.cursor() as cur:
                await cur.executemany("""INSERT INTO vore VALUES(?, ?, ?);""", results)

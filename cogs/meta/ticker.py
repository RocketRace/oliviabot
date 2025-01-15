from __future__ import annotations
import datetime
import random

import discord
from discord.ext import commands, tasks

from bot import Context, Cog

class Ticker(Cog):
    async def cog_load(self):
        await super().cog_load()
        self.tickers: dict[str, dict[int, datetime.datetime]] = {}
        async with self.bot.cursor() as cur:
            await cur.execute("""SELECT * FROM ticker_hashes;""")
            results = list(await cur.fetchall())
            for command, hash, delete_at in results:
                self.tickers.setdefault(command, {})[hash] = delete_at

    async def cog_unload(self):
        await super().cog_unload()
        self.tickers = {}

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: Context):
        assert ctx.command 
        qualname = ctx.command.qualified_name
        timestamp = ctx.message.created_at.replace(hour=0, minute=0, second=0)
        # The unique identifier is constructed using
        mishmash = hash((
            # The guild and channel (~6 bits)
            ctx.guild,
            ctx.channel.id,
            # The author (~6 bits)
            ctx.author.id,
            # The current date (~5 bits)
            timestamp.toordinal()
        ))
        delete_at = timestamp + datetime.timedelta(days=30)
        self.tickers.setdefault(qualname, {})[mishmash] = delete_at
        async with self.bot.cursor() as cur:
            await cur.execute(
                """INSERT OR REPLACE INTO ticker_hashes VALUES(?, ?, ?);""",
                [qualname, mishmash, delete_at.timestamp()]
            )
    
    @tasks.loop(time=datetime.time(hour=0, minute=0))
    async def ticker_cleanup(self):
        now = datetime.datetime.now()

        for cmd in self.tickers:
            for hash in self.tickers[cmd]:
                if self.tickers[cmd][hash] < now:
                    del self.tickers[cmd][hash]
            if not self.tickers[cmd]:
                del self.tickers[cmd]

        async with self.bot.cursor() as cur:
            await cur.execute(
                """DELETE FROM ticker_hashes WHERE delete_at < ?;""",
                [now.timestamp()]
            )

    def ticker_emoji(self, n: int):
        sequence = [
            "🔸", "🫧", "❤️", "🌱", "🔅", "💤", "🧶", "❄️", "🧩", "💠", "🍙", "🧊", "💡", "🧪", "🎈",
            "🪢", "🔆", "🎴", "🪹", "🍃", "🕯️", "🪶", "⚛️", "🪼", "🔓", "🫐", "🐛", "🥚", "🐚", "♨️",
            "🏵️", "🧿", "🦋", "🈳", "🌻", "🌿", "🌀", "🎲", "🌾", "🪴", "🎨", "🍵", "🪈", "🦔", "🪸",
            "🪺", "🪽", "🔣", "⛲", "🐦", "🔮", "🎇", "🕊️", "🌃", "🧬", "🌲", "⚗️", "📚", "🔭", "⚧",
            "🦢", "⚖️", "⚕️", "☄️", "🌫️", "🦌", "🔬", "🛰️", "🏞️", "🎏", "⛰️", "🎆", "🪐", "🏔️", "🌌",
        ]
        return sequence[min(n // 2 + 1, len(sequence) - 1)]

    @commands.command()
    async def ticker(self, ctx: Context):
        """Show a count of how my commands have been used in the past month"""
        return await ctx.send(
            "\n".join([
                f"{self.ticker_emoji(n)} `{name}`"
                for n, name in sorted([
                    (len(hashes), name)
                    for name, hashes in self.tickers.items()
                ], reverse=True)
            ])
        )

    
from __future__ import annotations

import random

import aiosqlite
import discord
from discord.ext import commands

from bot import Context, Cog

from .horse import unhorsify


class Louna(Cog):
    async def louna_cog_load(self):
        await self.reload_emoji()
    
    async def reload_emoji(self):
        async with self.bot.cursor() as cur:
            await cur.execute("""SELECT * FROM louna_emojis;""")
            rows = list(await cur.fetchall())
            self.louna_emojis: list[str] = [row[0] for row in rows]
            self.louna_weights: list[float] = [row[1] for row in rows]

    @commands.group(invoke_without_command=True)
    async def louna(self, ctx: Context):
        """l\u200bouna"""
        if random.random() < 1 / 25:
            k = 4
        else:
            k = random.randint(2, 3)
        choices = "".join(random.choices(self.louna_emojis, self.louna_weights, k=k))
        await ctx.reply(f"l\u200bouna {choices}", mention_author=False)
        async with ctx.cursor() as cur:
            await cur.execute(
                """UPDATE params SET louna_command_count = louna_command_count + 1;"""
            )
            await cur.execute(
                """UPDATE params SET louna_emoji_count = louna_emoji_count + ?;""", [k]
            )

    @commands.Cog.listener(name="on_message")
    async def hevonen(self, msg: discord.Message):
        before, after = msg.content, unhorsify(msg.content)
        if before != after and after.startswith("+louna") and not before.startswith("+louna config"):
            # clone is required as the same Message object is used across listeners
            new_msg = await msg.channel.fetch_message(msg.id)
            new_msg.content = after
            await self.bot.process_commands(new_msg)

    @louna.command()
    async def stats(self, ctx: Context):
        """how many l\u200bouna?"""
        async with ctx.cursor() as cur:
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
    
    @louna.group(name="config", invoke_without_command=True)
    @commands.is_owner()
    async def emoji_config(self, ctx: Context):
        """for internal use only"""
        weighted: dict[float, list[str]] = {}
        for emoji, weight in zip(self.louna_emojis, self.louna_weights):
            weighted.setdefault(weight, []).append(emoji)
        for emojis in weighted.values():
            emojis.sort()
        rows = [
            f"{weight} {" ".join(e)}" for weight, e in sorted(weighted.items(), reverse=True)
        ]
        response = "\n\n".join(rows)
        if response:
            await ctx.reply(response)
        else:
            await ctx.send("I have no emojis")

    @emoji_config.command(name="get", aliases=["check"])
    @commands.is_owner()
    async def get_emoji(self, ctx: Context, emoji: str):
        async with self.bot.cursor() as cur:
            await cur.execute(
                """SELECT weight FROM louna_emojis WHERE emoji = ?;""",
                [emoji]
            )
            result = await cur.fetchone()
            if result is None:
                return await ctx.ack(f"{emoji} is not on my list")
            else:
                weight = result[0]
                return await ctx.ack(f"{emoji} appears with a weight of {weight}")

    @emoji_config.command(name="add", aliases=["new"])
    @commands.is_owner()
    async def add_emoji(self, ctx: Context, weight: float | None, *emojis: str):
        weight = 1.0 if weight is None else weight
        async with self.bot.cursor() as cur:
            try:
                await cur.executemany(
                    """INSERT INTO louna_emojis VALUES(?, ?);""",
                    [(emoji, weight) for emoji in emojis]
                )
            except aiosqlite.IntegrityError:
                extant = []
                for emoji in emojis:
                    await cur.execute(
                        """SELECT emoji FROM louna_emojis WHERE emoji = ?;""",
                        [emoji]
                    )
                    rows = await cur.fetchall()
                    extant.extend([row[0] for row in rows])
                return await ctx.send(f"{" ".join(extant)} already exists!")
        await self.reload_emoji()
        await ctx.ack()
    
    @emoji_config.command(name="edit", aliases=["update"])
    @commands.is_owner()
    async def edit_emoji(self, ctx: Context, weight: float | None, *emojis: str):
        """for internal use only"""
        weight = 1.0 if weight is None else weight
        async with self.bot.cursor() as cur:
            await cur.executemany(
                """UPDATE louna_emojis SET weight = ? WHERE emoji = ?;""",
                [(weight, emoji) for emoji in emojis]
            )
        await self.reload_emoji()
        await ctx.ack()

    @emoji_config.command(name="delete", aliases=["remove"])
    @commands.is_owner()
    async def delete_emoji(self, ctx: Context, *emojis: str):
        """for internal use only"""
        async with self.bot.cursor() as cur:
            await cur.executemany(
                """DELETE FROM louna_emojis WHERE emoji = ?;""",
                [(emoji,) for emoji in emojis]
            )
        await self.reload_emoji()
        await ctx.ack()

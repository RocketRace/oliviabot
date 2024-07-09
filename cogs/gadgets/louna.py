from __future__ import annotations

import random
from discord.ext import commands

from bot import OliviaBot, Context, Cog


class Louna(Cog):
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
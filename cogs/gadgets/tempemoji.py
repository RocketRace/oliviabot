from __future__ import annotations
import asyncio
import datetime
from io import BytesIO
import math
import random
import re

import discord
from discord.ext import commands, tasks
from PIL import Image

from bot import Context, Cog

class EmojiNameConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        argument = re.sub(r"[^\w]", "", argument)
        if re.match(r"\w{1,27}", argument):
            return argument
        else:
            raise commands.BadArgument()

class SimplePronoun(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        [pronoun, *_] = argument.split("/")
        return pronoun

class TempEmoji(Cog):
    async def tempemoji_cog_load(self):
        self.deleter_task.start()
    
    async def tempemoji_cog_unload(self):
        self.deleter_task.stop()

    @commands.guild_only()
    # fixme: When discord fixes their shit, change this!
    @commands.bot_has_guild_permissions(manage_expressions=True)
    @commands.command()
    async def tempemoji(
        self,
        ctx: Context,
        image: discord.Attachment,
        name: str = commands.parameter(converter=EmojiNameConverter),
        pronouns: commands.Greedy[str] = commands.parameter(converter=commands.Greedy[SimplePronoun])
    ):
        """Creates a temporary emoji from an attachment

        The emoji lasts for 1 hour.

        Example: +tempemoji robotgirl she/her it/its
        
        Parameters
        -----------
        name: str
            The emoji name
        pronouns: str
            The emoji's pronouns (multiple allowed, use e.g. she/her they/them instead of she/they)
        """
        guild = ctx.guild
        assert guild
        if len(guild.emojis) >= guild.emoji_limit:
            return await ctx.send("Sorry... there's no space left :(")
        
        image_bytes = await image.read()
        byte_size = len(image_bytes)
        max_size = 256000
        if byte_size > max_size:
            img = Image.open(BytesIO(image_bytes))
            # approximate file size using pixels
            # this is okay, since the final size should stay within
            # 64kb and 256kb, aka a pretty large margin of error
            # for this purpose I also overshoot by 1.5x lol
            w, h = img.size
            shrink_factor = math.sqrt(byte_size / max_size) * 1.5
            # ensure that we don't shrink *both* axes under 128px
            # as long as one axis is greater, then we have not
            # lost any precision unnecessarily
            shrink_factor = min(shrink_factor, max(w / 128, h / 128))
            
            new_size = w // shrink_factor, h // shrink_factor
            img.thumbnail(new_size)
            new_bytes = BytesIO()
            img.save(new_bytes, "png")
            image_bytes = new_bytes.getvalue()
            byte_size = len(image_bytes)

        emoji = await guild.create_custom_emoji(
            name=name + "_temp",
            image=image_bytes,
            reason=f"+tempemoji :{name}_temp: by {ctx.author.display_name}"
        )

        hours = 1
        now = datetime.datetime.now()
        then = now + datetime.timedelta(hours=hours)

        async with ctx.bot.cursor() as cur:
            await cur.execute(
                """INSERT INTO tempemoji VALUES(?, ?, ?);""",
                [emoji.id, guild.id, then.timestamp()]
            )

        pronoun = random.choice(pronouns) if pronouns else "it"
        await ctx.message.add_reaction(emoji)
        await ctx.reply(f"{emoji} is here!\n-# {pronoun} will poof {discord.utils.format_dt(then, 'R')}!")
        await asyncio.sleep(60 * 60 * hours)
        await self.try_delete_emoji(emoji.id, guild.id)

    @tempemoji.error
    async def tempemoji_error(self, ctx: Context, error: commands.CommandError):
        match error:
            case commands.NoPrivateMessage():
                attachments = ctx.message.attachments
                attachment = attachments[0] if attachments else None
                msg = "sorry, you can only +tempemoji in a server..."
                try:
                    await ctx.send(
                        f"{msg} but we can still send images back and forth :)",
                        file=attachment
                    )
                # attachment too big
                except discord.HTTPException:
                    await ctx.send(msg)
                ctx.error_handled = True
            case commands.BotMissingPermissions():
                await ctx.send("I can't create emojis so I can't create tempemojis :(")
                ctx.error_handled = True
            case commands.BadArgument():
                await ctx.send("That name is too short! Or too long I didn't check")
                ctx.error_handled = True
            case commands.MissingRequiredArgument():
                await ctx.send("You have to include a name to the message as well !")
                ctx.error_handled = True
            case commands.MissingRequiredAttachment():
                await ctx.send("you have to send an image file for the emoji!")
                ctx.error_handled = True
            case commands.CommandInvokeError(original=discord.HTTPException()):
                await ctx.send("The image isn't quite right... I think it's too big (even though I resized it?)")
                ctx.error_handled = True

    async def try_delete_emoji(self, emoji_id: int, guild_id: int):
        emoji = self.bot.get_emoji(emoji_id)
        if emoji is None:
            return
        guild = self.bot.get_guild(guild_id)
        guild_display = guild.name if guild else str(guild_id)
        await self.bot.webhook.send(f"Deleting emoji <:__:{emoji_id}> in `{guild_display}`")
        try:
            await emoji.delete()
            return await self.bot.webhook.send(f"Deleted!")
        except discord.HTTPException:
            # nothing to do really, either we can't delete or it's already gone
            return await self.bot.webhook.send(f"Failed!")

    @tasks.loop(minutes=15)
    async def deleter_task(self):
        await asyncio.sleep(60)
        now = datetime.datetime.now()
        async with self.bot.cursor() as cur:
            await cur.execute(
                """SELECT emoji_id, guild_id FROM tempemoji WHERE delete_at < ?;""",
                [now.timestamp()]
            )
            for row in await cur.fetchall():
                emoji_id = row[0]
                guild_id = row[1]
                await self.try_delete_emoji(emoji_id, guild_id)
            
            await cur.execute(
                """DELETE FROM tempemoji WHERE delete_at < ?""",
                [now.timestamp()]
            )
    
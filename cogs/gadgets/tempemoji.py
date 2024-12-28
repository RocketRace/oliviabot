from __future__ import annotations
import asyncio
import datetime
import re

import discord
from discord.ext import commands, tasks

from bot import Context, Cog

class EmojiNameConverter(commands.Converter[str]):
    async def convert(self, ctx: commands.Context, argument: str):
        match = re.match(r":(\w{2,32}):|(\w{2,32})", argument)
        if match is not None:
            # groups across branches aren't merged
            return list(filter(None, match.groups()))[0]
        else:
            raise commands.BadArgument()
            

class TempEmoji(Cog):
    async def tempemoji_cog_load(self):
        self.deleter_task.start()
    
    async def tempemoji_cog_unload(self):
        self.deleter_task.stop()

    @commands.guild_only()
    # fixme: When discord fixes their shit, change this!
    @commands.bot_has_guild_permissions(manage_expressions=True)
    @commands.command()
    async def tempemoji(self, ctx: Context, image: discord.Attachment, name: str = commands.parameter(converter=EmojiNameConverter)):
        """Creates a temporary emoji from an attachment

        The emoji lasts for 1 hour.
        
        Parameters
        -----------
        name: str
            The emoji name
        """
        guild = ctx.guild
        assert guild
        if len(guild.emojis) >= guild.emoji_limit:
            return await ctx.send("Sorry... there's no space left :(")
        
        emoji = await guild.create_custom_emoji(
            name=name,
            image=await image.read(),
            reason=f"+tempemoji :{name}: by {ctx.author.display_name}"
        )

        now = datetime.datetime.now()
        then = now + datetime.timedelta(hours=1)

        async with ctx.bot.cursor() as cur:
            await cur.execute(
                """INSERT INTO tempemoji VALUES(?, ?, ?);""",
                [emoji.id, guild.id, then.timestamp()]
            )
        await ctx.message.add_reaction(emoji)
        await ctx.reply(f"{emoji} is here!\n-# it will poof {discord.utils.format_dt(then, "R")}!")
        await asyncio.sleep(60 * 60)
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
                await ctx.send("you have to include a name to the message as well !")
                ctx.error_handled = True
            case commands.MissingRequiredAttachment():
                await ctx.send("you have to send an image file for the emoji, sorry if that was unclear")
                ctx.error_handled = True
            case discord.HTTPException():
                await ctx.send("the image isn't quite right... i think it's too big (in the future i can rescale them)")
                ctx.error_handled = True

    async def try_delete_emoji(self, emoji_id: int, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild is not None:
            if guild.get_emoji(emoji_id) is None:
                return
            await self.bot.webhook.send(f"Deleting emoji <:__:{emoji_id}> in `{guild.name}`")
            try:
                await guild.delete_emoji(discord.Object(emoji_id))
                return await self.bot.webhook.send(f"Deleted!")
            except discord.HTTPException:
                # nothing to do really, either we can't delete or it's already gone
                return await self.bot.webhook.send(f"Did not delete!")
        return await self.bot.webhook.send(f"Can't delete {emoji_id} in {guild_id}! (No guild)")

    @tasks.loop(minutes=15)
    async def deleter_task(self):
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
    
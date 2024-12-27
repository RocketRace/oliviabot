from __future__ import annotations

import discord
from discord.ext import commands, tasks

from bot import Context, Cog

class TempEmoji(Cog):
    @commands.guild_only()
    @commands.bot_has_permissions(create_expressions=True)
    @commands.command()
    @commands.is_owner() # temporary check since the command isn't done yet
    async def tempemoji(self, ctx: Context, name: str, image: discord.Attachment):
        """Creates a temporary emoji that lasts for 24 hours
        
        Parameters
        -----------
        text: str | None
            The text / reply to be translated.
        """
        guild = ctx.guild
        assert guild
        if len(guild.emojis) >= guild.emoji_limit:
            return await ctx.send("Sorry... there's no space left :(")
        
        emoji = await guild.create_custom_emoji(
            name=name,
            image=await image.read(),
            reason=f"+tempemoji :{name}: by {ctx.author.display_avatar}"
        )

        await ctx.message.add_reaction(emoji)
        await ctx.reply(f"-# {emoji}")

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
            case discord.HTTPException():
                await ctx.send("woah ummmmm idk what happened but something went wrong...")
                ctx.error_handled = True
    
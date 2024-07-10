import logging
import traceback

import discord
from discord.ext import commands

from bot import Context, OliviaBot


class ErrorHandler(commands.Cog):
    def __init__(self, bot: OliviaBot):
        self.bot = bot

    async def log_error(self, ctx: Context, error: commands.CommandError):
        tb = "\n".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        embed = discord.Embed(
            title=error,
            description=f"```py\n{tb}\n```",
            color=discord.Color.from_str("#db7420"),
            timestamp=ctx.message.created_at,
        )

        author = f"Author: {ctx.author.mention} ({ctx.author}, ID: {ctx.author.id})"
        channel = (
            f"Channel: {ctx.channel.mention} ({ctx.channel}, ID: {ctx.channel.id})"
            if not isinstance(
                ctx.channel,
                (discord.DMChannel, discord.GroupChannel, discord.PartialMessageable),
            )
            else f"Channel: {ctx.channel} (ID: {ctx.channel.id})"
        )
        guild = (
            f"Guild: {ctx.guild} ({ctx.guild.member_count or "<unknown>"} members, ID: {ctx.guild.id})"
            if ctx.guild
            else "Private messages"
        )
        context = "\n".join([author, channel, guild])
        embed.add_field(name="Context", value=context, inline=False)

        content = (
            f"```\n{ctx.message.content[:1000]}\n```\nJump: {ctx.message.jump_url}"
        )
        embed.add_field(
            name=(
                "Message (truncated)" if len(ctx.message.content) > 1000 else "Message"
            ),
            value=content,
            inline=False,
        )

        webhook = discord.Webhook.from_url(self.bot.webhook_url, client=self.bot)
        await webhook.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: commands.CommandError):
        # skip errors that we don't want to report in any way
        if isinstance(error, commands.CommandNotFound):
            return

        await self.log_error(ctx, error)

        # Error handling resolution order:
        # 1. Command-local error handler
        # 2. Cog-local error handler
        # 3. Global error handler
        #
        # If any previous steps set `error_handled` to True, bail
        if ctx.error_handled:
            return

        command_name = ctx.command.name if ctx.command else "<no command>"

        match error:
            # UserInputError / BadArgument tree
            case commands.TooManyArguments():
                await ctx.send(f"Too many arguments given to {command_name}")
            case commands.MissingRequiredArgument():
                await ctx.send(
                    f"Command {command_name} missing required parameter '{error.param}'"
                )
            case commands.ArgumentParsingError():
                await ctx.send(
                    "Failed to parse input. I should give a better error here but that's not yet done"
                )
            case commands.BadArgument():
                await ctx.send(f"Bad argument in command {command_name}: {error}")

            # CheckFailure tree
            case commands.BotMissingPermissions():
                if len(error.missing_permissions) == 1:
                    await ctx.send(
                        f"I'm missing the {error.missing_permissions[0]} permission"
                    )
                else:
                    await ctx.send(
                        f"I'm missing all these permissions: {', '.join(error.missing_permissions)}"
                    )
            case commands.MissingPermissions():
                if len(error.missing_permissions) == 1:
                    await ctx.send(
                        f"You're missing the {error.missing_permissions[0]} permission"
                    )
                else:
                    await ctx.send(
                        f"You're missing all these permissions: {', '.join(error.missing_permissions)}"
                    )
            case commands.NotOwner():
                await ctx.send("well you're not olivia")
            case commands.CheckFailure():
                await ctx.send(f"Check failure in command {command_name}: {error}")

            # Other base errors
            case commands.ConversionError():
                await ctx.send("Something went wrong with the parsing here")
            case commands.CommandInvokeError():
                await ctx.send(
                    f"Something raised {error.original.__class__.__name__} from inside the command"
                )
                logging.exception(
                    f"Exception in command {command_name}",
                    exc_info=error.original,
                )
            case _:
                await ctx.send("Something went wrong, somehow")
                logging.exception(
                    f"Exception in command {command_name}: {error}", exc_info=error
                )


async def setup(bot: OliviaBot):
    await bot.add_cog(ErrorHandler(bot))

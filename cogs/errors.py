import logging
from discord.ext import commands

from bot import Context, OliviaBot


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: commands.CommandError):
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
            case commands.CommandNotFound():
                pass
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

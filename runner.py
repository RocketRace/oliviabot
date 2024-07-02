import asyncio
import logging
import pathlib
import sys

import config
import bot


async def main():
    match sys.argv:
        case [_, arg] if arg.lower() == "prod":
            prod = True
        case [_]:
            prod = False
        case _:
            relative = pathlib.Path(__file__).relative_to(pathlib.Path.cwd())
            print(f"Usage: python3 {relative} [prod]")
            exit(1)

    print("Running the bot in", "production" if prod else "development", "mode:")

    async with bot.init(prod=prod) as oliviabot:
        try:
            await oliviabot.start(config.bot_token)
        except asyncio.CancelledError:
            logging.info("Shutting down...")


asyncio.run(main())

import asyncio
import logging
import pathlib
import sys
from time import sleep
from typing import Literal

import aiosqlite
import discord
from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, PatternMatchingEventHandler

import config
from context import OliviaBot


class CogReloader(PatternMatchingEventHandler):
    def __init__(self, bot: OliviaBot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    def handle_change(self, path_str: str, action: Literal["load", "unload", "reload"]):
        path = pathlib.Path(path_str).relative_to(pathlib.Path.cwd() / "cogs")
        cog = f"cogs.{path.stem}"
        while pathlib.Path(".updating").exists():
            sleep(0.5)
        if cog in self.bot.activated_extensions:
            match action:
                case "load":
                    coro = self.bot.load_extension(cog)
                case "reload":
                    coro = self.bot.reload_extension(cog)
                case "unload":
                    coro = self.bot.unload_extension(cog)
            asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            logging.info(f"Extension {cog} {action}ed")

    def on_created(self, event: FileSystemEvent) -> None:
        self.handle_change(event.src_path, "load")

    def on_modified(self, event: FileSystemEvent) -> None:
        self.handle_change(event.src_path, "reload")

    def on_deleted(self, event: FileSystemEvent) -> None:
        self.handle_change(event.src_path, "unload")

    def on_moved(self, event: FileSystemEvent) -> None:
        self.handle_change(event.src_path, "unload")
        self.handle_change(event.dest_path, "load")


class ReloadReporter(PatternMatchingEventHandler):
    def on_created(self, event: FileSystemEvent) -> None:
        self.handle_change()

    def on_deleted(self, event: FileSystemEvent) -> None:
        self.handle_change()

    def on_modified(self, event: FileSystemEvent) -> None:
        self.handle_change()

    def on_moved(self, event: FileSystemEvent) -> None:
        self.handle_change()

    def handle_change(self):
        logging.info("Restarting bot")
        open(".reload-trigger", "w")


match sys.argv:
    case [_, arg] if arg.lower() == "prod":
        prod = True
    case [_]:
        prod = False
    case _:
        relative = pathlib.Path(__file__).relative_to(pathlib.Path.cwd())
        print(f"Usage: python3 {relative} [prod]")
        exit(1)


async def main():
    print("Running the bot in", "production" if prod else "development", "mode:")

    if prod:
        handler = logging.FileHandler("discord.log", encoding="utf-8")
        discord.utils.setup_logging(handler=handler, level=logging.INFO)
    else:
        discord.utils.setup_logging(level=logging.INFO)

    async with (
        aiosqlite.connect(config.database_path, autocommit=True) as db,
        OliviaBot(
            prod=prod,
            db=db,
            testing_guild_id=config.testing_guild_id,
            testing_channel_id=config.testing_channel_id,
            webhook_url=config.webhook_url,
            tester_bot_id=config.tester_bot_id,
            tester_bot_token=config.tester_bot_token,
        ) as oliviabot,
    ):
        observer = Observer()

        cog_watcher = CogReloader(oliviabot, patterns=["cogs/*.py"])
        root_watcher = ReloadReporter(
            patterns=[
                line.strip() for line in open(".bot-reload-patterns") if line.strip()
            ]
        )

        observer.schedule(cog_watcher, path="cogs")
        observer.schedule(root_watcher, path=".")

        try:
            observer.start()
            await oliviabot.start()
        except asyncio.CancelledError:
            pass
        finally:
            logging.info("Shutting down...")
            observer.stop()
            observer.join()


asyncio.run(main())

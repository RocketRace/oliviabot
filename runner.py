import asyncio
import logging
import os
import pathlib
import sys
from time import sleep
from typing import Literal

from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, PatternMatchingEventHandler

import config
import bot


class CogWatch(PatternMatchingEventHandler):
    def __init__(self, bot: bot.OliviaBot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    def handle_change(self, path_str: str, kind: Literal["load", "unload", "reload"]):
        path = pathlib.Path(path_str).relative_to(pathlib.Path.cwd() / "cogs")
        cog = f"cogs.{path.stem}"
        while pathlib.Path(".updating").exists():
            sleep(1)
        self.bot.dispatch("extension_update", cog, kind)

    def on_created(self, event: FileSystemEvent) -> None:
        self.handle_change(event.src_path, "load")

    def on_modified(self, event: FileSystemEvent) -> None:
        self.handle_change(event.src_path, "reload")

    def on_deleted(self, event: FileSystemEvent) -> None:
        self.handle_change(event.src_path, "unload")

    def on_moved(self, event: FileSystemEvent) -> None:
        self.handle_change(event.src_path, "unload")
        self.handle_change(event.dest_path, "load")


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
        observer = Observer()
        cog_watcher = CogWatch(oliviabot, patterns=["cogs/*.py"])
        observer.schedule(cog_watcher, path="cogs")
        try:
            observer.start()
            await oliviabot.start(config.bot_token)
        except asyncio.CancelledError:
            logging.info("Shutting down...")
        finally:
            observer.stop()
            observer.join()


asyncio.run(main())

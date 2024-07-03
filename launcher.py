from __future__ import annotations

import abc
import asyncio
import concurrent.futures
import logging
import pathlib
from shutil import ignore_patterns
import sys
from threading import Condition, Event
import threading
from time import sleep
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Literal

from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, PatternMatchingEventHandler

if TYPE_CHECKING:
    import bot


class CogReloader(PatternMatchingEventHandler):
    def __init__(self, bot: bot.OliviaBot, *args, **kwargs):
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


class ChangeHandler(PatternMatchingEventHandler, abc.ABC):
    @abc.abstractmethod
    def handle_change(self): ...

    def on_created(self, event: FileSystemEvent) -> None:
        self.handle_change()

    def on_deleted(self, event: FileSystemEvent) -> None:
        self.handle_change()

    def on_modified(self, event: FileSystemEvent) -> None:
        self.handle_change()

    def on_moved(self, event: FileSystemEvent) -> None:
        self.handle_change()


class BotReloader(ChangeHandler):
    def __init__(self, bot: bot.OliviaBot, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

    def handle_change(self):
        logging.info("Restarting bot")
        try:
            self.handle = self.bot.loop.call_soon_threadsafe(
                self.bot.dispatch, "restart_needed"
            )
        except AttributeError:
            # no loop, double dispatched
            pass


class RootReporter(ChangeHandler):
    def handle_change(self):
        open(".root-reload-trigger", "w")


match sys.argv:
    case [_, arg] if arg.lower() == "prod":
        prod = True
    case [_]:
        prod = False
    case _:
        relative = pathlib.Path(__file__).relative_to(pathlib.Path.cwd())
        print(f"Usage: python3 {relative} [prod]")
        exit(1)


async def launch():
    print("Running the bot in", "production" if prod else "development", "mode:")

    try:
        del sys.modules["bot"]
    except KeyError:
        pass

    import bot

    async with bot.init(prod=prod) as oliviabot:
        observer = Observer()

        cog_patterns = ["cogs/*.py"]
        bot_patterns = [
            line.strip() for line in open(".bot-reload-patterns") if line.strip()
        ]
        root_patterns = [
            line.strip() for line in open(".root-reload-patterns") if line.strip()
        ]

        cog_watcher = CogReloader(oliviabot, patterns=cog_patterns)
        bot_watcher = BotReloader(
            oliviabot,
            patterns=bot_patterns,
            ignore_patterns=root_patterns + cog_patterns,
        )
        root_watcher = RootReporter(patterns=root_patterns)

        observer.schedule(cog_watcher, path="cogs", recursive=True)
        observer.schedule(bot_watcher, path=".", recursive=True)
        observer.schedule(root_watcher, path=".", recursive=True)

        try:
            observer.start()
            await oliviabot.start()
        except asyncio.CancelledError:
            pass
        finally:
            logging.info("Shutting down...")
            observer.stop()
            observer.join()

    return oliviabot.restart_triggered


async def main():
    while await launch():
        pass


asyncio.run(main())

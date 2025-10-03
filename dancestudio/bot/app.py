import asyncio
import logging
from pathlib import Path
from typing import Iterable

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand


def _ensure_standalone_imports(paths: Iterable[Path]) -> None:
    """Ensure local package imports work when run outside the project root.

    The bot container copies only the contents of ``dancestudio/bot`` into
    ``/app``.  In that environment the ``dancestudio`` package is absent, which
    prevents ``from dancestudio.bot import ...`` imports from working.  We fall
    back to importing modules relative to the current file by temporarily
    extending ``sys.path`` with the provided directories.
    """

    import sys

    for path in paths:
        resolved = str(path.resolve())
        if resolved not in sys.path:
            sys.path.insert(0, resolved)


try:  # pragma: no cover - executed depending on deployment layout
    from dancestudio.bot.config import get_settings
    from dancestudio.bot.handlers import menu
    from dancestudio.bot.middlewares.logging import LoggingMiddleware
except ModuleNotFoundError as exc:  # pragma: no cover - fallback for Docker image
    if exc.name and not exc.name.startswith("dancestudio"):
        raise
    _ensure_standalone_imports([Path(__file__).resolve().parent])
    from config import get_settings  # type: ignore[no-redef]
    from handlers import menu  # type: ignore[no-redef]
    from middlewares.logging import LoggingMiddleware  # type: ignore[no-redef]

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    settings = get_settings()
    bot = Bot(
        settings.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(LoggingMiddleware())
    dp.include_router(menu.router)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Главное меню"),
        ]
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

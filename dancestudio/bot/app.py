import asyncio
import logging
import sys
import types
from importlib.machinery import ModuleSpec
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

def _bootstrap_namespace() -> None:
    """Ensure ``dancestudio.bot`` imports work when only the bot folder is present."""

    package_dir = Path(__file__).resolve().parent
    namespace_root = package_dir.parent

    namespace_module = sys.modules.get("dancestudio")
    if namespace_module is None:
        namespace_module = types.ModuleType("dancestudio")
        namespace_spec = ModuleSpec("dancestudio", loader=None, is_package=True)
        namespace_spec.submodule_search_locations = [str(namespace_root)]
        namespace_module.__spec__ = namespace_spec
        namespace_module.__path__ = list(namespace_spec.submodule_search_locations)
        namespace_module.__package__ = "dancestudio"
        sys.modules["dancestudio"] = namespace_module
    else:
        paths = list(getattr(namespace_module, "__path__", []))  # type: ignore[arg-type]
        location = str(namespace_root)
        if location not in paths:
            paths.insert(0, location)
            namespace_module.__path__ = paths  # type: ignore[attr-defined]

    bot_module = sys.modules.get("dancestudio.bot")
    if bot_module is None:
        bot_module = types.ModuleType("dancestudio.bot")
        sys.modules["dancestudio.bot"] = bot_module

    bot_spec = ModuleSpec("dancestudio.bot", loader=None, is_package=True)
    bot_spec.submodule_search_locations = [str(package_dir)]
    bot_module.__spec__ = bot_spec
    bot_module.__path__ = list(bot_spec.submodule_search_locations)  # type: ignore[attr-defined]
    bot_module.__package__ = "dancestudio.bot"
    setattr(namespace_module, "bot", bot_module)


_bootstrap_namespace()

from dancestudio.bot.config import get_settings
from dancestudio.bot.handlers import menu
from dancestudio.bot.middlewares.logging import LoggingMiddleware


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

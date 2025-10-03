"""Entry point for the standalone payments demo bot."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import get_settings
from handlers import common, payments


async def main() -> None:
    """Configure and launch the Telegram bot via long polling."""

    logging.basicConfig(level=logging.INFO)

    settings = get_settings()

    bot = Bot(token=settings.bot_token, parse_mode="HTML")
    dp = Dispatcher()

    dp.include_router(common.router)
    dp.include_router(payments.router)

    logging.info("Bot is running…")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

"""Common UX-related handlers for the demo bot."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message


router = Router()


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Greet the user and show a button to start the purchase flow."""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Купить", callback_data="go_buy")]]
    )
    await message.answer(
        "Привет! Это демо оплаты через Telegram Payments с YooKassa.\n"
        "Нажмите кнопку ниже, чтобы открыть форму оплаты.",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "go_buy")
async def handle_go_buy(callback: CallbackQuery) -> None:
    """Prompt the user to use the /buy command when they tap the button."""

    await callback.message.answer("Для оформления заказа отправьте команду /buy")
    await callback.answer()

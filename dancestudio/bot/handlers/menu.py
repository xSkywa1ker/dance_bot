from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from keyboards import main_menu_keyboard
from utils import texts

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(texts.MAIN_MENU, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "rules")
async def show_rules(callback: CallbackQuery) -> None:
    await callback.message.edit_text(texts.CANCEL_RULES, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "my_bookings")
async def my_bookings(callback: CallbackQuery) -> None:
    await callback.answer("Функция в разработке", show_alert=True)


@router.callback_query(F.data.in_({"book_class", "buy_subscription"}))
async def not_implemented(callback: CallbackQuery) -> None:
    await callback.answer("Скоро будет доступно", show_alert=True)

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Записаться на занятие", callback_data="book_class")],
            [InlineKeyboardButton(text="Купить абонемент", callback_data="buy_subscription")],
            [InlineKeyboardButton(text="Мои записи", callback_data="my_bookings")],
            [InlineKeyboardButton(text="Наши адреса", callback_data="addresses")],
            [InlineKeyboardButton(text="Правила отмены", callback_data="rules")],
        ]
    )

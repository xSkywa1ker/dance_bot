from __future__ import annotations

from typing import Iterable, Tuple

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


SlotButton = Tuple[int, str]


def slots_keyboard(direction_id: int, slots: Iterable[SlotButton]) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []
    for slot_id, title in slots:
        keyboard.append(
            [InlineKeyboardButton(text=title, callback_data=f"slot:{direction_id}:{slot_id}")]
        )
    keyboard.append(
        [
            InlineKeyboardButton(text="Назад", callback_data="back_to_directions"),
            InlineKeyboardButton(text="Главное меню", callback_data="back_main"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def slot_actions_keyboard(direction_id: int, slot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Записаться",
                    callback_data=f"book_slot:{direction_id}:{slot_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=f"back_to_schedule:{direction_id}",
                ),
                InlineKeyboardButton(text="Главное меню", callback_data="back_main"),
            ],
        ]
    )


__all__ = ["slots_keyboard", "slot_actions_keyboard", "SlotButton"]

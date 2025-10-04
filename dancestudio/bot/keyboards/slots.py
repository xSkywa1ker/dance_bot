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


def slot_actions_keyboard(
    direction_id: int, slot_id: int, *, booking_id: int | None = None
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="Записаться",
                callback_data=f"book_slot:{direction_id}:{slot_id}",
            )
        ]
    ]
    if booking_id is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Отменить запись",
                    callback_data=f"cancel_booking:{booking_id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=f"back_to_schedule:{direction_id}",
            ),
            InlineKeyboardButton(text="Главное меню", callback_data="back_main"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


__all__ = ["slots_keyboard", "slot_actions_keyboard", "SlotButton"]

from __future__ import annotations

from typing import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.api_client import Direction


def directions_keyboard(directions: Sequence[Direction]) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []
    for direction in directions:
        direction_id = direction.get("id")
        if not isinstance(direction_id, int):
            continue
        keyboard.append(
            [InlineKeyboardButton(text=direction.get("name", "Направление"), callback_data=f"direction:{direction_id}")]
        )
    keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


__all__ = ["directions_keyboard"]

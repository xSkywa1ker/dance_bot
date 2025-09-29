from __future__ import annotations

from typing import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.api_client import Product


def _format_price(value: float | int | None) -> str:
    if value is None:
        return ""
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text


def products_keyboard(products: Sequence[Product]) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []
    for product in products:
        product_id = product.get("id")
        if not isinstance(product_id, int):
            continue
        price = _format_price(product.get("price"))
        title = product.get("name", "Продукт")
        caption = f"{title}"
        if price:
            caption = f"{caption} · {price} ₽"
        keyboard.append([
            InlineKeyboardButton(text=caption, callback_data=f"product:{product_id}")
        ])
    keyboard.append(
        [
            InlineKeyboardButton(text="Назад", callback_data="buy_subscription"),
            InlineKeyboardButton(text="Главное меню", callback_data="back_main"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def product_actions_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Купить",
                    callback_data=f"purchase_product:{product_id}",
                )
            ],
            [
                InlineKeyboardButton(text="Назад", callback_data="buy_subscription"),
                InlineKeyboardButton(text="Главное меню", callback_data="back_main"),
            ],
        ]
    )


__all__ = ["products_keyboard", "product_actions_keyboard"]

"""Utilities for working with Telegram payments in the bot."""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Final

from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from dancestudio.bot.core.config import CURRENCY, PROVIDER, PROVIDER_TOKEN


KIND_SUBSCRIPTION: Final[str] = "subscription"
KIND_BOOKING: Final[str] = "booking"
_DESCRIPTION_MAX_LENGTH: Final[int] = 255
_TITLE_MAX_LENGTH: Final[int] = 32

_LOGGER = logging.getLogger(__name__)
_DEFAULT_INVOICE_ERROR_MESSAGE: Final[str] = (
    "Telegram отклонил счёт. Проверьте токен оплаты и настройки платежей в BotFather."
)
_KNOWN_ERROR_HINTS: Final[dict[str, str]] = {
    "PAYMENT_PROVIDER_INVALID": (
        "Telegram отклонил токен оплаты. Проверьте, что в @BotFather указан верный токен "
        "для этого бота."
    ),
    "PAYMENT_PROVIDER_MISMATCH": (
        "Токен оплаты привязан к другому боту. Получите новый токен в @BotFather."
    ),
    "CURRENCY_TOTAL_AMOUNT_INVALID": (
        "Telegram не принимает указанную сумму в выбранной валюте. Проверьте стоимость и "
        "значение переменной PAYMENT_CURRENCY."
    ),
    "CURRENCY_NOT_SUPPORTED": (
        "Выбранная валюта не поддерживается Telegram. Укажите поддерживаемую валюту в настройках."
    ),
    "AMOUNT_NOT_ENOUGH": (
        "Сумма счёта слишком мала для Telegram. Увеличьте стоимость или проверьте точность "
        "округления."
    ),
}


def payments_enabled() -> bool:
    """Return ``True`` when the bot is configured to send invoices."""

    return bool(PROVIDER_TOKEN)


def to_minor_units(amount_rub: object) -> int:
    """Convert the given amount in RUB into kopeks using half-up rounding."""

    try:
        quantized = Decimal(str(amount_rub)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid amount value: {amount_rub!r}") from exc

    minor = int(quantized * 100)
    if minor <= 0:
        raise ValueError("Amount must be >= 1 kopek")
    return minor


def build_provider_receipt(minor_amount: int, currency: str, title: str) -> str:
    """Return provider_data JSON compatible with Telegram YooKassa receipts."""

    value_rub = format(Decimal(minor_amount) / Decimal(100), ".2f")
    receipt = {
        "receipt": {
            "items": [
                {
                    "description": (title or "Оплата")[:128],
                    "quantity": "1.00",
                    "amount": {"value": value_rub, "currency": currency},
                }
            ]
        }
    }
    return json.dumps(receipt, ensure_ascii=False)


def build_payload(kind: str, order_id: str) -> str:
    return f"{kind}:{order_id}"


def parse_payload(payload: str) -> tuple[str, str] | None:
    if ":" not in payload:
        return None
    kind, order_id = payload.split(":", 1)
    if not kind or not order_id:
        return None
    return kind, order_id


async def send_invoice(
    message: Message,
    *,
    title: str,
    description: str,
    amount: float | int,
    payload: str,
) -> None:
    """Send a Telegram invoice to the user."""

    provider_token = PROVIDER_TOKEN
    if not provider_token:
        raise RuntimeError("Payment provider token is not configured")

    try:
        minor_units = to_minor_units(amount)
    except ValueError as exc:
        raise RuntimeError("Failed to prepare invoice amount") from exc

    safe_title = (title or "").strip()
    if not safe_title:
        safe_title = "Счёт"
    if len(safe_title) > _TITLE_MAX_LENGTH:
        safe_title = safe_title[:_TITLE_MAX_LENGTH].rstrip()
    if not safe_title:
        safe_title = "Счёт"

    prices = [types.LabeledPrice(label=safe_title, amount=minor_units)]

    safe_description = description.strip()
    if not safe_description:
        safe_description = safe_title
    safe_description = safe_description[:_DESCRIPTION_MAX_LENGTH]

    provider_data = build_provider_receipt(minor_units, CURRENCY, safe_title)

    _LOGGER.warning(
        "tg_invoice_debug",
        extra={
            "provider": PROVIDER,
            "currency": repr(CURRENCY),
            "minor_amount": minor_units,
            "prices_sum": sum(price.amount for price in prices),
            "provider_data": bool(provider_data),
        },
    )
    try:
        await message.answer_invoice(
            title=safe_title,
            description=safe_description,
            payload=payload,
            provider_token=provider_token,
            currency=CURRENCY,
            prices=prices,
            is_flexible=False,
            provider_data=provider_data,
        )
    except TelegramBadRequest as exc:
        error_hint = explain_invoice_error(str(exc))
        _LOGGER.warning(
            "Telegram rejected invoice: %s (payload=%s, amount_minor=%s)",
            exc,
            payload,
            minor_units,
            exc_info=True,
        )
        raise RuntimeError(error_hint) from exc


__all__ = [
    "KIND_BOOKING",
    "KIND_SUBSCRIPTION",
    "explain_invoice_error",
    "payments_enabled",
    "build_provider_receipt",
    "build_payload",
    "parse_payload",
    "send_invoice",
    "to_minor_units",
]


def explain_invoice_error(error_text: str) -> str:
    """Return a human-readable explanation for Telegram payment errors."""

    if not error_text:
        return _DEFAULT_INVOICE_ERROR_MESSAGE

    normalized = error_text.upper()
    for marker, message in _KNOWN_ERROR_HINTS.items():
        if marker in normalized:
            return message
    return _DEFAULT_INVOICE_ERROR_MESSAGE

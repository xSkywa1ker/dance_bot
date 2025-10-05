"""Utilities for working with Telegram payments in the bot."""

from __future__ import annotations
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from secrets import token_urlsafe
from typing import Final

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import LabeledPrice, Message

try:  # pragma: no cover - depends on import context
    from dancestudio.bot.config import get_settings
except ModuleNotFoundError as exc:  # pragma: no cover - fallback for demo scripts
    if exc.name and not exc.name.startswith("dancestudio"):
        raise
    from config import get_settings  # type: ignore[no-redef]


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

    settings = get_settings()
    return bool((settings.payment_provider_token or "").strip())


def _currency_code() -> str:
    settings = get_settings()
    currency = settings.payment_currency or "RUB"
    return currency.upper()


def to_minor_units(amount: float | int) -> int:
    """Convert a major currency amount into the smallest currency units."""

    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError) as exc:  # pragma: no cover - safety net
        raise ValueError(f"Invalid amount value: {amount!r}") from exc

    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    minor_units = int((quantized * 100).to_integral_value(rounding=ROUND_HALF_UP))
    return minor_units


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

    settings = get_settings()
    provider_token = (settings.payment_provider_token or "").strip()
    if not provider_token:
        raise RuntimeError("Payment provider token is not configured")

    try:
        minor_units = to_minor_units(amount)
    except ValueError as exc:
        raise RuntimeError("Failed to prepare invoice amount") from exc

    if minor_units <= 0:
        raise RuntimeError("Invoice amount must be positive")

    safe_title = (title or "").strip()
    if not safe_title:
        safe_title = "Счёт"
    if len(safe_title) > _TITLE_MAX_LENGTH:
        safe_title = safe_title[:_TITLE_MAX_LENGTH].rstrip()
    if not safe_title:
        safe_title = "Счёт"

    prices = [LabeledPrice(label=safe_title, amount=minor_units)]

    safe_description = description.strip()
    if not safe_description:
        safe_description = safe_title
    safe_description = safe_description[:_DESCRIPTION_MAX_LENGTH]
    try:
        await message.answer_invoice(
            title=safe_title,
            description=safe_description,
            payload=payload,
            provider_token=provider_token,
            currency=_currency_code(),
            prices=prices,
            start_parameter=token_urlsafe(16),
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

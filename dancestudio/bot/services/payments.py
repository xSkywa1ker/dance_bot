"""Utilities for working with Telegram payments in the bot."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from secrets import token_urlsafe
from typing import Final

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


def payments_enabled() -> bool:
    """Return ``True`` when the bot is configured to send invoices."""

    settings = get_settings()
    return bool(settings.payment_provider_token)


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
    if not settings.payment_provider_token:
        raise RuntimeError("Payment provider token is not configured")

    try:
        minor_units = to_minor_units(amount)
    except ValueError as exc:
        raise RuntimeError("Failed to prepare invoice amount") from exc

    if minor_units <= 0:
        raise RuntimeError("Invoice amount must be positive")

    prices = [LabeledPrice(label=title, amount=minor_units)]
    safe_description = description.strip()[:_DESCRIPTION_MAX_LENGTH]
    await message.answer_invoice(
        title=title,
        description=safe_description,
        payload=payload,
        provider_token=settings.payment_provider_token,
        currency=_currency_code(),
        prices=prices,
        start_parameter=token_urlsafe(16),
    )


__all__ = [
    "KIND_BOOKING",
    "KIND_SUBSCRIPTION",
    "payments_enabled",
    "build_payload",
    "parse_payload",
    "send_invoice",
    "to_minor_units",
]

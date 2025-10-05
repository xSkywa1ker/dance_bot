from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from secrets import token_urlsafe
from aiogram.types import LabeledPrice, Message

from dancestudio.bot.config import get_settings

KIND_SUBSCRIPTION = "subscription"
KIND_BOOKING = "booking"


def payments_enabled() -> bool:
    settings = get_settings()
    return bool(settings.payment_provider_token)


def _currency_code() -> str:
    settings = get_settings()
    currency = settings.payment_currency or "RUB"
    return currency.upper()


def to_minor_units(amount: float | int) -> int:
    value = Decimal(str(amount))
    return int((value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100).to_integral_value())


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
    settings = get_settings()
    if not settings.payment_provider_token:
        raise RuntimeError("Payment provider token is not configured")
    prices = [LabeledPrice(label=title, amount=to_minor_units(amount))]
    safe_description = description.strip()[:255]
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

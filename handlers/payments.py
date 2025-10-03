"""Payment-related Telegram bot handlers using Telegram Bot Payments API."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery
from aiogram.utils.payload import generate_payload
from aiogram import F

from config import get_settings


router = Router()
settings = get_settings()


@router.message(Command("buy"))
async def handle_buy_command(message: Message) -> None:
    """Send an invoice for the premium subscription purchase."""

    payload: str = generate_payload()
    prices = [LabeledPrice(label=settings.item_title, amount=settings.price_cents)]

    await message.answer_invoice(
        title=settings.item_title,
        description=settings.item_description[:255],
        payload=payload,
        provider_token=settings.provider_token,
        currency=settings.currency,
        prices=prices,
        need_name=False,
        need_email=False,
        need_phone_number=False,
        need_shipping_address=False,
    )


@router.pre_checkout_query()
async def handle_pre_checkout_query(pre_checkout_query: PreCheckoutQuery) -> None:
    """Acknowledge the pre-checkout query to allow the payment to proceed."""

    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message) -> None:
    """Respond to the user after a successful payment."""

    successful_payment = message.successful_payment
    if successful_payment is None:  # Defensive guard for type checkers.
        return

    order_id = successful_payment.invoice_payload

    text = (
        "✅ Оплата прошла успешно!\n"
        f"Заказ: `{order_id}`\n"
        f"Сумма: {successful_payment.total_amount / 100:.2f} {successful_payment.currency}\n"
        f"tg_charge_id: `{successful_payment.telegram_payment_charge_id}`\n"
        f"provider_charge_id: `{successful_payment.provider_payment_charge_id}`"
    )

    await message.answer(text, parse_mode="Markdown")

    # Здесь можно сохранить платёж и order_id в базу данных проекта.

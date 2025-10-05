from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery
from httpx import HTTPError

from dancestudio.bot.services import api_client
from dancestudio.bot.services import payments as payment_services
from dancestudio.bot.utils import texts

router = Router()


@router.pre_checkout_query()
async def handle_pre_checkout_query(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message) -> None:
    successful_payment = message.successful_payment
    if successful_payment is None:
        return
    payload_data = successful_payment.invoice_payload or ""
    parsed = payment_services.parse_payload(payload_data)
    if not parsed:
        await message.answer("✅ Оплата прошла успешно.")
        return
    kind, order_id = parsed
    provider_payment_id = successful_payment.provider_payment_charge_id or None
    try:
        await api_client.confirm_payment(
            order_id=order_id,
            status="paid",
            provider_payment_id=provider_payment_id,
        )
    except HTTPError:
        await message.answer(
            "Оплата прошла, но не удалось подтвердить её в системе. "
            "Пожалуйста, свяжитесь с администратором."
        )
        return

    if kind == payment_services.KIND_SUBSCRIPTION:
        await message.answer(texts.SUBSCRIPTION_PURCHASE_SUCCESS)
    elif kind == payment_services.KIND_BOOKING:
        await message.answer(texts.CLASS_PURCHASE_SUCCESS)
    else:
        await message.answer("✅ Оплата прошла успешно.")


__all__ = ["router"]

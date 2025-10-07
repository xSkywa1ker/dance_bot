"""Payment-related Telegram bot handlers using Telegram Bot Payments API."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery
from aiogram.utils.payload import generate_payload
from aiogram import F

from config import get_settings


router = Router()
settings = get_settings()


class BookingForm(StatesGroup):
    """Conversation steps for collecting booking data before payment."""

    waiting_for_age = State()
    waiting_for_full_name = State()


async def _send_invoice(message: Message) -> None:
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


@router.message(Command("buy"))
async def handle_buy_command(message: Message, state: FSMContext) -> None:
    """Start the booking flow by requesting the user's age."""

    await state.clear()
    await state.set_state(BookingForm.waiting_for_age)
    await message.answer("Введите ваш возраст")


@router.message(BookingForm.waiting_for_age, F.text)
async def handle_age_input(message: Message, state: FSMContext) -> None:
    """Validate and store the provided age before asking for a full name."""

    raw_age = message.text.strip()
    if not raw_age.isdigit():
        await message.answer("Пожалуйста, отправьте возраст числом, например: 25")
        return

    age = int(raw_age)
    if age <= 0 or age > 120:
        await message.answer("Укажите реальный возраст в диапазоне от 1 до 120 лет.")
        return

    await state.update_data(age=age)
    await state.set_state(BookingForm.waiting_for_full_name)
    await message.answer("Введите ваше ФИО")


@router.message(BookingForm.waiting_for_full_name, F.text)
async def handle_full_name_input(message: Message, state: FSMContext) -> None:
    """Store the user's full name, confirm the booking and send the invoice."""

    full_name = message.text.strip()
    if not full_name:
        await message.answer("ФИО не может быть пустым. Попробуйте ещё раз.")
        return

    await state.update_data(full_name=full_name)
    await state.clear()

    await message.answer("Бронь создана, оплатите, пожалуйста")
    await _send_invoice(message)


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

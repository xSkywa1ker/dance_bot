from __future__ import annotations

import ipaddress
from datetime import datetime
from json import JSONDecodeError
from typing import Mapping
from zoneinfo import ZoneInfo

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)
from httpx import HTTPError
from urllib.parse import urlparse

from dancestudio.bot.config import get_settings
from dancestudio.bot.keyboards import (
    directions_keyboard,
    product_actions_keyboard,
    products_keyboard,
    main_menu_keyboard,
    slots_keyboard,
    slot_actions_keyboard,
)
from dancestudio.bot.services import (
    create_booking,
    cancel_booking,
    create_subscription_payment,
    fetch_directions,
    fetch_products,
    fetch_slots,
    fetch_bookings,
    fetch_subscriptions,
    sync_user,
    fetch_studio_addresses,
)
from dancestudio.bot.services import payments as payment_services
from dancestudio.bot.services.api_client import Direction
from dancestudio.bot.utils import texts


logger = logging.getLogger(__name__)
from states.booking import BookingStates

router = Router()
_settings = get_settings()
_timezone = ZoneInfo(_settings.timezone)

_KEEP_FULL_NAME_CALLBACK = "profile:keep_full_name"
_KEEP_AGE_CALLBACK = "profile:keep_age"
_PENDING_SLOT_KEY = "pending_slot_id"
_PENDING_PRODUCT_KEY = "pending_product_id"
_EXISTING_FULL_NAME_KEY = "existing_full_name"
_EXISTING_AGE_KEY = "existing_age"


async def _safe_edit_message(
    message: Message, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> None:
    current_text = message.html_text or message.text or ""
    new_markup_dump = reply_markup.model_dump() if reply_markup else None
    existing_markup_dump = (
        message.reply_markup.model_dump() if message.reply_markup else None
    )
    if current_text == text and existing_markup_dump == new_markup_dump:
        return
    await message.edit_text(text, reply_markup=reply_markup)


def _is_allowed_payment_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    hostname = (parsed.hostname or "").lower()
    if not hostname or hostname == "localhost" or hostname.endswith(".local"):
        return False
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved:
        return False
    return True


def _resolve_payment_url(raw_value: object) -> str | None:
    if not isinstance(raw_value, str):
        return None
    value = raw_value.strip()
    if not value:
        return None
    if _is_allowed_payment_url(value):
        return value
    fallback = _settings.payment_fallback_url.strip()
    if fallback and _is_allowed_payment_url(fallback):
        return fallback
    return None


def _format_slot_time(slot: Mapping[str, object]) -> tuple[str, str]:
    raw_starts_at = slot.get("starts_at", "")
    if isinstance(raw_starts_at, str) and raw_starts_at.endswith("Z"):
        raw_starts_at = raw_starts_at.replace("Z", "+00:00")
    if not isinstance(raw_starts_at, str):
        return "", ""
    try:
        dt = datetime.fromisoformat(raw_starts_at)
    except ValueError:
        return "", ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    dt_local = dt.astimezone(_timezone)
    short_label = dt_local.strftime("%d.%m %H:%M")
    long_label = dt_local.strftime("%d.%m.%Y %H:%M")
    return short_label, long_label


def _format_reservation_deadline(raw_value: object) -> str:
    if not isinstance(raw_value, str):
        return ""
    value = raw_value.replace("Z", "+00:00") if raw_value.endswith("Z") else raw_value
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    dt_local = dt.astimezone(_timezone)
    now_local = datetime.now(_timezone)
    if dt_local.date() == now_local.date():
        return dt_local.strftime("%H:%M")
    return dt_local.strftime("%d.%m %H:%M")


def _format_subscription_valid_to(raw_value: object) -> str:
    if not isinstance(raw_value, str):
        return ""
    value = raw_value.replace("Z", "+00:00") if raw_value.endswith("Z") else raw_value
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(_timezone).strftime("%d.%m.%Y")


def _direction_title(direction: Direction) -> str:
    name = direction.get("name", "Направление")
    return texts.direction_schedule_title(name)


def _chunked(sequence: list, size: int) -> list[list]:
    return [sequence[i : i + size] for i in range(0, len(sequence), size)]


def _extract_full_name(user_payload: Mapping[str, object] | None) -> str | None:
    if not user_payload:
        return None
    value = user_payload.get("full_name")
    if isinstance(value, str):
        value = value.strip()
        if value:
            return value
    return None


def _is_valid_age(age: int) -> bool:
    return 3 <= age <= 120


def _extract_age(user_payload: Mapping[str, object] | None) -> int | None:
    if not user_payload:
        return None
    value = user_payload.get("age")
    try:
        age = int(value)
    except (TypeError, ValueError):
        return None
    return age if _is_valid_age(age) else None


async def _prompt_full_name(
    message: Message,
    state: FSMContext,
    existing_full_name: str | None = None,
) -> None:
    if not message:
        return
    await state.set_state(BookingStates.ask_full_name)
    if existing_full_name:
        await state.update_data(**{_EXISTING_FULL_NAME_KEY: existing_full_name})
    keyboard: InlineKeyboardMarkup | None = None
    if existing_full_name:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=texts.keep_full_name_button(existing_full_name),
                        callback_data=_KEEP_FULL_NAME_CALLBACK,
                    )
                ]
            ]
        )
    await message.answer(
        texts.ask_full_name(existing_full_name),
        reply_markup=keyboard,
    )


async def _prompt_age(
    message: Message,
    state: FSMContext,
    existing_age: int | None = None,
) -> None:
    if not message:
        return
    await state.set_state(BookingStates.ask_age)
    if existing_age is not None:
        await state.update_data(**{_EXISTING_AGE_KEY: existing_age})
    keyboard: InlineKeyboardMarkup | None = None
    if existing_age is not None:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=texts.keep_age_button(existing_age),
                        callback_data=_KEEP_AGE_CALLBACK,
                    )
                ]
            ]
        )
    await message.answer(
        texts.ask_age(existing_age),
        reply_markup=keyboard,
    )


async def _ensure_profile(
    message: Message,
    state: FSMContext,
    user_payload: Mapping[str, object] | None,
    *,
    slot_id: int | None = None,
    product_id: int | None = None,
    require_age: bool = True,
) -> bool:
    if not message:
        return True
    pending_updates: dict[str, object] = {}
    if slot_id is not None:
        pending_updates[_PENDING_SLOT_KEY] = slot_id
    if product_id is not None:
        pending_updates[_PENDING_PRODUCT_KEY] = product_id
    full_name = _extract_full_name(user_payload)
    if not full_name:
        if pending_updates:
            await state.update_data(**pending_updates)
        await _prompt_full_name(message, state)
        return False
    if require_age:
        age = _extract_age(user_payload)
        if age is None:
            if pending_updates:
                await state.update_data(**pending_updates)
            await _prompt_age(message, state)
            return False
    return True


async def _prompt_profile_if_incomplete(
    message: Message,
    state: FSMContext,
    user_payload: Mapping[str, object] | None,
) -> None:
    if not message or not user_payload:
        return
    if await _ensure_profile(message, state, user_payload):
        await state.clear()


async def _complete_pending_booking(
    message: Message,
    state: FSMContext,
    user_payload: Mapping[str, object] | None,
) -> None:
    data = await state.get_data()
    product_id = data.get(_PENDING_PRODUCT_KEY)
    if isinstance(product_id, int):
        await state.clear()
        await _complete_pending_purchase(message, state, user_payload, product_id)
        return
    slot_id = data.get(_PENDING_SLOT_KEY)
    if not isinstance(slot_id, int):
        await state.clear()
        return
    if not message or not message.from_user:
        await state.clear()
        return
    if not await _ensure_profile(message, state, user_payload, slot_id=slot_id):
        return
    await state.clear()
    await _perform_booking_flow(
        user=message.from_user,
        message=message,
        slot_id=slot_id,
        state=state,
        callback=None,
        user_payload=user_payload,
    )


async def _process_subscription_purchase(
    *,
    user,
    message: Message,
    product_id: int,
    state: FSMContext,
    user_payload: Mapping[str, object] | None,
    callback: CallbackQuery | None = None,
) -> None:
    try:
        products = await fetch_products()
    except HTTPError:
        if callback:
            await callback.answer(texts.API_ERROR, show_alert=True)
        else:
            await message.answer(texts.API_ERROR)
        return

    product = next((item for item in products if item.get("id") == product_id), None)
    if not product:
        if callback:
            await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        else:
            await message.answer(texts.ITEM_NOT_FOUND)
        return

    try:
        payment_response = await create_subscription_payment(
            tg_id=user.id,
            product_id=product_id,
            full_name=_extract_full_name(user_payload),
            age=_extract_age(user_payload),
        )
    except HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            error_text = texts.ITEM_NOT_FOUND
        elif exc.response is not None and exc.response.status_code == 400:
            detail = exc.response.json()
            error_text = detail.get("detail") if isinstance(detail, dict) else None
            if not isinstance(error_text, str) or not error_text:
                error_text = texts.API_ERROR
        else:
            error_text = texts.API_ERROR
        if callback:
            await callback.answer(error_text, show_alert=True)
        else:
            await message.answer(error_text)
        return

    raw_price = product.get("price")
    price = texts.format_price(raw_price)
    provider = str(payment_response.get("provider") or "")
    order_id = payment_response.get("order_id")
    amount_value = payment_response.get("amount")
    try:
        invoice_amount = float(amount_value) if amount_value is not None else None
    except (TypeError, ValueError):
        invoice_amount = None
    if invoice_amount is None:
        try:
            invoice_amount = float(raw_price) if raw_price is not None else None
        except (TypeError, ValueError):
            invoice_amount = None

    invoice_sent = False
    invoice_error: str | None = None
    invoice_text = texts.subscription_payment_details(
        product.get("name", ""), price or None, via_invoice=True
    )
    if (
        provider == "telegram"
        and payment_services.payments_enabled()
        and isinstance(order_id, str)
        and order_id.strip()
        and invoice_amount is not None
    ):
        try:
            payload_value = payment_services.build_payload(
                payment_services.KIND_SUBSCRIPTION, order_id
            )
            await payment_services.send_invoice(
                message,
                title=product.get("name", "Абонемент") or "Абонемент",
                description=invoice_text,
                amount=invoice_amount,
                payload=payload_value,
            )
            invoice_sent = True
        except RuntimeError as exc:
            invoice_error = str(exc)
            invoice_sent = False
            logger.warning(
                "Failed to send Telegram invoice for subscription order %s: %s",
                order_id,
                exc,
            )
        except TelegramBadRequest as exc:
            invoice_error = payment_services.explain_invoice_error(str(exc))
            invoice_sent = False
            logger.exception(
                "Telegram API rejected subscription invoice for order %s", order_id
            )

    buttons: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="Главное меню", callback_data="back_main")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    if invoice_sent:
        if message.from_user and message.from_user.is_bot:
            await _safe_edit_message(message, invoice_text, reply_markup=markup)
        else:
            await message.answer(invoice_text, reply_markup=markup)
        if callback:
            await callback.answer("Счёт на оплату отправлен")
    else:
        payment_url = _resolve_payment_url(payment_response.get("payment_url"))
        link_available = payment_url is not None
        text = texts.subscription_payment_details(
            product.get("name", ""), price or None, link_available=link_available
        )
        if payment_url:
            buttons = [[InlineKeyboardButton(text="Оплатить", url=payment_url)]] + buttons
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        if message.from_user and message.from_user.is_bot:
            await _safe_edit_message(message, text, reply_markup=markup)
        else:
            await message.answer(text, reply_markup=markup)
        if callback:
            if link_available:
                await callback.answer("Ссылка на оплату отправлена")
            else:
                alert_text = texts.payment_invoice_error(invoice_error)
                await callback.answer(alert_text, show_alert=True)
        elif not link_available:
            alert_text = texts.payment_invoice_error(invoice_error)
            await message.answer(alert_text)

    await _prompt_profile_if_incomplete(message, state, user_payload)


async def _complete_pending_purchase(
    message: Message,
    state: FSMContext,
    user_payload: Mapping[str, object] | None,
    product_id: int,
) -> None:
    user = message.from_user
    if not user:
        await message.answer(texts.API_ERROR)
        return
    await _process_subscription_purchase(
        user=user,
        message=message,
        product_id=product_id,
        state=state,
        user_payload=user_payload,
        callback=None,
    )


async def _answer_interaction(
    callback: CallbackQuery | None,
    message: Message,
    *,
    text: str | None = None,
    show_alert: bool = False,
) -> None:
    if callback:
        await callback.answer(text, show_alert=show_alert)
    elif text:
        await message.answer(text)


async def _perform_booking_flow(
    *,
    user,
    message: Message,
    slot_id: int,
    state: FSMContext,
    callback: CallbackQuery | None,
    user_payload: Mapping[str, object] | None,
) -> None:
    full_name = _extract_full_name(user_payload)
    age = _extract_age(user_payload)
    try:
        booking = await create_booking(
            tg_id=user.id,
            slot_id=slot_id,
            full_name=full_name,
            age=age,
        )
    except HTTPError as exc:
        if exc.response is not None:
            status_code = exc.response.status_code
            detail_text: str | None = None
            try:
                detail = exc.response.json()
            except (ValueError, JSONDecodeError):
                detail = None
            if isinstance(detail, dict):
                detail_text = detail.get("detail")
            elif isinstance(detail, str):
                detail_text = detail
            if status_code == 409 and detail_text == "Already booked":
                await _answer_interaction(callback, message, text=texts.ALREADY_BOOKED, show_alert=True)
            elif status_code == 409 and detail_text == "Slot start time is in the past":
                await _answer_interaction(callback, message, text=texts.PAST_SLOT_ERROR, show_alert=True)
            elif status_code == 409 and detail_text == "No free seats":
                await _answer_interaction(callback, message, text=texts.NO_SEATS_ERROR, show_alert=True)
            else:
                message_text = detail_text if isinstance(detail_text, str) else texts.API_ERROR
                await _answer_interaction(callback, message, text=message_text, show_alert=True)
        else:
            await _answer_interaction(callback, message, text=texts.API_ERROR, show_alert=True)
        return

    slot = booking.get("slot", {})
    _, long_label = _format_slot_time(slot)
    direction_name = slot.get("direction_name", "")
    price_label = texts.format_price(slot.get("price_single_visit"))
    reply_markup: InlineKeyboardMarkup | None = None
    callback_text: str | None = None
    callback_alert = False
    payments_available = payment_services.payments_enabled()
    if booking.get("needs_payment"):
        provider = str(booking.get("payment_provider") or "")
        order_id = booking.get("payment_order_id")
        amount_value = booking.get("payment_amount")
        try:
            invoice_amount = float(amount_value) if amount_value is not None else None
        except (TypeError, ValueError):
            invoice_amount = None
        if invoice_amount is None:
            try:
                invoice_amount = (
                    float(slot.get("price_single_visit"))
                    if slot.get("price_single_visit") is not None
                    else None
                )
            except (TypeError, ValueError):
                invoice_amount = None
        invoice_text = texts.booking_payment_required(
            direction_name, long_label, price_label or None, via_invoice=True
        )
        invoice_sent = False
        invoice_error: str | None = None
        if (
            provider == "telegram"
            and payments_available
            and isinstance(order_id, str)
            and order_id.strip()
            and invoice_amount is not None
        ):
            try:
                payload_value = payment_services.build_payload(
                    payment_services.KIND_BOOKING, order_id
                )
                await payment_services.send_invoice(
                    message,
                    title=direction_name or "Занятие",
                    description=invoice_text,
                    amount=invoice_amount,
                    payload=payload_value,
                )
                invoice_sent = True
            except RuntimeError as exc:
                invoice_error = str(exc)
                invoice_sent = False
                logger.warning(
                    "Failed to send Telegram invoice for booking order %s: %s",
                    order_id,
                    exc,
                )
            except TelegramBadRequest as exc:
                invoice_error = payment_services.explain_invoice_error(str(exc))
                invoice_sent = False
                logger.exception(
                    "Telegram API rejected booking invoice for order %s", order_id
                )

        if invoice_sent:
            reply_markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Мои записи", callback_data="my_bookings")],
                    [InlineKeyboardButton(text="Главное меню", callback_data="back_main")],
                ]
            )
            text = invoice_text
            callback_text = "Счёт на оплату отправлен"
        else:
            payment_url = _resolve_payment_url(booking.get("payment_url"))
            link_available = payment_url is not None
            buttons: list[list[InlineKeyboardButton]] = []
            if payment_url:
                buttons.append([InlineKeyboardButton(text="Оплатить", url=payment_url)])
            buttons.append(
                [InlineKeyboardButton(text="Мои записи", callback_data="my_bookings")]
            )
            buttons.append(
                [InlineKeyboardButton(text="Главное меню", callback_data="back_main")]
            )
            reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            text = texts.booking_payment_required(
                direction_name,
                long_label,
                price_label or None,
                link_available=link_available,
            )
            if link_available:
                callback_text = "Ссылка на оплату отправлена"
            else:
                callback_text = texts.payment_invoice_error(invoice_error)
                callback_alert = True
    else:
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Мои записи", callback_data="my_bookings")],
                [InlineKeyboardButton(text="Главное меню", callback_data="back_main")],
            ]
        )
        text = texts.booking_confirmed(direction_name, long_label)

    await _safe_edit_message(message, texts.MAIN_MENU, reply_markup=main_menu_keyboard())
    await message.answer(text, reply_markup=reply_markup)
    if callback:
        if callback_text:
            await callback.answer(callback_text, show_alert=callback_alert)
        else:
            await callback.answer()
    await _prompt_profile_if_incomplete(message, state, user_payload)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.from_user:
        try:
            await sync_user(
                tg_id=message.from_user.id,
                full_name=message.from_user.full_name,
            )
        except HTTPError:
            pass
    await message.answer(texts.MAIN_MENU, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "rules")
async def show_rules(callback: CallbackQuery) -> None:
    await _safe_edit_message(
        callback.message,
        texts.CANCEL_RULES,
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "addresses")
async def show_addresses(callback: CallbackQuery) -> None:
    try:
        result = await fetch_studio_addresses()
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return
    text = texts.studio_addresses(result.get("addresses"))
    await _safe_edit_message(
        callback.message,
        text,
        reply_markup=main_menu_keyboard(),
    )
    media_payload = result.get("media") if isinstance(result.get("media"), list) else []
    media_group: list[InputMediaPhoto | InputMediaVideo] = []
    for item in media_payload:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str) or not url:
            continue
        media_type = str(item.get("media_type") or "image")
        if media_type == "video":
            media_group.append(InputMediaVideo(media=url))
        else:
            media_group.append(InputMediaPhoto(media=url))
    for chunk in _chunked(media_group, 10):
        if not chunk:
            continue
        try:
            await callback.message.answer_media_group(chunk)
        except TelegramBadRequest:
            logger.exception("Failed to send studio address media group")
            break
    await callback.answer()


async def _compose_bookings_view(
    tg_id: int,
) -> tuple[str, InlineKeyboardMarkup, list[Mapping[str, object]]]:
    bookings = await fetch_bookings(tg_id=tg_id)
    try:
        subscriptions = await fetch_subscriptions(tg_id=tg_id)
    except HTTPError:
        subscriptions = None

    items: list[dict[str, object]] = []
    pay_rows: list[list[InlineKeyboardButton]] = []
    cancel_rows: list[list[InlineKeyboardButton]] = []
    payments_available = payment_services.payments_enabled()
    for booking in bookings:
        slot = booking.get("slot", {})
        short_label, _ = _format_slot_time(slot)
        direction_name = slot.get("direction_name", "") or "Занятие"
        title = f"{short_label} · {direction_name}" if short_label else direction_name
        status = str(booking.get("status", ""))
        entry: dict[str, object] = {"title": title, "status": status}
        booking_id = booking.get("id")
        if status == "reserved":
            note_parts = ["не оплачено"]
            deadline_label = _format_reservation_deadline(
                booking.get("reservation_expires_at")
            )
            if deadline_label:
                entry["payment_due"] = deadline_label
            payment_provider = str(booking.get("payment_provider") or "")
            payment_order_id = booking.get("payment_order_id")
            invoice_available = (
                payment_provider == "telegram"
                and payments_available
                and isinstance(booking_id, int)
                and isinstance(payment_order_id, str)
                and payment_order_id.strip()
            )
            if invoice_available:
                button_text = (
                    f"Оплатить · {short_label}" if short_label else "Оплатить"
                )
                pay_rows.append(
                    [
                        InlineKeyboardButton(
                            text=button_text,
                            callback_data=f"pay_booking:{booking_id}",
                        )
                    ]
                )
                note_parts.append("оплатите через Telegram")
            else:
                payment_url = _resolve_payment_url(booking.get("payment_url"))
                if payment_url:
                    button_text = (
                        f"Оплатить · {short_label}" if short_label else "Оплатить"
                    )
                    pay_rows.append(
                        [InlineKeyboardButton(text=button_text, url=payment_url)]
                    )
                else:
                    note_parts.append(texts.PAYMENT_LINK_UNAVAILABLE_NOTE)
            entry["note"] = " · ".join(note_parts)
        items.append(entry)

        if (
            isinstance(booking_id, int)
            and status in {"reserved", "confirmed"}
        ):
            button_text = (
                f"Отменить · {short_label}" if short_label else "Отменить запись"
            )
            cancel_rows.append(
                [
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"cancel_booking:{booking_id}",
                    )
                ]
            )

    sections: list[str] = [texts.bookings_list(items)]
    if subscriptions is not None:
        subscription_items: list[dict[str, object]] = []
        for subscription in subscriptions:
            valid_to_label = _format_subscription_valid_to(
                subscription.get("valid_to")
            )
            subscription_items.append(
                {
                    "product_name": subscription.get("product_name"),
                    "remaining_classes": subscription.get("remaining_classes"),
                    "total_classes": subscription.get("total_classes"),
                    "valid_to_label": valid_to_label,
                }
            )
        sections.append(texts.subscriptions_summary(subscription_items))

    text = "\n\n".join(section for section in sections if section)
    keyboard_rows: list[list[InlineKeyboardButton]] = [*pay_rows, *cancel_rows]
    keyboard_rows.append(
        [InlineKeyboardButton(text="Обновить", callback_data="my_bookings")]
    )
    keyboard_rows.append(
        [InlineKeyboardButton(text="Главное меню", callback_data="back_main")]
    )
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    return text, reply_markup, bookings


@router.callback_query(F.data == "my_bookings")
async def my_bookings(callback: CallbackQuery) -> None:
    user = callback.from_user
    if not user:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return
    try:
        await sync_user(tg_id=user.id, full_name=user.full_name)
    except HTTPError:
        pass
    try:
        text, reply_markup, _ = await _compose_bookings_view(user.id)
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return
    await _safe_edit_message(callback.message, text, reply_markup=reply_markup)
    await callback.answer()


@router.callback_query(F.data == "buy_subscription")
async def show_products(callback: CallbackQuery) -> None:
    try:
        products = await fetch_products()
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return

    if not products:
        await _safe_edit_message(
            callback.message,
            texts.NO_PRODUCTS,
            reply_markup=main_menu_keyboard(),
        )
        await callback.answer()
        return

    await _safe_edit_message(
        callback.message,
        texts.PRODUCTS_PROMPT,
        reply_markup=products_keyboard(products),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("product:"))
async def product_details(callback: CallbackQuery) -> None:
    try:
        product_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    try:
        products = await fetch_products()
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return

    product = next((item for item in products if item.get("id") == product_id), None)
    if not product:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    await _safe_edit_message(
        callback.message,
        texts.product_details(product),
        reply_markup=product_actions_keyboard(product_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("purchase_product:"))
async def purchase_product(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    message = callback.message
    if not user or not message:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return
    try:
        product_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    try:
        user_payload = await sync_user(tg_id=user.id, full_name=user.full_name)
    except HTTPError:
        user_payload = None

    if not await _ensure_profile(
        message, state, user_payload, product_id=product_id, require_age=False
    ):
        await callback.answer(texts.PROFILE_DETAILS_REQUIRED, show_alert=True)
        return

    await _process_subscription_purchase(
        user=user,
        message=message,
        product_id=product_id,
        state=state,
        callback=callback,
        user_payload=user_payload,
    )


@router.callback_query(F.data == "book_class")
async def choose_direction(callback: CallbackQuery) -> None:
    try:
        directions = await fetch_directions()
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return

    if not directions:
        await callback.answer(texts.NO_DIRECTIONS, show_alert=True)
        return

    await _safe_edit_message(
        callback.message,
        texts.DIRECTIONS_PROMPT,
        reply_markup=directions_keyboard(directions),
    )
    await callback.answer()


async def _show_direction(callback: CallbackQuery, direction_id: int) -> None:
    try:
        directions = await fetch_directions()
        slots = await fetch_slots(direction_id=direction_id)
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return

    direction = next((item for item in directions if item.get("id") == direction_id), None)
    if not direction:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    if not slots:
        await _safe_edit_message(
            callback.message,
            texts.no_slots(direction.get("name", "")),
            reply_markup=directions_keyboard(directions),
        )
        await callback.answer()
        return

    slot_buttons: list[tuple[int, str]] = []
    for slot in slots:
        short_label, _ = _format_slot_time(slot)
        slot_id = slot.get("id")
        if not isinstance(slot_id, int):
            continue
        if short_label:
            text = f"{short_label} · {slot.get('duration_min', 0)} мин"
        else:
            text = f"Занятие #{slot_id}"
        slot_buttons.append((slot_id, text))

    if not slot_buttons:
        await _safe_edit_message(
            callback.message,
            texts.no_slots(direction.get("name", "")),
            reply_markup=directions_keyboard(directions),
        )
        await callback.answer()
        return

    await _safe_edit_message(
        callback.message,
        _direction_title(direction),
        reply_markup=slots_keyboard(direction_id, slot_buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("direction:"))
async def show_direction_schedule(callback: CallbackQuery) -> None:
    try:
        direction_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return
    await _show_direction(callback, direction_id)


@router.callback_query(F.data.startswith("slot:"))
async def show_slot_details(callback: CallbackQuery) -> None:
    try:
        _, direction_id_str, slot_id_str = callback.data.split(":", 2)
        direction_id = int(direction_id_str)
        slot_id = int(slot_id_str)
    except (ValueError, IndexError):
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    try:
        directions = await fetch_directions()
        slots = await fetch_slots(direction_id=direction_id)
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return

    direction = next((item for item in directions if item.get("id") == direction_id), None)
    slot = next((item for item in slots if item.get("id") == slot_id), None)

    if not direction or not slot:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    existing_booking: Mapping[str, object] | None = None
    existing_booking_id: int | None = None
    if callback.from_user:
        try:
            user_bookings = await fetch_bookings(tg_id=callback.from_user.id)
        except HTTPError:
            user_bookings = None
        if user_bookings:
            for booking in user_bookings:
                slot_info = booking.get("slot", {})
                if (
                    isinstance(slot_info, Mapping)
                    and slot_info.get("id") == slot_id
                    and str(booking.get("status", "")) in {"reserved", "confirmed"}
                ):
                    booking_id = booking.get("id")
                    if isinstance(booking_id, int):
                        existing_booking = booking
                        existing_booking_id = booking_id
                        break

    _, long_label = _format_slot_time(slot)
    slot_text = texts.slot_details(direction.get("name", ""), slot, long_label)
    payment_button: InlineKeyboardButton | None = None
    if existing_booking and existing_booking_id is not None:
        status_value = str(existing_booking.get("status") or "")
        if status_value == "reserved":
            payments_available = payment_services.payments_enabled()
            provider = str(existing_booking.get("payment_provider") or "")
            order_id = existing_booking.get("payment_order_id")
            if (
                provider == "telegram"
                and payments_available
                and isinstance(order_id, str)
                and order_id.strip()
            ):
                payment_button = InlineKeyboardButton(
                    text="Оплатить",
                    callback_data=f"pay_booking:{existing_booking_id}",
                )
            else:
                payment_url = _resolve_payment_url(existing_booking.get("payment_url"))
                if payment_url:
                    payment_button = InlineKeyboardButton(
                        text="Оплатить",
                        url=payment_url,
                    )
    await _safe_edit_message(
        callback.message,
        slot_text,
        reply_markup=slot_actions_keyboard(
            direction_id,
            slot_id,
            booking_id=existing_booking_id,
            payment_button=payment_button,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back_to_schedule:"))
async def back_to_schedule(callback: CallbackQuery) -> None:
    try:
        direction_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return
    await _show_direction(callback, direction_id)


@router.callback_query(F.data.startswith("book_slot:"))
async def book_slot(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    message = callback.message
    if not user or not message:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return
    try:
        _, _, slot_id_str = callback.data.split(":", 2)
        slot_id = int(slot_id_str)
    except (ValueError, IndexError):
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    try:
        user_payload = await sync_user(tg_id=user.id, full_name=user.full_name)
    except HTTPError:
        user_payload = None

    if not await _ensure_profile(message, state, user_payload, slot_id=slot_id):
        await callback.answer(texts.PROFILE_DETAILS_REQUIRED, show_alert=True)
        return

    await _perform_booking_flow(
        user=user,
        message=message,
        slot_id=slot_id,
        state=state,
        callback=callback,
        user_payload=user_payload,
    )


@router.callback_query(F.data.startswith("pay_booking:"))
async def send_booking_invoice(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    message = callback.message
    if not user or not message:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return
    try:
        booking_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    try:
        user_payload = await sync_user(tg_id=user.id, full_name=user.full_name)
    except HTTPError:
        user_payload = None

    try:
        bookings = await fetch_bookings(tg_id=user.id)
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return

    booking = next((item for item in bookings if item.get("id") == booking_id), None)
    if not booking or booking.get("status") != "reserved":
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    provider = str(booking.get("payment_provider") or "")
    payments_available = payment_services.payments_enabled()
    order_id = booking.get("payment_order_id")
    if (
        provider != "telegram"
        or not payments_available
        or not isinstance(order_id, str)
        or not order_id.strip()
    ):
        await callback.answer(texts.PAYMENT_LINK_UNAVAILABLE_ALERT, show_alert=True)
        return

    amount_value = booking.get("payment_amount")
    try:
        invoice_amount = float(amount_value) if amount_value is not None else None
    except (TypeError, ValueError):
        invoice_amount = None
    slot = booking.get("slot", {})
    if invoice_amount is None:
        try:
            invoice_amount = (
                float(slot.get("price_single_visit"))
                if slot.get("price_single_visit") is not None
                else None
            )
        except (TypeError, ValueError):
            invoice_amount = None
    if invoice_amount is None:
        await callback.answer(texts.PAYMENT_LINK_UNAVAILABLE_ALERT, show_alert=True)
        return

    _, long_label = _format_slot_time(slot)
    direction_name = slot.get("direction_name", "")
    price_label = texts.format_price(slot.get("price_single_visit"))
    invoice_text = texts.booking_payment_required(
        direction_name, long_label, price_label or None, via_invoice=True
    )

    try:
        payload_value = payment_services.build_payload(
            payment_services.KIND_BOOKING, order_id
        )
        await payment_services.send_invoice(
            message,
            title=direction_name or "Занятие",
            description=invoice_text,
            amount=invoice_amount,
            payload=payload_value,
        )
    except (TelegramBadRequest, RuntimeError):
        await callback.answer(texts.PAYMENT_LINK_UNAVAILABLE_ALERT, show_alert=True)
        return

    reply_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Мои записи", callback_data="my_bookings")],
            [InlineKeyboardButton(text="Главное меню", callback_data="back_main")],
        ]
    )
    await message.answer(invoice_text, reply_markup=reply_markup)
    await callback.answer("Счёт на оплату отправлен")
    await _prompt_profile_if_incomplete(message, state, user_payload)


@router.callback_query(F.data.startswith("cancel_booking:"))
async def cancel_booking_callback(callback: CallbackQuery) -> None:
    user = callback.from_user
    message = callback.message
    if not user or not message:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return
    try:
        booking_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    try:
        booking = await cancel_booking(tg_id=user.id, booking_id=booking_id)
    except HTTPError as exc:
        if exc.response is not None:
            detail = exc.response.json()
            detail_text = detail.get("detail") if isinstance(detail, dict) else None
            status_code = exc.response.status_code
            if status_code == 404:
                await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
            else:
                await callback.answer(detail_text or texts.API_ERROR, show_alert=True)
        else:
            await callback.answer(texts.API_ERROR, show_alert=True)
        return

    slot = booking.get("slot", {})
    _, long_label = _format_slot_time(slot)
    direction_name = slot.get("direction_name", "")
    status_value = str(booking.get("status", ""))

    if status_value == "late_cancel":
        await callback.answer(texts.BOOKING_CANCEL_TOO_LATE, show_alert=True)
        return

    if status_value != "canceled":
        await callback.answer(texts.BOOKING_CANCEL_ERROR, show_alert=True)
        return

    await callback.answer(texts.BOOKING_CANCEL_SUCCESS)
    reply_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Мои записи", callback_data="my_bookings")],
            [InlineKeyboardButton(text="Главное меню", callback_data="back_main")],
        ]
    )
    await message.answer(
        texts.booking_canceled(direction_name, long_label),
        reply_markup=reply_markup,
    )

    try:
        text, bookings_markup, _ = await _compose_bookings_view(user.id)
        await _safe_edit_message(message, text, reply_markup=bookings_markup)
    except HTTPError:
        pass


@router.callback_query(F.data == "back_to_directions")
async def back_to_directions(callback: CallbackQuery) -> None:
    try:
        directions = await fetch_directions()
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return

    if not directions:
        await callback.answer(texts.NO_DIRECTIONS, show_alert=True)
        return

    await _safe_edit_message(
        callback.message,
        texts.DIRECTIONS_PROMPT,
        reply_markup=directions_keyboard(directions),
    )
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery) -> None:
    await _safe_edit_message(
        callback.message,
        texts.MAIN_MENU,
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.message(BookingStates.ask_full_name)
async def save_full_name(message: Message, state: FSMContext) -> None:
    user = message.from_user
    full_name = (message.text or "").strip()
    if not user:
        await message.answer(texts.API_ERROR)
        return
    if not full_name:
        await message.answer(texts.FULL_NAME_INVALID)
        return
    try:
        user_payload = await sync_user(tg_id=user.id, full_name=full_name)
    except HTTPError:
        await message.answer(texts.API_ERROR)
        return
    await message.answer(texts.full_name_saved(full_name))
    data = await state.get_data()
    pending_slot = data.get(_PENDING_SLOT_KEY)
    if isinstance(pending_slot, int) and _extract_age(user_payload) is None:
        await _prompt_age(message, state)
        return
    await _complete_pending_booking(message, state, user_payload)


@router.callback_query(BookingStates.ask_full_name, F.data == _KEEP_FULL_NAME_CALLBACK)
async def keep_full_name(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    message = callback.message
    if not user or not message:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return
    try:
        user_payload = await sync_user(tg_id=user.id)
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return
    existing_age = _extract_age(user_payload)
    data = await state.get_data()
    pending_slot = data.get(_PENDING_SLOT_KEY)
    if isinstance(pending_slot, int) and existing_age is None:
        await _prompt_age(message, state, existing_age)
        await callback.answer(texts.PROFILE_DETAILS_REQUIRED, show_alert=True)
        return
    await _complete_pending_booking(message, state, user_payload)
    await callback.answer(texts.KEPT_FULL_NAME)


@router.message(BookingStates.ask_age)
async def save_age(message: Message, state: FSMContext) -> None:
    user = message.from_user
    raw_age = (message.text or "").strip()
    if not user:
        await message.answer(texts.API_ERROR)
        return
    if not raw_age.isdigit():
        await message.answer(texts.AGE_INVALID)
        return
    age = int(raw_age)
    if not _is_valid_age(age):
        await message.answer(texts.AGE_INVALID)
        return
    try:
        user_payload = await sync_user(tg_id=user.id, age=age)
    except HTTPError:
        await message.answer(texts.API_ERROR)
        return
    await message.answer(texts.age_saved(age))
    await _complete_pending_booking(message, state, user_payload)


@router.callback_query(BookingStates.ask_age, F.data == _KEEP_AGE_CALLBACK)
async def keep_age(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    message = callback.message
    if not user or not message:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return
    try:
        user_payload = await sync_user(tg_id=user.id)
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return
    await _complete_pending_booking(message, state, user_payload)
    await callback.answer(texts.KEPT_AGE)

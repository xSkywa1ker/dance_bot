from __future__ import annotations

import ipaddress
from datetime import datetime
from typing import Mapping
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from httpx import HTTPError
from urllib.parse import urlparse

from config import get_settings
from keyboards import (
    directions_keyboard,
    product_actions_keyboard,
    products_keyboard,
    main_menu_keyboard,
    slots_keyboard,
    slot_actions_keyboard,
)
from services import (
    create_booking,
    create_subscription_payment,
    fetch_directions,
    fetch_products,
    fetch_slots,
    fetch_bookings,
    sync_user,
    fetch_studio_addresses,
)
from services.api_client import Direction
from states.booking import BookingStates
from utils import texts

router = Router()
_settings = get_settings()
_timezone = ZoneInfo(_settings.timezone)


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


def _direction_title(direction: Direction) -> str:
    name = direction.get("name", "Направление")
    return texts.direction_schedule_title(name)


async def _prompt_full_name_if_missing(
    message: Message,
    state: FSMContext,
    user_payload: Mapping[str, object] | None,
) -> None:
    if not message or not user_payload:
        return
    full_name = user_payload.get("full_name")
    if isinstance(full_name, str) and full_name.strip():
        await state.clear()
        return
    await state.set_state(BookingStates.ask_full_name)
    await message.answer(texts.ASK_FULL_NAME)


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
    await callback.answer()


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
        bookings = await fetch_bookings(tg_id=user.id)
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return

    items: list[dict[str, object]] = []
    pay_rows: list[list[InlineKeyboardButton]] = []
    for booking in bookings:
        slot = booking.get("slot", {})
        short_label, _ = _format_slot_time(slot)
        direction_name = slot.get("direction_name", "") or "Занятие"
        title = f"{short_label} · {direction_name}" if short_label else direction_name
        status = str(booking.get("status", ""))
        entry: dict[str, object] = {"title": title, "status": status}
        if status == "reserved":
            note_parts = ["не оплачено"]
            deadline_label = _format_reservation_deadline(
                booking.get("reservation_expires_at")
            )
            if deadline_label:
                entry["payment_due"] = deadline_label
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

    text = texts.bookings_list(items)
    keyboard_rows: list[list[InlineKeyboardButton]] = [*pay_rows]
    keyboard_rows.append(
        [InlineKeyboardButton(text="Обновить", callback_data="my_bookings")]
    )
    keyboard_rows.append(
        [InlineKeyboardButton(text="Главное меню", callback_data="back_main")]
    )
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
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

    try:
        products = await fetch_products()
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return

    product = next((item for item in products if item.get("id") == product_id), None)
    if not product:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    try:
        payment_response = await create_subscription_payment(
            tg_id=user.id,
            product_id=product_id,
        )
    except HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        elif exc.response is not None and exc.response.status_code == 400:
            detail = exc.response.json()
            message_text = detail.get("detail") if isinstance(detail, dict) else None
            if not isinstance(message_text, str) or not message_text:
                message_text = texts.API_ERROR
            await callback.answer(message_text, show_alert=True)
        else:
            await callback.answer(texts.API_ERROR, show_alert=True)
        return

    payment_url = _resolve_payment_url(payment_response.get("payment_url"))
    price = texts.format_price(product.get("price"))
    link_available = payment_url is not None
    text = texts.subscription_payment_details(
        product.get("name", ""), price or None, link_available=link_available
    )
    buttons: list[list[InlineKeyboardButton]] = []
    if payment_url:
        buttons.append([InlineKeyboardButton(text="Оплатить", url=payment_url)])
    buttons.append([InlineKeyboardButton(text="Главное меню", callback_data="back_main")])
    await _safe_edit_message(
        message,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    if link_available:
        await callback.answer("Ссылка на оплату отправлена")
    else:
        await callback.answer(texts.PAYMENT_LINK_UNAVAILABLE_ALERT, show_alert=True)
    await _prompt_full_name_if_missing(message, state, user_payload)


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

    _, long_label = _format_slot_time(slot)
    slot_text = texts.slot_details(direction.get("name", ""), slot, long_label)
    await _safe_edit_message(
        callback.message,
        slot_text,
        reply_markup=slot_actions_keyboard(direction_id, slot_id),
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

    try:
        booking = await create_booking(tg_id=user.id, slot_id=slot_id)
    except HTTPError as exc:
        if exc.response is not None:
            detail = exc.response.json()
            detail_text = detail.get("detail") if isinstance(detail, dict) else None
            status_code = exc.response.status_code
            if status_code == 409 and detail_text == "Already booked":
                await callback.answer(texts.ALREADY_BOOKED, show_alert=True)
            elif status_code == 409 and detail_text == "Slot start time is in the past":
                await callback.answer(texts.PAST_SLOT_ERROR, show_alert=True)
            elif status_code == 409 and detail_text == "No free seats":
                await callback.answer(texts.NO_SEATS_ERROR, show_alert=True)
            else:
                message_text = detail_text if isinstance(detail_text, str) else texts.API_ERROR
                await callback.answer(message_text, show_alert=True)
        else:
            await callback.answer(texts.API_ERROR, show_alert=True)
        return

    slot = booking.get("slot", {})
    _, long_label = _format_slot_time(slot)
    direction_name = slot.get("direction_name", "")
    price_label = texts.format_price(slot.get("price_single_visit"))
    reply_markup: InlineKeyboardMarkup | None = None
    if booking.get("needs_payment"):
        payment_url = _resolve_payment_url(booking.get("payment_url"))
        link_available = payment_url is not None
        buttons: list[list[InlineKeyboardButton]] = []
        if payment_url:
            buttons.append([InlineKeyboardButton(text="Оплатить", url=payment_url)])
        buttons.append([InlineKeyboardButton(text="Мои записи", callback_data="my_bookings")])
        buttons.append([InlineKeyboardButton(text="Главное меню", callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        text = texts.booking_payment_required(
            direction_name, long_label, price_label or None, link_available=link_available
        )
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
    await callback.answer()
    await _prompt_full_name_if_missing(message, state, user_payload)


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
        await sync_user(tg_id=user.id, full_name=full_name)
    except HTTPError:
        await message.answer(texts.API_ERROR)
        return
    await message.answer(texts.FULL_NAME_SAVED)
    await state.clear()

from __future__ import annotations

from datetime import datetime
from typing import Mapping
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from httpx import HTTPError

from config import get_settings
from keyboards import (
    directions_keyboard,
    main_menu_keyboard,
    slots_keyboard,
    slot_actions_keyboard,
)
from services import (
    fetch_directions,
    fetch_slots,
    fetch_bookings,
    sync_user,
)
from services.api_client import Direction
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


def _direction_title(direction: Direction) -> str:
    name = direction.get("name", "Направление")
    return texts.direction_schedule_title(name)


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

    items: list[tuple[str, str]] = []
    for booking in bookings:
        slot = booking.get("slot", {})
        short_label, _ = _format_slot_time(slot)
        direction_name = slot.get("direction_name", "") or "Занятие"
        title = f"{short_label} · {direction_name}" if short_label else direction_name
        status = str(booking.get("status", ""))
        items.append((title, status))

    text = texts.bookings_list(items)
    await _safe_edit_message(callback.message, text, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "buy_subscription")
async def show_products(callback: CallbackQuery) -> None:
    await _safe_edit_message(
        callback.message,
        texts.SUBSCRIPTION_PURCHASE_SUCCESS,
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer("Покупка успешно завершена")


@router.callback_query(F.data.startswith("product:"))
async def product_details(callback: CallbackQuery) -> None:
    await _safe_edit_message(
        callback.message,
        texts.SUBSCRIPTION_PURCHASE_SUCCESS,
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer("Покупка успешно завершена")


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
async def book_slot(callback: CallbackQuery) -> None:
    await _safe_edit_message(
        callback.message,
        texts.MAIN_MENU,
        reply_markup=main_menu_keyboard(),
    )
    await callback.message.answer(texts.CLASS_PURCHASE_SUCCESS)
    await callback.answer("Покупка успешно завершена")


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

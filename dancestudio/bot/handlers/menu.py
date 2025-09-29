from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from httpx import HTTPError

from config import get_settings
from keyboards import (
    directions_keyboard,
    main_menu_keyboard,
    products_keyboard,
    slots_keyboard,
)
from services import fetch_directions, fetch_products, fetch_slots
from services.api_client import Direction, Slot
from utils import texts

router = Router()
_settings = get_settings()
_timezone = ZoneInfo(_settings.timezone)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(texts.MAIN_MENU, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "rules")
async def show_rules(callback: CallbackQuery) -> None:
    await callback.message.edit_text(texts.CANCEL_RULES, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "my_bookings")
async def my_bookings(callback: CallbackQuery) -> None:
    await callback.answer("Функция в разработке", show_alert=True)


@router.callback_query(F.data == "buy_subscription")
async def show_products(callback: CallbackQuery) -> None:
    try:
        products = await fetch_products()
    except HTTPError:
        await callback.answer(texts.API_ERROR, show_alert=True)
        return

    if not products:
        await callback.answer(texts.NO_PRODUCTS, show_alert=True)
        return

    await callback.message.edit_text(texts.PRODUCTS_PROMPT, reply_markup=products_keyboard(products))
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

    await callback.message.edit_text(texts.product_details(product), reply_markup=products_keyboard(products))
    await callback.answer()


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

    await callback.message.edit_text(texts.DIRECTIONS_PROMPT, reply_markup=directions_keyboard(directions))
    await callback.answer()


def _format_slot_time(slot: Slot) -> tuple[str, str]:
    starts_at = slot.get("starts_at", "")
    if starts_at.endswith("Z"):
        starts_at = starts_at.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(starts_at)
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


@router.callback_query(F.data.startswith("direction:"))
async def show_direction_schedule(callback: CallbackQuery) -> None:
    try:
        direction_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return
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
        await callback.message.edit_text(texts.no_slots(direction.get("name", "")), reply_markup=directions_keyboard(directions))
        await callback.answer()
        return

    slot_buttons = []
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
        await callback.message.edit_text(
            texts.no_slots(direction.get("name", "")),
            reply_markup=directions_keyboard(directions),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        _direction_title(direction),
        reply_markup=slots_keyboard(direction_id, slot_buttons),
    )
    await callback.answer()


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
    await callback.answer(
        texts.slot_details(direction.get("name", ""), slot, long_label),
        show_alert=True,
    )


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

    await callback.message.edit_text(texts.DIRECTIONS_PROMPT, reply_markup=directions_keyboard(directions))
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery) -> None:
    await callback.message.edit_text(texts.MAIN_MENU, reply_markup=main_menu_keyboard())
    await callback.answer()

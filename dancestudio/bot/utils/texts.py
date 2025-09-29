from __future__ import annotations

from typing import Mapping

MAIN_MENU = "Что вы хотите сделать?"
CANCEL_RULES = "Отмена возможна не позднее чем за 24 часа до занятия."
PRODUCTS_PROMPT = "Выберите доступный абонемент:"  # noqa: E305
NO_PRODUCTS = "Пока нет доступных абонементов"
NO_DIRECTIONS = "Пока нет активных направлений"
API_ERROR = "Не удалось получить данные. Попробуйте позже."
ITEM_NOT_FOUND = "Элемент не найден. Попробуйте обновить список."
DIRECTIONS_PROMPT = "Выберите направление:"


def _format_price(value: float | int | None) -> str:
    if value is None:
        return ""
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return f"{text} ₽"


def product_details(product: Mapping[str, object]) -> str:
    name = product.get("name", "Абонемент")
    lines = [f"<b>{name}</b>"]
    price = _format_price(product.get("price"))
    if price:
        lines.append(f"Стоимость: {price}")
    description = product.get("description")
    if isinstance(description, str) and description.strip():
        lines.append(description.strip())
    classes_count = product.get("classes_count")
    if isinstance(classes_count, int) and classes_count > 0:
        lines.append(f"Занятий: {classes_count}")
    validity_days = product.get("validity_days")
    if isinstance(validity_days, int) and validity_days > 0:
        lines.append(f"Срок действия: {validity_days} дней")
    return "\n".join(lines)


def direction_schedule_title(name: str) -> str:
    clean_name = name or "Направление"
    return f"Расписание для «{clean_name}»"


def no_slots(name: str) -> str:
    clean_name = name or "направления"
    return f"Для «{clean_name}» пока нет занятий."


def slot_details(direction_name: str, slot: Mapping[str, object], starts_at: str) -> str:
    clean_direction = direction_name or "Занятие"
    duration = slot.get("duration_min", 0)
    capacity = slot.get("capacity", 0)
    price = _format_price(slot.get("price_single_visit"))
    allow_subscription = slot.get("allow_subscription", False)
    status = slot.get("status", "scheduled")

    lines = [f"{clean_direction}", starts_at]
    if duration:
        lines.append(f"Длительность: {duration} мин")
    if capacity:
        lines.append(f"Мест: {capacity}")
    if price:
        lines.append(f"Разовое посещение: {price}")
    lines.append("Доступно по абонементу" if allow_subscription else "Без абонемента")
    if isinstance(status, str) and status != "scheduled":
        lines.append(f"Статус: {status}")
    return "\n".join(lines)

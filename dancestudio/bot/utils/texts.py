from __future__ import annotations

from typing import Mapping, Sequence

MAIN_MENU = "Что вы хотите сделать?"
CANCEL_RULES = "Отмена возможна не позднее чем за 24 часа до занятия."
NO_PRODUCTS = "Пока нет доступных абонементов"
PRODUCTS_PROMPT = "Выберите абонемент:"
NO_DIRECTIONS = "Пока нет активных направлений"
API_ERROR = "Не удалось получить данные. Попробуйте позже."
ITEM_NOT_FOUND = "Элемент не найден. Попробуйте обновить список."
DIRECTIONS_PROMPT = "Выберите направление:"
NO_BOOKINGS = "У вас пока нет записей."
BOOKINGS_TITLE = "Ваши записи:"
BOOKING_CONFIRMED = "Запись подтверждена!"
BOOKING_PAYMENT_REQUIRED = "Бронь создана, оплатите занятие, чтобы подтвердить запись."
SUBSCRIPTION_PAYMENT_REQUIRED = "Оплатите абонемент, чтобы завершить оформление."
SUBSCRIPTION_PURCHASE_SUCCESS = (
    "Готово! Абонемент успешно оформлен.\n"
    "Мы свяжемся с вами для подтверждения деталей."
)
CLASS_PURCHASE_SUCCESS = (
    "Отлично! Занятие успешно оплачено.\n"
    "Ждём вас на тренировке!"
)
ALREADY_BOOKED = "Вы уже записаны на это занятие."
ASK_FULL_NAME = "Пожалуйста, напишите ваше полное ФИО."
FULL_NAME_SAVED = "Спасибо! Мы сохранили ваше ФИО."
FULL_NAME_INVALID = "Пожалуйста, отправьте ФИО текстом."
PAST_SLOT_ERROR = "Запись на прошедшее занятие недоступна."
NO_SEATS_ERROR = "Свободных мест не осталось."


def _format_price(value: float | int | None) -> str:
    if value is None:
        return ""
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return f"{text} ₽"


def format_price(value: float | int | None) -> str:
    return _format_price(value)


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


def booking_confirmed(direction_name: str, starts_at: str) -> str:
    clean_direction = direction_name or "Занятие"
    return (
        f"{BOOKING_CONFIRMED}\n\n"
        f"«{clean_direction}»\n{starts_at}\n"
        "Ждём вас на занятии!"
    )


def booking_payment_required(direction_name: str, starts_at: str, price: str | None) -> str:
    clean_direction = direction_name or "Занятие"
    parts = [BOOKING_PAYMENT_REQUIRED, "", f"«{clean_direction}»", starts_at]
    if price:
        parts.append(f"Стоимость: {price}")
    parts.append("Перейдите по ссылке ниже, чтобы оплатить занятие.")
    return "\n".join(parts)


def subscription_payment_details(product_name: str, price: str | None) -> str:
    clean_name = product_name or "Абонемент"
    parts = [SUBSCRIPTION_PAYMENT_REQUIRED, "", f"«{clean_name}»"]
    if price:
        parts.append(f"Стоимость: {price}")
    parts.append("Перейдите по ссылке ниже, чтобы оплатить.")
    return "\n".join(parts)


def _status_label(status: str) -> str:
    mapping = {
        "confirmed": "подтверждена",
        "reserved": "ожидает оплаты",
        "canceled": "отменена",
        "late_cancel": "поздняя отмена",
    }
    return mapping.get(status, status)


def bookings_list(items: Sequence[Mapping[str, object]]) -> str:
    if not items:
        return NO_BOOKINGS
    lines = [BOOKINGS_TITLE]
    for item in items:
        title = str(item.get("title", ""))
        status = str(item.get("status", ""))
        note_value = item.get("note")
        note = str(note_value) if isinstance(note_value, str) and note_value else ""
        status_label = _status_label(status)
        if status == "reserved":
            payment_due_value = item.get("payment_due")
            payment_due = (
                str(payment_due_value)
                if isinstance(payment_due_value, str) and payment_due_value
                else ""
            )
            parts = [title]
            if payment_due:
                parts.append(f"бронь до {payment_due}")
            if note:
                parts.append(note)
            else:
                parts.append("требуется оплата")
            lines.append("• " + " — ".join(part for part in parts if part))
        elif note:
            lines.append(f"• {title} ({note})")
        elif status_label:
            lines.append(f"• {title} ({status_label})")
        else:
            lines.append(f"• {title}")
    return "\n".join(lines)

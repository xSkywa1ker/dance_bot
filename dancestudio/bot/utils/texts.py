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
NO_SUBSCRIPTIONS = "Активных абонементов нет."
SUBSCRIPTIONS_TITLE = "Ваши абонементы:"
BOOKING_CONFIRMED = "Запись подтверждена!"
BOOKING_PAYMENT_REQUIRED = "Бронь создана, оплатите занятие, чтобы подтвердить запись."
BOOKING_CANCEL_SUCCESS = "Запись отменена."
BOOKING_CANCEL_REFUND_NOTE = (
    "Мы вернули вам одно занятие. Вы можете записаться на другую тренировку."
)
BOOKING_CANCEL_TOO_LATE = "Отменить занятие можно не позднее чем за 24 часа до начала."
BOOKING_CANCEL_ERROR = "Не удалось отменить запись."
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
ASK_AGE = "Укажите, пожалуйста, ваш возраст (числом)."
AGE_INVALID = "Пожалуйста, отправьте возраст числом от 3 до 120."
PAST_SLOT_ERROR = "Запись на прошедшее занятие недоступна."
NO_SEATS_ERROR = "Свободных мест не осталось."
ADDRESSES_TITLE = "Наши адреса:"
NO_ADDRESSES = "Адреса пока не указаны."
PAYMENT_LINK_UNAVAILABLE_NOTE = "ссылка для оплаты недоступна"
PAYMENT_LINK_UNAVAILABLE_MESSAGE = (
    "Ссылка для оплаты сейчас недоступна.\n"
    "Пожалуйста, свяжитесь с администратором, чтобы завершить оплату."
)
PAYMENT_LINK_UNAVAILABLE_ALERT = (
    "Не удалось сформировать ссылку для оплаты. "
    "Пожалуйста, свяжитесь с администратором."
)
PAYMENT_INVOICE_FAILED_ALERT = (
    "Не удалось отправить счёт через Telegram. "
    "Пожалуйста, свяжитесь с администратором."
)
PAYMENT_INVOICE_NOTE = (
    "Счёт на оплату отправлен отдельным сообщением в Telegram.\n"
    "Нажмите «Оплатить» в счёте, чтобы завершить оплату."
)
PROFILE_DETAILS_REQUIRED = "Пожалуйста, подтвердите ваши ФИО и возраст, чтобы продолжить."
KEPT_FULL_NAME = "Оставляем текущее ФИО."
KEPT_AGE = "Оставляем текущий возраст."


def _format_price(value: float | int | None) -> str:
    if value is None:
        return ""
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return f"{text} ₽"


def format_price(value: float | int | None) -> str:
    return _format_price(value)


def ask_full_name(existing_full_name: str | None = None) -> str:
    if existing_full_name:
        return (
            f"Сейчас сохранено ФИО:\n{existing_full_name}\n\n"
            "Если всё верно, нажмите кнопку ниже или отправьте новое ФИО."
        )
    return ASK_FULL_NAME


def keep_full_name_button(existing_full_name: str) -> str:
    return f"Оставить «{existing_full_name}»"


def full_name_saved(full_name: str | None = None) -> str:
    if full_name:
        return f"Спасибо! Мы сохранили ФИО «{full_name}»."
    return FULL_NAME_SAVED


def ask_age(existing_age: int | None = None) -> str:
    if existing_age is not None:
        return (
            f"Сейчас указан возраст {existing_age}.\n"
            "Если хотите оставить его, нажмите кнопку ниже или отправьте новый возраст."
        )
    return ASK_AGE


def keep_age_button(existing_age: int) -> str:
    return f"Оставить {existing_age}"


def age_saved(age: int) -> str:
    return f"Возраст {age} сохранён."


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
    capacity_raw = slot.get("capacity")
    try:
        capacity = int(capacity_raw)
    except (TypeError, ValueError):
        capacity = 0
    available_raw = slot.get("available_seats")
    try:
        available = int(available_raw)
    except (TypeError, ValueError):
        available = None
    price = _format_price(slot.get("price_single_visit"))
    allow_subscription = slot.get("allow_subscription", False)
    status = slot.get("status", "scheduled")

    lines = [f"{clean_direction}", starts_at]
    if duration:
        lines.append(f"Длительность: {duration} мин")
    if available is not None and capacity:
        lines.append(f"Свободно: {max(available, 0)}/{capacity}")
    elif capacity:
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


def booking_canceled(direction_name: str, starts_at: str) -> str:
    clean_direction = direction_name or "Занятие"
    parts = [
        BOOKING_CANCEL_SUCCESS,
        "",
        f"«{clean_direction}»",
        starts_at,
        BOOKING_CANCEL_REFUND_NOTE,
    ]
    return "\n".join(part for part in parts if part)


def booking_payment_required(
    direction_name: str,
    starts_at: str,
    price: str | None,
    *,
    link_available: bool = True,
    via_invoice: bool = False,
) -> str:
    clean_direction = direction_name or "Занятие"
    parts = [BOOKING_PAYMENT_REQUIRED, "", f"«{clean_direction}»", starts_at]
    if price:
        parts.append(f"Стоимость: {price}")
    if via_invoice:
        parts.append(PAYMENT_INVOICE_NOTE)
    elif link_available:
        parts.append("Перейдите по ссылке ниже, чтобы оплатить занятие.")
    else:
        parts.append(PAYMENT_LINK_UNAVAILABLE_MESSAGE)
    return "\n".join(parts)


def payment_invoice_error(hint: str | None = None) -> str:
    if hint and hint.strip():
        return f"{PAYMENT_INVOICE_FAILED_ALERT}\n{hint.strip()}"
    return PAYMENT_INVOICE_FAILED_ALERT


def studio_addresses(addresses: str | None) -> str:
    if not addresses or not addresses.strip():
        return NO_ADDRESSES
    return f"{ADDRESSES_TITLE}\n{addresses.strip()}"


def subscription_payment_details(
    product_name: str,
    price: str | None,
    *,
    link_available: bool = True,
    via_invoice: bool = False,
) -> str:
    clean_name = product_name or "Абонемент"
    parts = [SUBSCRIPTION_PAYMENT_REQUIRED, "", f"«{clean_name}»"]
    if price:
        parts.append(f"Стоимость: {price}")
    if via_invoice:
        parts.append(PAYMENT_INVOICE_NOTE)
    elif link_available:
        parts.append("Перейдите по ссылке ниже, чтобы оплатить.")
    else:
        parts.append(PAYMENT_LINK_UNAVAILABLE_MESSAGE)
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
                parts.append(status_label)
            lines.append(" · ".join(part for part in parts if part))
        else:
            parts = [title, status_label]
            if note:
                parts.append(note)
            lines.append(" · ".join(part for part in parts if part))
    return "\n".join(lines)


def subscriptions_summary(items: Sequence[Mapping[str, object]]) -> str:
    if not items:
        return NO_SUBSCRIPTIONS
    lines = [SUBSCRIPTIONS_TITLE]
    for item in items:
        product_name = str(item.get("product_name", "")) or "Абонемент"
        remaining = item.get("remaining_classes")
        total = item.get("total_classes")
        valid_to = item.get("valid_to_label")
        parts = [product_name]
        if isinstance(remaining, int):
            if isinstance(total, int) and total > 0:
                parts.append(f"{remaining}/{total} занятий")
            else:
                parts.append(f"Осталось {remaining} занятий")
        if isinstance(valid_to, str) and valid_to:
            parts.append(f"Действует до {valid_to}")
        lines.append(" · ".join(parts))
    return "\n".join(lines)

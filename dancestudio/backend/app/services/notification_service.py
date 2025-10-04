from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SlotCancellationNotification:
    tg_id: int
    message: str


def build_slot_cancellation_message(
    *, direction_name: str | None, starts_at: datetime
) -> str:
    settings = get_settings()
    timezone = ZoneInfo(settings.timezone)
    local_dt = starts_at.astimezone(timezone)
    direction_label = direction_name or "Занятие"
    formatted_dt = local_dt.strftime("%d.%m.%Y %H:%M")
    return (
        f"Занятие «{direction_label}» {formatted_dt} отменено. "
        "Мы вернули вам одно занятие."
    )


def notify_slot_cancellation(notifications: list[SlotCancellationNotification]) -> None:
    if not notifications:
        return

    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        logger.warning(
            "Telegram bot token is not configured; skipping slot cancellation notifications"
        )
        return

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    with httpx.Client(timeout=10) as client:
        for notification in notifications:
            try:
                response = client.post(
                    api_url,
                    json={
                        "chat_id": notification.tg_id,
                        "text": notification.message,
                        "disable_web_page_preview": True,
                    },
                )
                response.raise_for_status()
            except httpx.HTTPError:
                logger.exception(
                    "Failed to send slot cancellation notification",
                    extra={"tg_id": notification.tg_id},
                )

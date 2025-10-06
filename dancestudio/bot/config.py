from dataclasses import dataclass
import os
from dotenv import load_dotenv

from .core.config import CURRENCY as _PAYMENT_CURRENCY
from .core.config import PROVIDER_TOKEN as _PAYMENT_PROVIDER_TOKEN

load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


@dataclass
class BotSettings:
    token: str = _env("TELEGRAM_BOT_TOKEN")
    admin_ids: tuple[int, ...] = tuple(
        int(x.strip()) for x in _env("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip()
    )
    api_base_url: str = _env("API_BASE_URL", "http://backend:8000/api/v1")
    timezone: str = _env("TIMEZONE", "Europe/Moscow")
    api_token: str = _env("BOT_API_TOKEN", "")
    payment_fallback_url: str = _env("PAYMENT_FALLBACK_URL", "")
    payment_provider_token: str = _PAYMENT_PROVIDER_TOKEN
    payment_currency: str = _PAYMENT_CURRENCY


def get_settings() -> BotSettings:
    return BotSettings()

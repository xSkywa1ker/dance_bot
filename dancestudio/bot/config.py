from dataclasses import dataclass
import os
from dotenv import load_dotenv

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
    _payment_token: str = _env("PAYMENT_PROVIDER_TOKEN", "")
    if not _payment_token:
        # Backwards compatibility with early docker-compose examples that used
        # ``PROVIDER_TOKEN`` for the Telegram payment provider token.
        _payment_token = _env("PROVIDER_TOKEN", "")
    payment_provider_token: str = _payment_token
    payment_currency: str = _env("PAYMENT_CURRENCY", "RUB")


def get_settings() -> BotSettings:
    return BotSettings()

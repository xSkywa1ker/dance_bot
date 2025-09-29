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


def get_settings() -> BotSettings:
    return BotSettings()

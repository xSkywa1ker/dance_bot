"""Application configuration loading utilities."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv


ENV_FILE_PATH: Final[Path] = Path(".env")


@dataclass(frozen=True, slots=True)
class Settings:
    """Dataclass describing configuration values loaded from the environment."""

    bot_token: str
    provider_token: str
    item_title: str
    item_description: str
    price_cents: int
    currency: str = "RUB"


def get_settings() -> Settings:
    """Load application settings from ``.env`` file and validate required values.

    Returns:
        Settings: A populated Settings instance with validated configuration values.

    Raises:
        RuntimeError: If mandatory environment variables are missing or invalid.
    """

    load_dotenv(dotenv_path=ENV_FILE_PATH, override=False)

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("Environment variable BOT_TOKEN is required but was not provided.")

    provider_token = os.getenv("PROVIDER_TOKEN")
    if not provider_token:
        raise RuntimeError(
            "Environment variable PROVIDER_TOKEN is required but was not provided."
        )

    item_title = os.getenv("ITEM_TITLE", "")
    item_description = os.getenv("ITEM_DESCRIPTION", "")

    price_raw = os.getenv("PRICE_RUB_CENTS")
    if price_raw is None:
        raise RuntimeError(
            "Environment variable PRICE_RUB_CENTS is required but was not provided."
        )
    try:
        price_cents = int(price_raw)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive guard.
        raise RuntimeError("Environment variable PRICE_RUB_CENTS must be an integer.") from exc

    currency = os.getenv("CURRENCY", "RUB") or "RUB"

    return Settings(
        bot_token=bot_token,
        provider_token=provider_token,
        item_title=item_title,
        item_description=item_description,
        price_cents=price_cents,
        currency=currency,
    )


__all__ = ["Settings", "get_settings"]

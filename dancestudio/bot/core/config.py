"""Environment-based configuration for payment providers."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True, frozen=True)
class _PaymentConfig:
    """Internal helper dataclass for validating payment-related environment values."""

    provider: str
    currency: str
    provider_token: str

    @classmethod
    def from_env(cls) -> "_PaymentConfig":
        """Create a configuration instance from environment variables."""

        provider_raw = os.getenv("PAYMENT_PROVIDER") or "telegram"
        currency_raw = os.getenv("PAYMENT_CURRENCY") or "RUB"
        token_raw = os.getenv("PAYMENT_PROVIDER_TOKEN")

        provider = provider_raw.strip().lower()
        currency = currency_raw.strip().upper()
        provider_token = (token_raw or "").strip()

        if provider == "telegram" and currency != "RUB":
            raise RuntimeError(
                "Telegram payments support only RUB currency. "
                f"Got PAYMENT_CURRENCY={currency!r}."
            )

        if provider == "telegram" and not provider_token:
            raise RuntimeError(
                "PAYMENT_PROVIDER_TOKEN is required when PAYMENT_PROVIDER is 'telegram'."
            )

        return cls(provider=provider, currency=currency, provider_token=provider_token)


_CONFIG: Final[_PaymentConfig] = _PaymentConfig.from_env()

PROVIDER: Final[str] = _CONFIG.provider
CURRENCY: Final[str] = _CONFIG.currency
PROVIDER_TOKEN: Final[str] = _CONFIG.provider_token


__all__ = ["PROVIDER", "CURRENCY", "PROVIDER_TOKEN"]

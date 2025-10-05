from abc import ABC, abstractmethod
from typing import Any
from ...config import Settings


class BasePaymentGateway(ABC):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def create_payment(
        self,
        order_id: str,
        amount: float,
        currency: str,
        description: str,
        return_url: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def parse_webhook(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def get_gateway(settings: Settings) -> BasePaymentGateway:
    if settings.payment_provider == "stub":
        from .stub import StubGateway

        return StubGateway(settings)
    if settings.payment_provider == "yookassa":
        from .yookassa import YooKassaGateway

        return YooKassaGateway(settings)
    if settings.payment_provider == "telegram":
        from .telegram import TelegramGateway

        return TelegramGateway(settings)
    raise ValueError(f"Unsupported payment provider {settings.payment_provider}")

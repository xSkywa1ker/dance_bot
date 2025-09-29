import logging
from typing import Any
from .gateway import BasePaymentGateway

logger = logging.getLogger(__name__)


class YooKassaGateway(BasePaymentGateway):
    def create_payment(
        self,
        order_id: str,
        amount: float,
        currency: str,
        description: str,
        return_url: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        logger.info("Creating YooKassa payment", extra={"order_id": order_id, "amount": amount})
        return {
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "confirmation_url": return_url,
        }

    def parse_webhook(self, data: dict[str, Any]) -> dict[str, Any]:
        logger.info("Parsing YooKassa webhook", extra=data)
        return {
            "order_id": data.get("object", {}).get("metadata", {}).get("order_id"),
            "status": data.get("object", {}).get("status"),
            "provider_payment_id": data.get("object", {}).get("id"),
        }

from __future__ import annotations

from typing import Any

from .gateway import BasePaymentGateway


class StubGateway(BasePaymentGateway):
    """Simple payment gateway stub that pretends every payment succeeds."""

    def create_payment(
        self,
        order_id: str,
        amount: float,
        currency: str,
        description: str,
        return_url: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "status": "succeeded",
            "return_url": return_url,
            "description": description,
            "metadata": metadata,
        }

    def parse_webhook(self, data: dict[str, Any]) -> dict[str, Any]:
        # Webhooks are not used for the stub provider, simply echo data back
        return {
            "order_id": data.get("order_id"),
            "status": data.get("status", "succeeded"),
            "provider_payment_id": data.get("provider_payment_id"),
        }

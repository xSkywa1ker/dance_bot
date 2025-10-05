from __future__ import annotations

from typing import Any

from .gateway import BasePaymentGateway


class TelegramGateway(BasePaymentGateway):
    """Gateway stub for Telegram Bot API payments.

    Telegram invoices are created client-side by the bot, so the backend only
    needs to generate an order identifier and later accept webhook-style
    confirmations. This gateway therefore returns minimal payloads that can be
    relayed back to Telegram handlers in the bot.
    """

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
            "status": "pending",
            "metadata": metadata,
        }

    def parse_webhook(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "order_id": data.get("order_id"),
            "status": data.get("status", "paid"),
            "provider_payment_id": data.get("provider_payment_id"),
        }

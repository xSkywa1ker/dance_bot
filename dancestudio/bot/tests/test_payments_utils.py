from __future__ import annotations

import json
import os
import pytest

os.environ.setdefault("PAYMENT_PROVIDER", "telegram")
os.environ.setdefault("PAYMENT_CURRENCY", "RUB")
os.environ.setdefault("PAYMENT_PROVIDER_TOKEN", "test-token")

from ..services import payments


def test_payments_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(payments, "PROVIDER_TOKEN", "", raising=False)
    assert not payments.payments_enabled()

    monkeypatch.setattr(payments, "PROVIDER_TOKEN", "token", raising=False)
    assert payments.payments_enabled()


@pytest.mark.parametrize(
    "amount, expected",
    [
        (10, 1000),
        (10.0, 1000),
        (10.01, 1001),
        (10.015, 1002),
        (0.99, 99),
    ],
)
def test_to_minor_units(amount: float, expected: int) -> None:
    assert payments.to_minor_units(amount) == expected


def test_to_minor_units_invalid() -> None:
    with pytest.raises(ValueError):
        payments.to_minor_units("not-a-number")  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        payments.to_minor_units(0)


def test_build_provider_receipt() -> None:
    payload = payments.build_provider_receipt(1050, payments.CURRENCY, "Абонемент")
    data = json.loads(payload)
    item = data["receipt"]["items"][0]

    assert item["amount"] == {"value": "10.50", "currency": payments.CURRENCY}
    assert item["quantity"] == "1.00"


def test_build_and_parse_payload() -> None:
    payload = payments.build_payload(payments.KIND_SUBSCRIPTION, "order-123")
    assert payments.parse_payload(payload) == (payments.KIND_SUBSCRIPTION, "order-123")
    assert payments.parse_payload("invalid") is None

def test_explain_invoice_error_known_code() -> None:
    message = payments.explain_invoice_error(
        "TelegramBadRequest: Bad Request: PAYMENT_PROVIDER_INVALID"
    )
    assert "токен" in message.lower()


def test_explain_invoice_error_unknown_code() -> None:
    message = payments.explain_invoice_error("Some unexpected error")
    assert "telegram" in message.lower()

class _DummyMessage:
    def __init__(self) -> None:
        self.invoice_kwargs: dict[str, object] | None = None

    async def answer_invoice(self, **kwargs: object) -> None:  # pragma: no cover - exercised
        self.invoice_kwargs = kwargs


@pytest.mark.asyncio()
async def test_send_invoice_sanitises_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = _DummyMessage()
    monkeypatch.setattr(payments, "PROVIDER_TOKEN", "token", raising=False)

    await payments.send_invoice(
        dummy,
        title="  Очень длинное название продукта, которое превышает лимит символов  ",
        description="   \n\n",
        amount=10,
        payload="kind:order",
    )

    assert dummy.invoice_kwargs is not None
    title = dummy.invoice_kwargs["title"]
    label = dummy.invoice_kwargs["prices"][0].label  # type: ignore[index]
    description = dummy.invoice_kwargs["description"]
    provider_token = dummy.invoice_kwargs["provider_token"]

    assert len(title) <= 32
    assert title == label
    assert description == title
    provider_data = dummy.invoice_kwargs["provider_data"]

    assert provider_token == "token"
    assert isinstance(provider_data, str)
    data = json.loads(provider_data)
    assert data["receipt"]["items"][0]["amount"] == {
        "value": "10.00",
        "currency": payments.CURRENCY,
    }

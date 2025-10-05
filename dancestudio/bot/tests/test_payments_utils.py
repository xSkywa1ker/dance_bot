from __future__ import annotations

from types import SimpleNamespace

import pytest

from ..services import payments


def test_payments_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        payments,
        "get_settings",
        lambda: SimpleNamespace(payment_provider_token="", payment_currency="RUB"),
    )
    assert not payments.payments_enabled()

    monkeypatch.setattr(
        payments,
        "get_settings",
        lambda: SimpleNamespace(payment_provider_token="token", payment_currency="RUB"),
    )
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
    monkeypatch.setattr(
        payments,
        "get_settings",
        lambda: SimpleNamespace(
            payment_provider_token="  token  ",
            payment_currency="rub",
        ),
    )

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
    assert provider_token == "token"

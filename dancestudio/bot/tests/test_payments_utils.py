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

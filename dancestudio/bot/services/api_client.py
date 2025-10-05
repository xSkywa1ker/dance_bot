from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict

import httpx

try:  # pragma: no cover - executed depending on import layout
    from dancestudio.bot.config import get_settings
except ModuleNotFoundError as exc:  # pragma: no cover - fallback for Docker image
    if exc.name and not exc.name.startswith("dancestudio"):
        raise
    from config import get_settings  # type: ignore[no-redef]


class Product(TypedDict, total=False):
    id: int
    name: str
    type: str
    description: str | None
    price: float
    classes_count: int | None
    validity_days: int | None
    direction_limit_id: int | None
    is_active: bool


class Direction(TypedDict, total=False):
    id: int
    name: str
    description: str | None
    is_active: bool


class Slot(TypedDict, total=False):
    id: int
    direction_id: int
    starts_at: str
    duration_min: int
    capacity: int
    price_single_visit: float
    allow_subscription: bool
    status: str


class BookingSlot(TypedDict, total=False):
    id: int
    direction_id: int
    direction_name: str
    starts_at: str
    duration_min: int
    price_single_visit: float | None
    allow_subscription: bool


class Booking(TypedDict, total=False):
    id: int
    status: str
    slot: BookingSlot
    needs_payment: bool
    payment_status: str | None
    payment_url: str | None
    payment_id: int | None
    payment_provider: str | None
    payment_order_id: str | None
    payment_amount: float | None
    payment_currency: str | None
    reservation_expires_at: str | None


class Subscription(TypedDict, total=False):
    id: int
    product_id: int
    product_name: str
    remaining_classes: int
    total_classes: int | None
    valid_from: str
    valid_to: str
    status: str


class StudioAddresses(TypedDict, total=False):
    addresses: str


class PaymentResponse(TypedDict, total=False):
    payment_id: int
    status: str
    payment_url: str | None
    order_id: str | None
    provider: str | None
    amount: float | None
    currency: str | None


_settings = get_settings()


def _request_path(path: str) -> str:
    """Return a path relative to the configured API base URL."""

    if path.startswith("http://") or path.startswith("https://"):
        return path
    return path.lstrip("/")


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(base_url=_settings.api_base_url, timeout=10.0) as client:
        response = await client.get(_request_path(path), params=params, headers=_headers())
        response.raise_for_status()
        return response.json()


async def _post(path: str, json: dict[str, Any]) -> Any:
    async with httpx.AsyncClient(base_url=_settings.api_base_url, timeout=10.0) as client:
        response = await client.post(_request_path(path), json=json, headers=_headers())
        response.raise_for_status()
        return response.json()


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    if _settings.api_token:
        headers["X-Bot-Token"] = _settings.api_token
    return headers


async def fetch_products(*, active_only: bool = True) -> list[Product]:
    data = await _get("/products")
    if active_only:
        return [product for product in data if product.get("is_active")]
    return data


async def fetch_directions(*, active_only: bool = True) -> list[Direction]:
    params = {"include_inactive": not active_only}
    data = await _get("/directions", params=params)
    if active_only:
        return [direction for direction in data if direction.get("is_active")]
    return data


async def fetch_slots(*, direction_id: int | None = None) -> list[Slot]:
    params: dict[str, Any] = {"from_dt": datetime.now(timezone.utc).isoformat()}
    if direction_id is not None:
        params["direction_id"] = direction_id
    data = await _get("/slots", params=params)
    return data


async def sync_user(*, tg_id: int, full_name: str | None = None, phone: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"tg_id": tg_id}
    if full_name is not None:
        payload["full_name"] = full_name
    if phone is not None:
        payload["phone"] = phone
    return await _post("/bot/users/sync", payload)


async def fetch_bookings(*, tg_id: int) -> list[Booking]:
    data = await _get(f"/bot/users/{tg_id}/bookings")
    return data


async def fetch_subscriptions(*, tg_id: int) -> list[Subscription]:
    data = await _get(f"/bot/users/{tg_id}/subscriptions")
    return data


async def create_booking(*, tg_id: int, slot_id: int, full_name: str | None = None, phone: str | None = None) -> Booking:
    payload: dict[str, Any] = {"tg_id": tg_id, "slot_id": slot_id}
    if full_name is not None:
        payload["full_name"] = full_name
    if phone is not None:
        payload["phone"] = phone
    data = await _post("/bot/bookings", payload)
    return data


async def cancel_booking(*, tg_id: int, booking_id: int) -> Booking:
    payload: dict[str, Any] = {"tg_id": tg_id}
    data = await _post(f"/bot/bookings/{booking_id}/cancel", payload)
    return data


async def create_subscription_payment(
    *, tg_id: int, product_id: int, full_name: str | None = None, phone: str | None = None
) -> PaymentResponse:
    payload: dict[str, Any] = {"tg_id": tg_id, "product_id": product_id}
    if full_name is not None:
        payload["full_name"] = full_name
    if phone is not None:
        payload["phone"] = phone
    data = await _post("/bot/payments/subscription", payload)
    return data


async def confirm_payment(
    *, order_id: str, status: str = "paid", provider_payment_id: str | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"order_id": order_id, "status": status}
    if provider_payment_id:
        payload["provider_payment_id"] = provider_payment_id
    data = await _post("/payments/webhook", payload)
    return data


async def fetch_studio_addresses() -> StudioAddresses:
    data = await _get("/bot/addresses")
    if isinstance(data, dict) and isinstance(data.get("addresses"), str):
        return {"addresses": data["addresses"]}
    return {"addresses": ""}


__all__ = [
    "Product",
    "Direction",
    "Slot",
    "Booking",
    "Subscription",
    "StudioAddresses",
    "PaymentResponse",
    "fetch_products",
    "fetch_directions",
    "fetch_slots",
    "fetch_bookings",
    "fetch_subscriptions",
    "create_booking",
    "cancel_booking",
    "sync_user",
    "create_subscription_payment",
    "confirm_payment",
    "fetch_studio_addresses",
]

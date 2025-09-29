from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict

import httpx

from config import get_settings


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


_settings = get_settings()


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(base_url=_settings.api_base_url, timeout=10.0) as client:
        response = await client.get(path, params=params, headers=_headers())
        response.raise_for_status()
        return response.json()


async def _post(path: str, json: dict[str, Any]) -> Any:
    async with httpx.AsyncClient(base_url=_settings.api_base_url, timeout=10.0) as client:
        response = await client.post(path, json=json, headers=_headers())
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


async def create_booking(*, tg_id: int, slot_id: int, full_name: str | None = None, phone: str | None = None) -> Booking:
    payload: dict[str, Any] = {"tg_id": tg_id, "slot_id": slot_id}
    if full_name is not None:
        payload["full_name"] = full_name
    if phone is not None:
        payload["phone"] = phone
    data = await _post("/bot/bookings", payload)
    return data


async def create_subscription_payment(
    *, tg_id: int, product_id: int, full_name: str | None = None, phone: str | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"tg_id": tg_id, "product_id": product_id}
    if full_name is not None:
        payload["full_name"] = full_name
    if phone is not None:
        payload["phone"] = phone
    data = await _post("/bot/payments/subscription", payload)
    return data


__all__ = [
    "Product",
    "Direction",
    "Slot",
    "Booking",
    "fetch_products",
    "fetch_directions",
    "fetch_slots",
    "fetch_bookings",
    "create_booking",
    "sync_user",
    "create_subscription_payment",
]

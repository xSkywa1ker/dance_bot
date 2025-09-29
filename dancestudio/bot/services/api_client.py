from __future__ import annotations

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


_settings = get_settings()


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(base_url=_settings.api_base_url, timeout=10.0) as client:
        response = await client.get(path, params=params)
        response.raise_for_status()
        return response.json()


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
    params: dict[str, Any] | None = None
    if direction_id is not None:
        params = {"direction_id": direction_id}
    data = await _get("/slots", params=params)
    return data


__all__ = ["Product", "Direction", "Slot", "fetch_products", "fetch_directions", "fetch_slots"]

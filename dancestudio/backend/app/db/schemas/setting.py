from __future__ import annotations

from pydantic import BaseModel


class StudioAddresses(BaseModel):
    addresses: str


class StudioAddressesUpdate(BaseModel):
    addresses: str

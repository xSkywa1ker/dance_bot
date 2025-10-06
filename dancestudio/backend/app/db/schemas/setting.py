from __future__ import annotations

from pydantic import BaseModel, Field


class SettingMedia(BaseModel):
    id: int
    url: str
    media_type: str
    filename: str


class StudioAddresses(BaseModel):
    addresses: str
    media: list[SettingMedia] = Field(default_factory=list)


class StudioAddressesUpdate(BaseModel):
    addresses: str
    media_ids: list[int] = Field(default_factory=list)

from datetime import datetime
from pydantic import BaseModel


class ClassSlotBase(BaseModel):
    direction_id: int | None = None
    starts_at: datetime
    duration_min: int
    capacity: int
    price_single_visit: float
    allow_subscription: bool = True
    status: str = "scheduled"


class ClassSlotCreate(ClassSlotBase):
    direction_id: int


class ClassSlotUpdate(BaseModel):
    direction_id: int | None = None
    starts_at: datetime | None = None
    duration_min: int | None = None
    capacity: int | None = None
    price_single_visit: float | None = None
    allow_subscription: bool | None = None
    status: str | None = None


class ClassSlot(ClassSlotBase):
    id: int

    class Config:
        from_attributes = True

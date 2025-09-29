from datetime import datetime
from pydantic import BaseModel


class BookingBase(BaseModel):
    user_id: int
    class_slot_id: int


class BookingCreate(BookingBase):
    source: str = "admin"


class BookingCancel(BaseModel):
    reason: str | None = None


class Booking(BookingBase):
    id: int
    status: str
    created_at: datetime
    user_full_name: str | None = None
    slot_starts_at: datetime | None = None
    slot_direction_name: str | None = None

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

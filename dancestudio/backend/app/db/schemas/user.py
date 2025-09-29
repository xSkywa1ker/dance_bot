from datetime import datetime
from pydantic import BaseModel


class UserBase(BaseModel):
    tg_id: int
    full_name: str | None = None
    age: int | None = None
    phone: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    age: int | None = None
    phone: str | None = None


class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

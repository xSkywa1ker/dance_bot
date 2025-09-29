from datetime import datetime
from pydantic import BaseModel


class PaymentBase(BaseModel):
    user_id: int
    amount: float
    currency: str = "RUB"
    purpose: str
    product_id: int | None = None
    class_slot_id: int | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentWebhook(BaseModel):
    order_id: str
    status: str
    provider_payment_id: str | None = None


class Payment(PaymentBase):
    id: int
    status: str
    provider: str
    order_id: str
    created_at: datetime

    class Config:
        from_attributes = True

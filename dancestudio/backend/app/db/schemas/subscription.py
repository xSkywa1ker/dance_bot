from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ManualSubscriptionGrant(BaseModel):
    classes_count: int = Field(gt=0, description="Количество занятий для абонемента")
    validity_days: int | None = Field(
        default=None,
        gt=0,
        description="Срок действия в днях. Если не указан, используется значение по умолчанию.",
    )


class Subscription(BaseModel):
    id: int
    user_id: int
    product_id: int
    remaining_classes: int
    initial_classes: int | None = None
    valid_from: datetime
    valid_to: datetime
    status: str

    class Config:
        from_attributes = True

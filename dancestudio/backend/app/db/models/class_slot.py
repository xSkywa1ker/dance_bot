from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..session import Base


class SlotStatus(str, PyEnum):
    scheduled = "scheduled"
    canceled = "canceled"
    completed = "completed"


class ClassSlot(Base):
    __tablename__ = "class_slots"
    __table_args__ = (
        UniqueConstraint("direction_id", "starts_at", name="uq_class_slot_direction_time"),
        CheckConstraint("capacity > 0", name="ck_class_slot_capacity_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    direction_id: Mapped[int] = mapped_column(ForeignKey("directions.id", ondelete="CASCADE"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_min: Mapped[int] = mapped_column(Integer, default=60)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_single_visit: Mapped[float] = mapped_column(Numeric(10, 2))
    allow_subscription: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[SlotStatus] = mapped_column(Enum(SlotStatus), default=SlotStatus.scheduled)

    direction = relationship("Direction", back_populates="slots")
    bookings = relationship("Booking", back_populates="slot")

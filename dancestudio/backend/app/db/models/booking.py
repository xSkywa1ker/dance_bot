from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..session import Base


class BookingStatus(str, PyEnum):
    reserved = "reserved"
    confirmed = "confirmed"
    canceled = "canceled"
    late_cancel = "late_cancel"
    attended = "attended"
    no_show = "no_show"


class BookingSource(str, PyEnum):
    bot = "bot"
    admin = "admin"


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("user_id", "class_slot_id", name="uq_booking_user_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    class_slot_id: Mapped[int] = mapped_column(ForeignKey("class_slots.id", ondelete="CASCADE"))
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.reserved)
    source: Mapped[BookingSource] = mapped_column(Enum(BookingSource), default=BookingSource.bot)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canceled_by: Mapped[str | None] = mapped_column(String(64))
    cancellation_reason: Mapped[str | None] = mapped_column(String(255))

    user = relationship("User")
    slot = relationship("ClassSlot", back_populates="bookings")

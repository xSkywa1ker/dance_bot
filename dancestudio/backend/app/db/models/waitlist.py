from enum import Enum as PyEnum
from sqlalchemy import Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..session import Base


class WaitlistStatus(str, PyEnum):
    active = "active"
    notified = "notified"
    joined = "joined"
    expired = "expired"


class Waitlist(Base):
    __tablename__ = "waitlist"
    __table_args__ = (
        UniqueConstraint("user_id", "class_slot_id", name="uq_waitlist_user_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    class_slot_id: Mapped[int] = mapped_column(ForeignKey("class_slots.id", ondelete="CASCADE"))
    status: Mapped[WaitlistStatus] = mapped_column(Enum(WaitlistStatus), default=WaitlistStatus.active)

    user = relationship("User")
    slot = relationship("ClassSlot")

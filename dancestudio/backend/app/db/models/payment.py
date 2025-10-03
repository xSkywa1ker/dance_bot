from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    CHAR,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..session import Base


class PaymentStatus(str, PyEnum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    canceled = "canceled"
    refunded = "refunded"


class PaymentPurpose(str, PyEnum):
    single_visit = "single_visit"
    subscription = "subscription"


class PaymentProvider(str, PyEnum):
    stub = "stub"
    yookassa = "yookassa"
    stripe = "stripe"
    tinkoff = "tinkoff"
    cloudpayments = "cloudpayments"


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("order_id", name="uq_payment_order_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    class_slot_id: Mapped[int | None] = mapped_column(ForeignKey("class_slots.id"))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(CHAR(3), default="RUB")
    provider: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider))
    order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(128))
    confirmation_url: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending)
    purpose: Mapped[PaymentPurpose] = mapped_column(Enum(PaymentPurpose))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    product = relationship("Product")
    slot = relationship("ClassSlot")

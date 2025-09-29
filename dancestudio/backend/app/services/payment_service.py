import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from ..db import models
from ..config import get_settings
from .payments import gateway


def create_payment(
    db: Session,
    user: models.User,
    amount: float,
    purpose: models.PaymentPurpose,
    product: models.Product | None = None,
    slot: models.ClassSlot | None = None,
) -> models.Payment:
    order_id = str(uuid.uuid4())
    settings = get_settings()
    payment = models.Payment(
        user_id=user.id,
        product_id=product.id if product else None,
        class_slot_id=slot.id if slot else None,
        amount=amount,
        currency="RUB",
        provider=models.PaymentProvider(settings.payment_provider),
        order_id=order_id,
        purpose=purpose,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    gateway_client = gateway.get_gateway(settings)
    gateway_client.create_payment(
        order_id=order_id,
        amount=amount,
        currency=payment.currency,
        description=f"Dance class payment #{order_id}",
        return_url=settings.payment_return_url,
        metadata={"user_id": user.id},
    )
    return payment


def apply_payment(db: Session, payment: models.Payment, status: models.PaymentStatus) -> models.Payment:
    if payment.status == status:
        return payment
    payment.status = status
    payment.updated_at = datetime.utcnow()
    if status == models.PaymentStatus.paid and payment.class_slot_id:
        booking = (
            db.query(models.Booking)
            .filter_by(class_slot_id=payment.class_slot_id, user_id=payment.user_id)
            .order_by(models.Booking.id.desc())
            .first()
        )
        if booking:
            booking.status = models.BookingStatus.confirmed
    db.commit()
    db.refresh(payment)
    return payment

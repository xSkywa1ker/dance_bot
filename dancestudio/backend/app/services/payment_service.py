import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import models
from .payments import gateway


def create_payment(
    db: Session,
    user: models.User,
    amount: float,
    purpose: models.PaymentPurpose,
    product: models.Product | None = None,
    slot: models.ClassSlot | None = None,
) -> tuple[models.Payment, dict[str, Any]]:
    order_id = str(uuid.uuid4())
    settings = get_settings()
    currency = (settings.payment_currency or "RUB").upper()
    payment = models.Payment(
        user_id=user.id,
        product_id=product.id if product else None,
        class_slot_id=slot.id if slot else None,
        amount=amount,
        currency=currency,
        provider=models.PaymentProvider(settings.payment_provider),
        order_id=order_id,
        purpose=purpose,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    gateway_client = gateway.get_gateway(settings)
    gateway_response = gateway_client.create_payment(
        order_id=order_id,
        amount=amount,
        currency=currency,
        description=f"Dance class payment #{order_id}",
        return_url=settings.payment_return_url,
        metadata={"user_id": user.id},
    )
    confirmation_url = (
        gateway_response.get("confirmation_url")
        or gateway_response.get("return_url")
    )
    if confirmation_url:
        payment.confirmation_url = confirmation_url
        db.commit()
        db.refresh(payment)
    if settings.payment_provider == "stub":
        payment = apply_payment(db, payment, models.PaymentStatus.paid)
    return payment, gateway_response


def apply_payment(db: Session, payment: models.Payment, status: models.PaymentStatus) -> models.Payment:
    if payment.status == status:
        return payment
    payment.status = status
    payment.updated_at = datetime.now(timezone.utc)
    if status == models.PaymentStatus.paid:
        payment.confirmation_url = None
        if payment.class_slot_id:
            booking = (
                db.query(models.Booking)
                .filter_by(class_slot_id=payment.class_slot_id, user_id=payment.user_id)
                .order_by(models.Booking.id.desc())
                .first()
            )
            if booking:
                booking.status = models.BookingStatus.confirmed
        if (
            payment.purpose == models.PaymentPurpose.subscription
            and payment.product_id
        ):
            product = db.get(models.Product, payment.product_id)
            if product:
                valid_from = datetime.now(timezone.utc)
                validity_days = product.validity_days or 30
                remaining_classes = product.classes_count or 0
                subscription = models.Subscription(
                    user_id=payment.user_id,
                    product_id=product.id,
                    remaining_classes=remaining_classes,
                    valid_from=valid_from,
                    valid_to=valid_from + timedelta(days=validity_days),
                )
                db.add(subscription)
    db.commit()
    db.refresh(payment)
    return payment

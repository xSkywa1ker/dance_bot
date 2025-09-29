from datetime import datetime, timedelta
from app.db import models
from app.services import booking_service, payment_service


def test_auto_subscription_confirmation(db_session):
    direction = models.Direction(name="Contemporary")
    db_session.add(direction)
    db_session.commit()
    slot = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.utcnow() + timedelta(days=3),
        duration_min=60,
        capacity=2,
        price_single_visit=500,
    )
    user = models.User(tg_id=999)
    product = models.Product(type=models.ProductType.subscription, name="Абонемент", price=1000)
    subscription = models.Subscription(
        user=user,
        product=product,
        remaining_classes=5,
        valid_from=datetime.utcnow() - timedelta(days=1),
        valid_to=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add_all([slot, user, product, subscription])
    db_session.commit()
    booking = booking_service.book_class(db_session, user, slot)
    assert booking.status == models.BookingStatus.confirmed


def test_payment_webhook_idempotent(db_session):
    direction = models.Direction(name="Salsa")
    db_session.add(direction)
    db_session.commit()
    slot = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.utcnow() + timedelta(days=5),
        duration_min=60,
        capacity=2,
        price_single_visit=500,
    )
    user = models.User(tg_id=222)
    db_session.add_all([slot, user])
    db_session.commit()
    booking = booking_service.book_class(db_session, user, slot)
    payment = payment_service.create_payment(
        db_session,
        user,
        amount=500,
        purpose=models.PaymentPurpose.single_visit,
        slot=slot,
    )
    payment_service.apply_payment(db_session, payment, models.PaymentStatus.paid)
    payment_service.apply_payment(db_session, payment, models.PaymentStatus.paid)
    db_session.refresh(payment)
    assert payment.status == models.PaymentStatus.paid

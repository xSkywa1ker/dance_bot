from datetime import datetime, timedelta, timezone

from app.db import models
from app.services import booking_service, payment_service


def test_auto_subscription_confirmation(db_session):
    direction = models.Direction(name="Contemporary")
    db_session.add(direction)
    db_session.commit()
    slot = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.now(timezone.utc) + timedelta(days=3),
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
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_to=datetime.now(timezone.utc) + timedelta(days=30),
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
        starts_at=datetime.now(timezone.utc) + timedelta(days=5),
        duration_min=60,
        capacity=2,
        price_single_visit=500,
    )
    user = models.User(tg_id=222)
    db_session.add_all([slot, user])
    db_session.commit()
    booking = booking_service.book_class(db_session, user, slot)
    payment, _ = payment_service.create_payment(
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


def test_stub_payment_creates_subscription(db_session):
    user = models.User(tg_id=555)
    product = models.Product(
        type=models.ProductType.subscription,
        name="Месячный абонемент",
        price=3500,
        classes_count=8,
        validity_days=30,
    )
    db_session.add_all([user, product])
    db_session.commit()

    payment, _ = payment_service.create_payment(
        db_session,
        user,
        amount=float(product.price),
        purpose=models.PaymentPurpose.subscription,
        product=product,
    )

    db_session.refresh(payment)
    assert payment.status == models.PaymentStatus.paid

    subscription = (
        db_session.query(models.Subscription)
        .filter_by(user_id=user.id, product_id=product.id)
        .one()
    )
    assert subscription.remaining_classes == product.classes_count
    assert subscription.valid_to - subscription.valid_from == timedelta(days=product.validity_days)

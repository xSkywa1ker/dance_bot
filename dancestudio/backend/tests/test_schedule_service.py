from datetime import datetime, timedelta, timezone

from app.core.constants import SLOT_CANCELED_REASON
from app.db import models
from app.services import booking_service, schedule_service


def test_cancel_slot_refunds_subscription_and_creates_notifications(db_session):
    direction = models.Direction(name="Ballet")
    db_session.add(direction)
    db_session.commit()

    slot = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.now(timezone.utc) + timedelta(days=2),
        duration_min=60,
        capacity=5,
        price_single_visit=700,
    )
    user_with_subscription = models.User(tg_id=1001)
    subscription_product = models.Product(
        type=models.ProductType.subscription,
        name="Тестовый абонемент",
        price=3500,
        classes_count=5,
        validity_days=30,
    )
    active_subscription = models.Subscription(
        user=user_with_subscription,
        product=subscription_product,
        remaining_classes=5,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_to=datetime.now(timezone.utc) + timedelta(days=10),
    )
    another_user = models.User(tg_id=2002)

    db_session.add_all(
        [slot, user_with_subscription, subscription_product, active_subscription, another_user]
    )
    db_session.commit()

    booking = booking_service.book_class(db_session, user_with_subscription, slot)
    db_session.refresh(active_subscription)
    assert active_subscription.remaining_classes == 4

    reserved_booking = models.Booking(
        user_id=another_user.id,
        class_slot_id=slot.id,
        status=models.BookingStatus.reserved,
    )
    payment = models.Payment(
        user_id=another_user.id,
        class_slot_id=slot.id,
        amount=slot.price_single_visit,
        currency="RUB",
        provider=models.PaymentProvider.stub,
        order_id="order-1",
        purpose=models.PaymentPurpose.single_visit,
    )
    db_session.add_all([reserved_booking, payment])
    db_session.commit()

    result = schedule_service.cancel_slot(
        db_session,
        slot,
        actor="admin",
        actor_id=42,
    )

    db_session.refresh(active_subscription)
    db_session.refresh(booking)
    db_session.refresh(reserved_booking)
    db_session.refresh(payment)

    assert result.status == models.SlotStatus.canceled
    assert booking.status == models.BookingStatus.canceled
    assert booking.cancellation_reason == SLOT_CANCELED_REASON
    assert booking.canceled_by == "admin"
    assert reserved_booking.status == models.BookingStatus.canceled
    assert active_subscription.remaining_classes == 5
    assert payment.status == models.PaymentStatus.canceled

    compensation = (
        db_session.query(models.Subscription)
        .filter(models.Subscription.user_id == another_user.id)
        .order_by(models.Subscription.id.desc())
        .first()
    )
    assert compensation is not None
    assert compensation.remaining_classes == 1

    logs = (
        db_session.query(models.AuditLog)
        .filter(models.AuditLog.action == "slot_canceled_notification")
        .all()
    )
    assert len(logs) == 2
    assert all(log.actor_type == models.ActorType.admin for log in logs)
    assert set(log.payload.get("user_id") for log in logs) == {
        user_with_subscription.id,
        another_user.id,
    }
    assert all(log.payload.get("message") for log in logs)

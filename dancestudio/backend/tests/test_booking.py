from datetime import datetime, timedelta, timezone
import pytest
from app.core.constants import PAYMENT_TIMEOUT_REASON, RESERVATION_PAYMENT_TIMEOUT, SYSTEM_ACTOR
from app.db import models
from app.services import booking_service


def create_user(session, tg_id=1):
    user = models.User(tg_id=tg_id)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_slot(session, capacity=1):
    direction = models.Direction(name="Hip-Hop")
    session.add(direction)
    session.commit()
    slot = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.now(timezone.utc) + timedelta(days=2),
        duration_min=60,
        capacity=capacity,
        price_single_visit=500,
    )
    session.add(slot)
    session.commit()
    session.refresh(slot)
    return slot


def create_direction(session, name: str) -> models.Direction:
    direction = models.Direction(name=name)
    session.add(direction)
    session.commit()
    session.refresh(direction)
    return direction


def test_booking_capacity_limit(db_session):
    slot = create_slot(db_session, capacity=1)
    user1 = create_user(db_session, 1)
    user2 = create_user(db_session, 2)

    booking_service.book_class(db_session, user1, slot)
    with pytest.raises(booking_service.BookingError):
        booking_service.book_class(db_session, user2, slot)


def test_rebook_after_cancellation(db_session):
    slot = create_slot(db_session, capacity=2)
    user = create_user(db_session, 1)

    booking = booking_service.book_class(db_session, user, slot)
    assert booking.status in {models.BookingStatus.reserved, models.BookingStatus.confirmed}

    canceled = booking_service.cancel_booking(db_session, booking, actor="test")
    assert canceled.status == models.BookingStatus.canceled

    new_booking = booking_service.book_class(db_session, user, slot)
    assert new_booking.id == booking.id
    assert new_booking.status in {models.BookingStatus.reserved, models.BookingStatus.confirmed}


def test_rebook_after_reservation_timeout(db_session):
    slot = create_slot(db_session, capacity=2)
    user = create_user(db_session, 1)

    booking = booking_service.book_class(db_session, user, slot)
    assert booking.status == models.BookingStatus.reserved

    booking.created_at = datetime.now(timezone.utc) - RESERVATION_PAYMENT_TIMEOUT - timedelta(minutes=1)
    booking.status = models.BookingStatus.canceled
    booking.canceled_at = datetime.now(timezone.utc)
    booking.canceled_by = SYSTEM_ACTOR
    booking.cancellation_reason = PAYMENT_TIMEOUT_REASON
    db_session.commit()

    assert booking.status == models.BookingStatus.canceled

    new_booking = booking_service.book_class(db_session, user, slot)
    assert new_booking.id == booking.id
    assert new_booking.status == models.BookingStatus.reserved


def test_booking_uses_matching_direction_subscription(db_session):
    user = create_user(db_session, 1)
    direction_a = create_direction(db_session, "Contemporary")
    direction_b = create_direction(db_session, "Jazz")

    slot = models.ClassSlot(
        direction_id=direction_a.id,
        starts_at=datetime.now(timezone.utc) + timedelta(days=3),
        duration_min=60,
        capacity=5,
        price_single_visit=700,
        allow_subscription=True,
    )
    db_session.add(slot)
    db_session.commit()
    db_session.refresh(slot)

    product_b = models.Product(
        type=models.ProductType.subscription,
        name="Jazz 4",
        price=4000,
        classes_count=4,
        validity_days=30,
        direction_limit_id=direction_b.id,
        is_active=True,
    )
    product_a = models.Product(
        type=models.ProductType.subscription,
        name="Contemporary 8",
        price=8000,
        classes_count=8,
        validity_days=30,
        direction_limit_id=direction_a.id,
        is_active=True,
    )
    db_session.add_all([product_a, product_b])
    db_session.commit()

    now = datetime.now(timezone.utc)
    subscription_b = models.Subscription(
        user_id=user.id,
        product_id=product_b.id,
        remaining_classes=2,
        valid_from=now - timedelta(days=1),
        valid_to=now + timedelta(days=5),
        status=models.SubscriptionStatus.active,
    )
    subscription_a = models.Subscription(
        user_id=user.id,
        product_id=product_a.id,
        remaining_classes=3,
        valid_from=now - timedelta(days=1),
        valid_to=now + timedelta(days=10),
        status=models.SubscriptionStatus.active,
    )
    db_session.add_all([subscription_a, subscription_b])
    db_session.commit()

    booking = booking_service.book_class(db_session, user, slot)

    assert booking.status == models.BookingStatus.confirmed

    db_session.refresh(subscription_a)
    assert subscription_a.remaining_classes == 2

    db_session.refresh(subscription_b)
    assert subscription_b.remaining_classes == 2

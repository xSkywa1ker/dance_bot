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

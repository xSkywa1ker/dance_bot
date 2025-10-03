import pytest
from datetime import datetime, timedelta, timezone
from app.db import models
from app.services import booking_service


def test_cancellation_rules(db_session):
    direction = models.Direction(name="Jazz")
    db_session.add(direction)
    db_session.commit()
    slot = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.now(timezone.utc) + timedelta(days=2),
        duration_min=60,
        capacity=2,
        price_single_visit=500,
    )
    user = models.User(tg_id=123)
    db_session.add_all([slot, user])
    db_session.commit()
    booking = booking_service.book_class(db_session, user, slot)
    result = booking_service.cancel_booking(db_session, booking, actor="user")
    assert result.status == models.BookingStatus.canceled

    slot_late = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.now(timezone.utc) + timedelta(hours=10),
        duration_min=60,
        capacity=2,
        price_single_visit=500,
    )
    db_session.add(slot_late)
    db_session.commit()
    booking2 = booking_service.book_class(db_session, user, slot_late)
    result2 = booking_service.cancel_booking(db_session, booking2, actor="user")
    assert result2.status == models.BookingStatus.late_cancel

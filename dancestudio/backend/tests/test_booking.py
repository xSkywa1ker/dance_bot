from datetime import datetime, timedelta, timezone
import pytest
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

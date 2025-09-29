from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.db import models
from app.services.schedule_service import free_seat


def test_free_seat_notifies_waitlisted_user(db_session):
    direction = models.Direction(name="Test Direction")
    slot = models.ClassSlot(
        direction=direction,
        starts_at=datetime.now(UTC) + timedelta(hours=1),
        duration_min=60,
        capacity=10,
        price_single_visit=Decimal("10.00"),
    )
    user = models.User(tg_id=123456)
    waitlist_entry = models.Waitlist(user=user, slot=slot)

    db_session.add_all([direction, slot, user, waitlist_entry])
    db_session.commit()

    free_seat(db_session, slot)

    db_session.refresh(waitlist_entry)
    assert waitlist_entry.status == models.WaitlistStatus.notified

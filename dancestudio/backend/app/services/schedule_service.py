from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..db import models


def get_available_slots(db: Session, direction_id: int | None = None) -> list[models.ClassSlot]:
    stmt = select(models.ClassSlot).where(models.ClassSlot.starts_at >= datetime.utcnow())
    if direction_id:
        stmt = stmt.where(models.ClassSlot.direction_id == direction_id)
    return list(db.execute(stmt).scalars().all())


def free_seat(db: Session, slot: models.ClassSlot) -> None:
    wait_entry = (
        db.query(models.Waitlist)
        .filter_by(class_slot_id=slot.id, status=models.WaitlistStatus.active)
        .order_by(models.Waitlist.id)
        .first()
    )
    if wait_entry:
        wait_entry.status = models.WaitlistStatus.notified
        db.commit()

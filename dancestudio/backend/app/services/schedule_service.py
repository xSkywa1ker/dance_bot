from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..core.constants import SLOT_CANCELED_REASON
from ..db import models
from .subscription_service import grant_class_credit


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


def cancel_slot(
    db: Session,
    slot: models.ClassSlot,
    *,
    actor: str,
    actor_id: int | None = None,
) -> models.ClassSlot:
    if slot.status == models.SlotStatus.canceled:
        return slot

    now = datetime.now(timezone.utc)
    slot.status = models.SlotStatus.canceled

    bookings = (
        db.query(models.Booking)
        .options(
            selectinload(models.Booking.slot).selectinload(
                models.ClassSlot.direction
            )
        )
        .filter(models.Booking.class_slot_id == slot.id)
        .filter(
            models.Booking.status.in_(
                [models.BookingStatus.confirmed, models.BookingStatus.reserved]
            )
        )
        .all()
    )

    for booking in bookings:
        grant_class_credit(
            db,
            user_id=booking.user_id,
            slot_direction_id=slot.direction_id,
        )
        booking.status = models.BookingStatus.canceled
        booking.canceled_at = now
        booking.canceled_by = actor
        booking.cancellation_reason = SLOT_CANCELED_REASON

        payments = (
            db.query(models.Payment)
            .filter(models.Payment.class_slot_id == slot.id)
            .filter(models.Payment.user_id == booking.user_id)
            .filter(models.Payment.status == models.PaymentStatus.pending)
            .all()
        )
        for payment in payments:
            payment.status = models.PaymentStatus.canceled
            payment.updated_at = now
            payment.confirmation_url = None

        direction_name = None
        if booking.slot and booking.slot.direction:
            direction_name = booking.slot.direction.name
        message_text = None
        if booking.slot:
            message_text = (
                f"Занятие «{direction_name or 'Занятие'}» "
                f"{booking.slot.starts_at.isoformat()} отменено. "
                "Мы вернули вам одно занятие."
            )

        db.add(
            models.AuditLog(
                actor_type=models.ActorType.admin,
                actor_id=actor_id,
                action="slot_canceled_notification",
                payload={
                    "user_id": booking.user_id,
                    "slot_id": slot.id,
                    "slot_starts_at": booking.slot.starts_at.isoformat()
                    if booking.slot
                    else None,
                    "direction": direction_name,
                    "message": message_text,
                },
            )
        )

    db.commit()
    db.refresh(slot)
    return slot

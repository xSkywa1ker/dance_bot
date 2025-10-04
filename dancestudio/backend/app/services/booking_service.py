from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import models
from ..db.models.booking import BookingSource, BookingStatus
from ..db.models.class_slot import SlotStatus
from ..db.models.subscription import SubscriptionStatus
from .subscription_service import grant_class_credit


class BookingError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _slot_starts_in_future(slot: models.ClassSlot) -> bool:
    starts_at = slot.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)
    return starts_at > _utc_now()


def book_class(db: Session, user: models.User, slot: models.ClassSlot) -> models.Booking:
    if slot.status != SlotStatus.scheduled:
        raise BookingError("Slot is not available")
    if not _slot_starts_in_future(slot):
        raise BookingError("Slot start time is in the past")
    transaction_ctx = db.begin_nested() if db.in_transaction() else db.begin()
    try:
        with transaction_ctx:
            locked_slot = (
                db.execute(
                    select(models.ClassSlot)
                    .where(models.ClassSlot.id == slot.id)
                    .with_for_update()
                )
                .scalar_one()
            )
            if not _slot_starts_in_future(locked_slot):
                raise BookingError("Slot start time is in the past")
            active_bookings = db.scalar(
                select(func.count(models.Booking.id)).where(
                    models.Booking.class_slot_id == locked_slot.id,
                    models.Booking.status.in_([
                        BookingStatus.reserved,
                        BookingStatus.confirmed,
                    ]),
                )
            )
            if active_bookings >= locked_slot.capacity:
                raise BookingError("No free seats")
            existing = db.execute(
                select(models.Booking).where(
                    models.Booking.user_id == user.id,
                    models.Booking.class_slot_id == locked_slot.id,
                )
            ).scalar_one_or_none()
            reuse_booking = False
            if existing:
                if existing.status in [BookingStatus.reserved, BookingStatus.confirmed]:
                    raise BookingError("Already booked")
                booking = existing
                reuse_booking = True
            else:
                booking = models.Booking(
                    user_id=user.id,
                    class_slot_id=locked_slot.id,
                    source=BookingSource.bot,
                )
                db.add(booking)
            now = _utc_now()
            subscription = (
                db.execute(
                    select(models.Subscription)
                    .where(
                        models.Subscription.user_id == user.id,
                        models.Subscription.status == SubscriptionStatus.active,
                        models.Subscription.remaining_classes > 0,
                        models.Subscription.valid_from <= now,
                        models.Subscription.valid_to >= now,
                    )
                    .order_by(models.Subscription.valid_to)
                )
                .scalars()
                .first()
            )
            if subscription and (
                not subscription.product.direction_limit_id
                or subscription.product.direction_limit_id == locked_slot.direction_id
            ):
                subscription.remaining_classes -= 1
                booking.status = BookingStatus.confirmed
            else:
                booking.status = BookingStatus.reserved
            booking.source = BookingSource.bot
            booking.created_at = now
            booking.canceled_at = None
            booking.canceled_by = None
            booking.cancellation_reason = None
            if reuse_booking:
                db.add(booking)
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "")
        if constraint == "uq_booking_user_slot":
            raise BookingError("Already booked") from exc
        raise
    return booking


def cancel_booking(db: Session, booking: models.Booking, actor: str) -> models.Booking:
    slot = booking.slot
    now = _utc_now()
    slot_starts_at = slot.starts_at
    if slot_starts_at.tzinfo is None:
        slot_starts_at = slot_starts_at.replace(tzinfo=timezone.utc)
    if slot_starts_at - now < timedelta(hours=24):
        booking.status = BookingStatus.late_cancel
        db.commit()
        return booking
    if booking.status not in [BookingStatus.confirmed, BookingStatus.reserved]:
        raise BookingError("Cannot cancel")
    grant_class_credit(
        db,
        user_id=booking.user_id,
        slot_direction_id=slot.direction_id,
    )
    booking.status = BookingStatus.canceled
    booking.canceled_at = now
    booking.canceled_by = actor
    db.commit()
    db.refresh(booking)
    return booking

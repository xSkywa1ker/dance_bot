from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..db import models
from ..db.models.class_slot import SlotStatus
from ..db.models.booking import BookingStatus, BookingSource
from ..db.models.subscription import SubscriptionStatus


class BookingError(Exception):
    pass


def book_class(db: Session, user: models.User, slot: models.ClassSlot) -> models.Booking:
    if slot.status != SlotStatus.scheduled:
        raise BookingError("Slot is not available")
    transaction_ctx = db.begin_nested() if db.in_transaction() else db.begin()
    with transaction_ctx:
        locked_slot = (
            db.execute(select(models.ClassSlot).where(models.ClassSlot.id == slot.id).with_for_update())
            .scalar_one()
        )
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
        if existing:
            return existing
        subscription = (
            db.execute(
                select(models.Subscription)
                .where(
                    models.Subscription.user_id == user.id,
                    models.Subscription.status == SubscriptionStatus.active,
                    models.Subscription.remaining_classes > 0,
                    models.Subscription.valid_from <= datetime.utcnow(),
                    models.Subscription.valid_to >= datetime.utcnow(),
                )
                .order_by(models.Subscription.valid_to)
            ).scalars().first()
        )
        if subscription and (
            not subscription.product.direction_limit_id
            or subscription.product.direction_limit_id == locked_slot.direction_id
        ):
            subscription.remaining_classes -= 1
            booking = models.Booking(
                user_id=user.id,
                class_slot_id=locked_slot.id,
                status=BookingStatus.confirmed,
                source=BookingSource.bot,
            )
        else:
            booking = models.Booking(
                user_id=user.id,
                class_slot_id=locked_slot.id,
                status=BookingStatus.reserved,
                source=BookingSource.bot,
            )
        db.add(booking)
    return booking


def cancel_booking(db: Session, booking: models.Booking, actor: str) -> models.Booking:
    slot = booking.slot
    now = datetime.utcnow()
    if slot.starts_at - now < timedelta(hours=24):
        booking.status = BookingStatus.late_cancel
        db.commit()
        return booking
    if booking.status not in [BookingStatus.confirmed, BookingStatus.reserved]:
        raise BookingError("Cannot cancel")
    if booking.status == BookingStatus.confirmed:
        subscription = (
            db.query(models.Subscription)
            .filter(
                models.Subscription.user_id == booking.user_id,
                models.Subscription.status == SubscriptionStatus.active,
            )
            .first()
        )
        if subscription:
            subscription.remaining_classes += 1
    booking.status = BookingStatus.canceled
    booking.canceled_at = now
    booking.canceled_by = actor
    db.commit()
    db.refresh(booking)
    return booking

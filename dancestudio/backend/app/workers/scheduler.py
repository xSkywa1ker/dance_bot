from datetime import datetime, timedelta
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import and_

from ..core.constants import (
    PAYMENT_TIMEOUT_REASON,
    RESERVATION_PAYMENT_TIMEOUT,
    SYSTEM_ACTOR,
)
from ..db import models
from ..db.session import SessionLocal

logger = logging.getLogger(__name__)


def send_reminders() -> None:
    with SessionLocal() as db:
        upcoming = (
            db.query(models.ClassSlot)
            .filter(models.ClassSlot.starts_at.between(datetime.utcnow() + timedelta(hours=23), datetime.utcnow() + timedelta(hours=25)))
            .all()
        )
        for slot in upcoming:
            logger.info("Reminder for slot", extra={"slot_id": slot.id})


def cleanup_reserved() -> None:
    with SessionLocal() as db:
        now = datetime.utcnow()
        cutoff = now - RESERVATION_PAYMENT_TIMEOUT
        stale = (
            db.query(models.Booking)
            .filter(models.Booking.status == models.BookingStatus.reserved)
            .filter(models.Booking.created_at < cutoff)
            .all()
        )
        for booking in stale:
            booking.status = models.BookingStatus.canceled
            booking.canceled_at = now
            booking.canceled_by = SYSTEM_ACTOR
            booking.cancellation_reason = PAYMENT_TIMEOUT_REASON
            pending_payments = (
                db.query(models.Payment)
                .filter(
                    and_(
                        models.Payment.class_slot_id == booking.class_slot_id,
                        models.Payment.user_id == booking.user_id,
                        models.Payment.status == models.PaymentStatus.pending,
                    )
                )
                .all()
            )
            for payment in pending_payments:
                payment.status = models.PaymentStatus.canceled
                payment.updated_at = now
                payment.confirmation_url = None
        db.commit()


def process_waitlist() -> None:
    with SessionLocal() as db:
        notifications = (
            db.query(models.Waitlist)
            .filter(models.Waitlist.status == models.WaitlistStatus.notified)
            .all()
        )
        for wait in notifications:
            logger.info("Waitlist notification", extra={"wait_id": wait.id})
            wait.status = models.WaitlistStatus.joined
        db.commit()


def get_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_reminders, "interval", hours=1)
    scheduler.add_job(cleanup_reserved, "interval", minutes=1)
    scheduler.add_job(process_waitlist, "interval", minutes=30)
    return scheduler

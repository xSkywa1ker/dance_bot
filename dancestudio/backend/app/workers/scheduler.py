from datetime import datetime, timedelta
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ..db.session import SessionLocal
from ..db import models

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
        stale = (
            db.query(models.Booking)
            .filter(models.Booking.status == models.BookingStatus.reserved)
            .filter(models.Booking.created_at < datetime.utcnow() - timedelta(hours=2))
            .all()
        )
        for booking in stale:
            booking.status = models.BookingStatus.canceled
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
    scheduler.add_job(cleanup_reserved, "interval", hours=1)
    scheduler.add_job(process_waitlist, "interval", minutes=30)
    return scheduler

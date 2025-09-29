from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...api import deps
from ...db import models, schemas
from ...db.session import get_db
from ...services import booking_service, payment_service

router = APIRouter(prefix="/bot", tags=["bot"])


class SyncUserRequest(BaseModel):
    tg_id: int
    full_name: str | None = None
    phone: str | None = None


class BotBookingSlot(BaseModel):
    id: int
    direction_id: int
    direction_name: str
    starts_at: datetime
    duration_min: int
    price_single_visit: float | None
    allow_subscription: bool


class BotBookingResponse(BaseModel):
    id: int
    status: str
    slot: BotBookingSlot
    needs_payment: bool
    payment_status: str | None = None
    payment_url: str | None = None


class BotBookingRequest(SyncUserRequest):
    slot_id: int


def _sync_user(db: Session, payload: SyncUserRequest) -> models.User:
    user = db.query(models.User).filter_by(tg_id=payload.tg_id).first()
    created = False
    if not user:
        user = models.User(tg_id=payload.tg_id)
        db.add(user)
        created = True
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if created or payload.full_name is not None or payload.phone is not None:
        db.commit()
        db.refresh(user)
    return user


def _latest_payment(db: Session, booking: models.Booking) -> models.Payment | None:
    return (
        db.query(models.Payment)
        .filter_by(class_slot_id=booking.class_slot_id, user_id=booking.user_id)
        .order_by(models.Payment.created_at.desc())
        .first()
    )


def _serialize_booking(
    booking: models.Booking,
    *,
    payment: models.Payment | None = None,
    payment_url: str | None = None,
) -> BotBookingResponse:
    slot = booking.slot
    direction = slot.direction
    status_value = booking.status.value if hasattr(booking.status, "value") else str(booking.status)
    payment_status = None
    if payment:
        payment_status = payment.status.value if hasattr(payment.status, "value") else str(payment.status)
    price = float(slot.price_single_visit) if slot.price_single_visit is not None else None
    return BotBookingResponse(
        id=booking.id,
        status=status_value,
        slot=BotBookingSlot(
            id=slot.id,
            direction_id=slot.direction_id,
            direction_name=direction.name if direction else "",
            starts_at=slot.starts_at,
            duration_min=slot.duration_min,
            price_single_visit=price,
            allow_subscription=slot.allow_subscription,
        ),
        needs_payment=status_value == models.BookingStatus.reserved.value,
        payment_status=payment_status,
        payment_url=payment_url,
    )


@router.post("/users/sync", response_model=schemas.User)
def sync_user(
    payload: SyncUserRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(deps.verify_bot_token)],
) -> schemas.User:
    user = _sync_user(db, payload)
    return schemas.User.model_validate(user)


@router.get("/users/{tg_id}/bookings", response_model=list[BotBookingResponse])
def list_user_bookings(
    tg_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(deps.verify_bot_token)],
) -> list[BotBookingResponse]:
    user = db.query(models.User).filter_by(tg_id=tg_id).first()
    if not user:
        return []
    upcoming = (
        db.query(models.Booking)
        .join(models.ClassSlot)
        .filter(models.Booking.user_id == user.id)
        .filter(models.ClassSlot.starts_at >= datetime.utcnow())
        .filter(models.Booking.status.in_([models.BookingStatus.confirmed, models.BookingStatus.reserved]))
        .order_by(models.ClassSlot.starts_at)
        .all()
    )
    results: list[BotBookingResponse] = []
    for booking in upcoming:
        payment = _latest_payment(db, booking)
        results.append(_serialize_booking(booking, payment=payment))
    return results


@router.post("/bookings", response_model=BotBookingResponse)
def create_booking(
    payload: BotBookingRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(deps.verify_bot_token)],
) -> BotBookingResponse:
    user = _sync_user(db, payload)
    slot = db.get(models.ClassSlot, payload.slot_id)
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")
    booking = booking_service.book_class(db, user, slot)
    db.refresh(booking)
    payment_url: str | None = None
    payment = _latest_payment(db, booking)
    if booking.status == models.BookingStatus.reserved:
        amount = float(slot.price_single_visit or 0)
        payment, gateway_response = payment_service.create_payment(
            db,
            user,
            amount=amount,
            purpose=models.PaymentPurpose.single_visit,
            slot=slot,
        )
        payment_url = gateway_response.get("confirmation_url") or gateway_response.get("return_url")
        db.refresh(booking)
    return _serialize_booking(booking, payment=payment, payment_url=payment_url)

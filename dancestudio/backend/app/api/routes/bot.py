from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, selectinload

from ...api import deps
from ...core.constants import RESERVATION_PAYMENT_TIMEOUT
from ...db import models, schemas
from ...db.session import get_db
from ...services import booking_service, payment_service, settings_service

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
    reservation_expires_at: datetime | None = None


class BotBookingRequest(SyncUserRequest):
    slot_id: int


class BotBookingCancelRequest(SyncUserRequest):
    pass


class BotSubscriptionPurchaseRequest(SyncUserRequest):
    product_id: int


class BotSubscription(BaseModel):
    id: int
    product_id: int
    product_name: str
    remaining_classes: int
    total_classes: int | None = None
    valid_from: datetime
    valid_to: datetime
    status: str


class BotPaymentResponse(BaseModel):
    payment_id: int
    status: str
    payment_url: str | None = None


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
    reservation_expires_at = None
    if booking.status == models.BookingStatus.reserved:
        created_at = booking.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        reservation_expires_at = created_at + RESERVATION_PAYMENT_TIMEOUT
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
        reservation_expires_at=reservation_expires_at,
    )


@router.post("/users/sync", response_model=schemas.User)
def sync_user(
    payload: SyncUserRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(deps.verify_bot_token)],
) -> schemas.User:
    user = _sync_user(db, payload)
    return schemas.User.model_validate(user)


@router.get("/addresses", response_model=schemas.StudioAddresses)
def get_addresses(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(deps.verify_bot_token)],
) -> schemas.StudioAddresses:
    addresses = settings_service.get_addresses(db)
    return schemas.StudioAddresses(addresses=addresses)


@router.get("/users/{tg_id}/bookings", response_model=list[BotBookingResponse])
def list_user_bookings(
    tg_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(deps.verify_bot_token)],
) -> list[BotBookingResponse]:
    user = db.query(models.User).filter_by(tg_id=tg_id).first()
    if not user:
        return []
    now = datetime.now(timezone.utc)
    cutoff = now - RESERVATION_PAYMENT_TIMEOUT
    upcoming = (
        db.query(models.Booking)
        .options(
            selectinload(models.Booking.slot).selectinload(models.ClassSlot.direction)
        )
        .join(models.ClassSlot)
        .filter(models.Booking.user_id == user.id)
        .filter(models.ClassSlot.starts_at >= now)
        .filter(
            or_(
                models.Booking.status == models.BookingStatus.confirmed,
                and_(
                    models.Booking.status == models.BookingStatus.reserved,
                    models.Booking.created_at >= cutoff,
                ),
            )
        )
        .order_by(models.ClassSlot.starts_at)
        .all()
    )
    results: list[BotBookingResponse] = []
    for booking in upcoming:
        payment = _latest_payment(db, booking)
        payment_url = None
        if (
            payment
            and payment.status == models.PaymentStatus.pending
            and payment.confirmation_url
        ):
            payment_url = payment.confirmation_url
        results.append(
            _serialize_booking(
                booking,
                payment=payment,
                payment_url=payment_url,
            )
        )
    return results


@router.get("/users/{tg_id}/subscriptions", response_model=list[BotSubscription])
def list_user_subscriptions(
    tg_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(deps.verify_bot_token)],
) -> list[BotSubscription]:
    user = db.query(models.User).filter_by(tg_id=tg_id).first()
    if not user:
        return []
    now = datetime.now(timezone.utc)
    subscriptions = (
        db.query(models.Subscription)
        .options(selectinload(models.Subscription.product))
        .filter(models.Subscription.user_id == user.id)
        .filter(models.Subscription.status == models.SubscriptionStatus.active)
        .filter(models.Subscription.valid_to >= now)
        .order_by(models.Subscription.valid_to)
        .all()
    )
    results: list[BotSubscription] = []
    for subscription in subscriptions:
        product = subscription.product
        status_value = (
            subscription.status.value
            if hasattr(subscription.status, "value")
            else str(subscription.status)
        )
        results.append(
            BotSubscription(
                id=subscription.id,
                product_id=subscription.product_id,
                product_name=product.name if product else "Абонемент",
                remaining_classes=subscription.remaining_classes,
                total_classes=product.classes_count if product else None,
                valid_from=subscription.valid_from,
                valid_to=subscription.valid_to,
                status=status_value,
            )
        )
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
    try:
        booking = booking_service.book_class(db, user, slot)
    except booking_service.BookingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
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
        payment_url = payment.confirmation_url or (
            gateway_response.get("confirmation_url")
            or gateway_response.get("return_url")
        )
    if db.in_transaction():
        db.commit()
    db.refresh(booking)
    return _serialize_booking(booking, payment=payment, payment_url=payment_url)


@router.post("/bookings/{booking_id}/cancel", response_model=BotBookingResponse)
def cancel_booking(
    booking_id: int,
    payload: BotBookingCancelRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(deps.verify_bot_token)],
) -> BotBookingResponse:
    user = db.query(models.User).filter_by(tg_id=payload.tg_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    booking = db.get(models.Booking, booking_id)
    if not booking or booking.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    booking = booking_service.cancel_booking(db, booking, actor=f"bot:{user.tg_id}")
    payment = _latest_payment(db, booking)
    return _serialize_booking(booking, payment=payment)


@router.post("/payments/subscription", response_model=BotPaymentResponse)
def purchase_subscription(
    payload: BotSubscriptionPurchaseRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(deps.verify_bot_token)],
) -> BotPaymentResponse:
    user = _sync_user(db, payload)
    product = db.get(models.Product, payload.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if product.type != models.ProductType.subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not a subscription",
        )
    payment, gateway_response = payment_service.create_payment(
        db,
        user,
        amount=float(product.price),
        purpose=models.PaymentPurpose.subscription,
        product=product,
    )
    payment_url = gateway_response.get("confirmation_url") or gateway_response.get("return_url")
    status_value = (
        payment.status.value if hasattr(payment.status, "value") else str(payment.status)
    )
    return BotPaymentResponse(
        payment_id=payment.id,
        status=status_value,
        payment_url=payment_url,
    )

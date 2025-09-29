from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from ...api import deps
from ...db.session import get_db
from ...db import models, schemas
from ...services import booking_service

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("", response_model=list[schemas.Booking])
def list_bookings(
    slot_id: int | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager", "viewer")),
):
    query = (
        db.query(models.Booking)
        .options(
            selectinload(models.Booking.user),
            selectinload(models.Booking.slot).selectinload(models.ClassSlot.direction),
        )
    )
    if slot_id:
        query = query.filter(models.Booking.class_slot_id == slot_id)
    if user_id:
        query = query.filter(models.Booking.user_id == user_id)
    return query.all()


@router.post("", response_model=schemas.Booking)
def create_booking(
    payload: schemas.BookingCreate,
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager")),
):
    user = db.get(models.User, payload.user_id)
    slot = db.get(models.ClassSlot, payload.class_slot_id)
    if not user or not slot:
        raise HTTPException(status_code=404, detail="User or slot not found")
    try:
        booking = booking_service.book_class(db, user, slot)
    except booking_service.BookingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return booking


@router.post("/{booking_id}/cancel", response_model=schemas.Booking)
def cancel_booking(
    booking_id: int,
    payload: schemas.BookingCancel,
    db: Session = Depends(get_db),
    admin: models.AdminUser = Depends(deps.require_roles("admin", "manager")),
):
    booking = db.get(models.Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    try:
        return booking_service.cancel_booking(db, booking, actor=admin.login)
    except booking_service.BookingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/stats")
def booking_stats(db: Session = Depends(get_db), _: models.AdminUser = Depends(deps.require_roles("admin", "manager"))):
    total = db.query(models.Booking).count()
    confirmed = (
        db.query(models.Booking)
        .filter(models.Booking.status == models.BookingStatus.confirmed)
        .count()
    )
    return {"total": total, "confirmed": confirmed}

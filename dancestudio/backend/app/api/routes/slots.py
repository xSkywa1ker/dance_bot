from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from ...api import deps
from ...db.session import get_db
from ...db import models, schemas
from ...services import schedule_service

router = APIRouter(prefix="/slots", tags=["slots"])


@router.get("", response_model=list[schemas.ClassSlot])
def list_slots(
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    direction_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.ClassSlot)
    if from_dt:
        query = query.filter(models.ClassSlot.starts_at >= from_dt)
    if to_dt:
        query = query.filter(models.ClassSlot.starts_at <= to_dt)
    if direction_id:
        query = query.filter(models.ClassSlot.direction_id == direction_id)
    slots = query.order_by(models.ClassSlot.starts_at).all()
    slot_ids = [slot.id for slot in slots]
    if slot_ids:
        active_counts = dict(
            db.query(
                models.Booking.class_slot_id,
                func.count(models.Booking.id),
            )
            .filter(models.Booking.class_slot_id.in_(slot_ids))
            .filter(
                models.Booking.status.in_(
                    [models.BookingStatus.reserved, models.BookingStatus.confirmed]
                )
            )
            .group_by(models.Booking.class_slot_id)
            .all()
        )
    else:
        active_counts = {}
    for slot in slots:
        booked = int(active_counts.get(slot.id, 0))
        capacity = int(slot.capacity or 0)
        available = max(capacity - booked, 0) if capacity else 0
        setattr(slot, "booked_seats", booked)
        setattr(slot, "available_seats", available)
    return slots


@router.post("", response_model=schemas.ClassSlot)
def create_slot(
    payload: schemas.ClassSlotCreate,
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager")),
):
    slot = models.ClassSlot(**payload.model_dump())
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.patch("/{slot_id}", response_model=schemas.ClassSlot)
def update_slot(
    slot_id: int,
    payload: schemas.ClassSlotUpdate,
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager")),
):
    slot = db.get(models.ClassSlot, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(slot, key, value)
    db.commit()
    db.refresh(slot)
    return slot


@router.post("/{slot_id}/cancel", response_model=schemas.ClassSlot)
def cancel_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    admin: models.AdminUser = Depends(deps.require_roles("admin", "manager")),
):
    slot = db.get(models.ClassSlot, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    slot = schedule_service.cancel_slot(
        db,
        slot,
        actor=admin.login,
        actor_id=admin.id,
    )
    return slot


@router.delete("/{slot_id}")
def delete_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin")),
):
    slot = db.get(models.ClassSlot, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    db.delete(slot)
    db.commit()
    return {"status": "deleted"}

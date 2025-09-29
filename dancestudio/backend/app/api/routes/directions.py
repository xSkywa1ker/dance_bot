from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...api import deps
from ...db.session import get_db
from ...db import models, schemas

router = APIRouter(prefix="/directions", tags=["directions"])


@router.get("", response_model=list[schemas.Direction])
def list_directions(db: Session = Depends(get_db)):
    return db.query(models.Direction).filter_by(is_active=True).all()


@router.post("", response_model=schemas.Direction)
def create_direction(
    payload: schemas.DirectionCreate,
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager")),
):
    direction = models.Direction(**payload.model_dump())
    db.add(direction)
    db.commit()
    db.refresh(direction)
    return direction


@router.patch("/{direction_id}", response_model=schemas.Direction)
def update_direction(
    direction_id: int,
    payload: schemas.DirectionUpdate,
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager")),
):
    direction = db.get(models.Direction, direction_id)
    if not direction:
        raise HTTPException(status_code=404, detail="Direction not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(direction, key, value)
    db.commit()
    db.refresh(direction)
    return direction


@router.delete("/{direction_id}")
def delete_direction(
    direction_id: int,
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin")),
):
    direction = db.get(models.Direction, direction_id)
    if not direction:
        raise HTTPException(status_code=404, detail="Direction not found")
    db.delete(direction)
    db.commit()
    return {"status": "deleted"}

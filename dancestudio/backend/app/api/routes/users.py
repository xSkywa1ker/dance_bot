from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ...api import deps
from ...db.session import get_db
from ...db import models, schemas
from ...services import subscription_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[schemas.User])
def list_users(
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager", "viewer")),
):
    return db.query(models.User).all()


@router.get("/search", response_model=list[schemas.User])
def search_users(
    q: str = Query(..., min_length=2, description="Часть ФИО"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager", "viewer")),
):
    pattern = f"%{q.strip()}%"
    results = (
        db.query(models.User)
        .filter(models.User.full_name.ilike(pattern))
        .order_by(models.User.full_name.asc())
        .limit(limit)
        .all()
    )
    return results


@router.get("/{user_id}", response_model=schemas.User)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager", "viewer")),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager")),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/manual-subscription", response_model=schemas.Subscription)
def grant_manual_subscription(
    user_id: int,
    payload: schemas.ManualSubscriptionGrant,
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager")),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    subscription = subscription_service.issue_manual_subscription(
        db,
        user_id=user.id,
        classes_count=payload.classes_count,
        validity_days=payload.validity_days,
    )
    return schemas.Subscription.model_validate(subscription)

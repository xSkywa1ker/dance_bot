from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, selectinload

from ..db import models

_COMPENSATION_PRODUCT_NAME = "Компенсация отмены занятия"
_COMPENSATION_VALIDITY_DAYS = 90
_MANUAL_PRODUCT_NAME = "Абонемент администратора"
_DEFAULT_MANUAL_VALIDITY_DAYS = 365


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_compensation_product(db: Session) -> models.Product:
    product = (
        db.query(models.Product)
        .filter(models.Product.name == _COMPENSATION_PRODUCT_NAME)
        .filter(models.Product.type == models.ProductType.subscription)
        .first()
    )
    if product:
        return product
    product = models.Product(
        type=models.ProductType.subscription,
        name=_COMPENSATION_PRODUCT_NAME,
        description="Кредит за отмененное занятие",
        price=0,
        classes_count=1,
        validity_days=_COMPENSATION_VALIDITY_DAYS,
        is_active=False,
    )
    db.add(product)
    db.flush()
    return product


def _get_manual_product(db: Session) -> models.Product:
    product = (
        db.query(models.Product)
        .filter(models.Product.name == _MANUAL_PRODUCT_NAME)
        .filter(models.Product.type == models.ProductType.subscription)
        .first()
    )
    if product:
        return product
    product = models.Product(
        type=models.ProductType.subscription,
        name=_MANUAL_PRODUCT_NAME,
        description="Абонемент, выданный администратором",
        price=0,
        classes_count=None,
        validity_days=None,
        is_active=False,
    )
    db.add(product)
    db.flush()
    return product


def grant_class_credit(
    db: Session,
    *,
    user_id: int,
    slot_direction_id: int | None = None,
) -> models.Subscription:
    """Return an active subscription with an extra class or create a new credit."""

    now = _now()
    subscription = (
        db.query(models.Subscription)
        .options(selectinload(models.Subscription.product))
        .filter(models.Subscription.user_id == user_id)
        .filter(models.Subscription.status == models.SubscriptionStatus.active)
        .filter(models.Subscription.valid_to >= now)
        .order_by(models.Subscription.valid_to)
        .first()
    )
    if subscription and subscription.product:
        direction_limit = subscription.product.direction_limit_id
        if direction_limit and slot_direction_id and direction_limit != slot_direction_id:
            subscription = None
    if subscription:
        subscription.remaining_classes += 1
        if subscription.initial_classes is not None:
            subscription.initial_classes += 1
        return subscription

    product = _get_compensation_product(db)
    validity_days = product.validity_days or _COMPENSATION_VALIDITY_DAYS
    subscription = (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == user_id)
        .filter(models.Subscription.status == models.SubscriptionStatus.active)
        .filter(models.Subscription.product_id == product.id)
        .filter(models.Subscription.valid_to >= now)
        .order_by(models.Subscription.valid_to.desc())
        .first()
    )
    if subscription:
        subscription.remaining_classes += 1
        target_valid_to = now + timedelta(days=validity_days)
        if subscription.valid_to < target_valid_to:
            subscription.valid_to = target_valid_to
        return subscription

    subscription = models.Subscription(
        user_id=user_id,
        product_id=product.id,
        remaining_classes=1,
        initial_classes=1,
        valid_from=now,
        valid_to=now + timedelta(days=validity_days),
        status=models.SubscriptionStatus.active,
    )
    db.add(subscription)
    return subscription


def issue_manual_subscription(
    db: Session,
    *,
    user_id: int,
    classes_count: int,
    validity_days: int | None = None,
) -> models.Subscription:
    now = _now()
    product = _get_manual_product(db)
    days = validity_days or _DEFAULT_MANUAL_VALIDITY_DAYS
    subscription = models.Subscription(
        user_id=user_id,
        product_id=product.id,
        remaining_classes=classes_count,
        initial_classes=classes_count,
        valid_from=now,
        valid_to=now + timedelta(days=days),
        status=models.SubscriptionStatus.active,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


__all__ = ["grant_class_credit", "issue_manual_subscription"]

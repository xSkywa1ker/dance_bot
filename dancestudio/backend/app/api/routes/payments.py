from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...api import deps
from ...db.session import get_db
from ...db import models, schemas
from ...services import payment_service
from ...services.payments import gateway
from ...config import get_settings

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=list[schemas.Payment])
def list_payments(
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager")),
):
    return db.query(models.Payment).all()


@router.post("/create", response_model=schemas.Payment)
def create_payment_endpoint(
    payload: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager")),
):
    user = db.get(models.User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    product = db.get(models.Product, payload.product_id) if payload.product_id else None
    slot = db.get(models.ClassSlot, payload.class_slot_id) if payload.class_slot_id else None
    payment, _ = payment_service.create_payment(
        db,
        user,
        amount=payload.amount,
        purpose=models.PaymentPurpose(payload.purpose),
        product=product,
        slot=slot,
    )
    return payment


@router.post("/webhook")
def payments_webhook(payload: dict, db: Session = Depends(get_db)):
    settings = get_settings()
    gateway_client = gateway.get_gateway(settings)
    parsed = gateway_client.parse_webhook(payload)
    order_id = parsed.get("order_id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Invalid webhook")
    payment = db.query(models.Payment).filter_by(order_id=order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    status_map = {
        "pending": models.PaymentStatus.pending,
        "succeeded": models.PaymentStatus.paid,
        "paid": models.PaymentStatus.paid,
        "canceled": models.PaymentStatus.canceled,
        "refunded": models.PaymentStatus.refunded,
        "failed": models.PaymentStatus.failed,
    }
    status_value = status_map.get(parsed.get("status"), models.PaymentStatus.failed)
    payment_service.apply_payment(db, payment, status_value)
    return {"status": "ok"}

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...api import deps
from ...db import schemas
from ...db.session import get_db
from ...services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/addresses", response_model=schemas.StudioAddresses)
def get_addresses(
    db: Session = Depends(get_db),
    _: None = Depends(deps.require_roles("admin", "manager")),
) -> schemas.StudioAddresses:
    addresses = settings_service.get_addresses(db)
    return schemas.StudioAddresses(addresses=addresses)


@router.put("/addresses", response_model=schemas.StudioAddresses)
def update_addresses(
    payload: schemas.StudioAddressesUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(deps.require_roles("admin", "manager")),
) -> schemas.StudioAddresses:
    addresses = settings_service.update_addresses(db, addresses=payload.addresses)
    return schemas.StudioAddresses(addresses=addresses)

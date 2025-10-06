from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request
from sqlalchemy.orm import Session

from ...api import deps
from ...db import models, schemas
from ...db.session import get_db
from ...services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


def _media_response(request: Request, asset: models.SettingMedia) -> schemas.SettingMedia:
    url = request.url_for("media", path=asset.file_path)
    return schemas.SettingMedia(
        id=asset.id,
        url=str(url),
        media_type=asset.media_type.value,
        filename=asset.file_name,
    )


@router.get("/addresses", response_model=schemas.StudioAddresses)
def get_addresses(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(deps.require_roles("admin", "manager")),
) -> schemas.StudioAddresses:
    addresses, media_items = settings_service.get_addresses(db)
    media = [_media_response(request, asset) for asset in media_items]
    return schemas.StudioAddresses(addresses=addresses, media=media)


@router.put("/addresses", response_model=schemas.StudioAddresses)
def update_addresses(
    request: Request,
    payload: schemas.StudioAddressesUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(deps.require_roles("admin", "manager")),
) -> schemas.StudioAddresses:
    addresses, media_items = settings_service.update_addresses(
        db,
        addresses=payload.addresses,
        media_ids=payload.media_ids,
    )
    media = [_media_response(request, asset) for asset in media_items]
    return schemas.StudioAddresses(addresses=addresses, media=media)


@router.post("/addresses/media", response_model=list[schemas.SettingMedia])
async def upload_addresses_media(
    request: Request,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(deps.require_roles("admin", "manager")),
) -> list[schemas.SettingMedia]:
    try:
        assets = settings_service.save_addresses_media(db, files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [_media_response(request, asset) for asset in assets]

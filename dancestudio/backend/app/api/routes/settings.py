from email.parser import BytesHeaderParser
from email.policy import default
from tempfile import SpooledTemporaryFile

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session
from starlette.datastructures import Headers
from multipart.multipart import parse_options_header

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


async def _extract_uploads(request: Request) -> list[UploadFile]:
    content_type = request.headers.get("content-type")
    if not content_type:
        raise HTTPException(status_code=400, detail="Missing Content-Type header")

    try:
        header_bytes = content_type.encode("latin-1")
    except UnicodeEncodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid Content-Type header") from exc

    try:
        media_type, params = parse_options_header(header_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Content-Type header") from exc

    if media_type != b"multipart/form-data" or b"boundary" not in params:
        raise HTTPException(status_code=400, detail="Malformed multipart payload")

    body = await request.body()
    if not body:
        return []

    boundary = params[b"boundary"]
    delimiter = b"--" + boundary

    header_parser = BytesHeaderParser(policy=default)

    uploads: list[UploadFile] = []
    for section in body.split(delimiter):
        if not section:
            continue

        if section.startswith(b"--"):
            # reached the closing boundary, stop processing
            break

        # Trim the leading line break that separates the boundary from headers
        section = section.lstrip(b"\r\n")
        if not section:
            continue

        # Separate headers from payload, accepting both CRLF and LF only separators
        header_bytes: bytes
        data: bytes
        for separator in (b"\r\n\r\n", b"\n\n", b"\r\r"):
            header_bytes, sep, data = section.partition(separator)
            if sep:
                break
        else:
            # Unable to find header/body separator, skip this part
            continue

        # Remove the trailing newline that precedes the next boundary without
        # touching newlines that are part of the uploaded content.
        if data.endswith(b"\r\n"):
            data = data[:-2]
        elif data.endswith(b"\n") or data.endswith(b"\r"):
            data = data[:-1]

        if not data:
            data = b""

        try:
            headers = header_parser.parsebytes(header_bytes)
        except Exception:  # pragma: no cover - defensive
            continue

        if headers.get_content_disposition() != "form-data":
            continue

        filename = headers.get_filename()
        if not filename:
            continue

        tmp = SpooledTemporaryFile()
        try:
            tmp.write(data)
            tmp.seek(0)
        except Exception:
            tmp.close()
            raise

        raw_headers = [
            (name.lower().encode("latin-1"), value.encode("latin-1"))
            for name, value in headers.items()
        ]
        if not any(name == b"content-type" for name, _ in raw_headers):
            raw_headers.append(
                (b"content-type", headers.get_content_type().encode("latin-1"))
            )

        uploads.append(
            UploadFile(
                file=tmp,
                size=len(data),
                filename=filename,
                headers=Headers(raw=raw_headers),
            )
        )

    return uploads


@router.post("/addresses/media", response_model=list[schemas.SettingMedia])
async def upload_addresses_media(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(deps.require_roles("admin", "manager")),
) -> list[schemas.SettingMedia]:
    files = await _extract_uploads(request)
    try:
        assets = settings_service.save_addresses_media(db, files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [_media_response(request, asset) for asset in assets]

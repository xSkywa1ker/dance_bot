from __future__ import annotations

from pathlib import Path
from typing import Iterable

from fastapi import UploadFile
from sqlalchemy.orm import Session

from ..db import models
from ..db.models.setting_media import SettingMediaType
from .storage import (
    ensure_media_directory,
    get_media_path,
    relative_media_path,
    remove_media_file,
)

ADDRESSES_KEY = "studio_addresses"
_MEDIA_SUBDIR = Path("settings") / "addresses"


def get_addresses(db: Session) -> tuple[str, list[models.SettingMedia]]:
    setting = db.get(models.Setting, ADDRESSES_KEY)
    addresses = setting.value if setting and setting.value is not None else ""
    media_items = (
        db.query(models.SettingMedia)
        .filter(models.SettingMedia.setting_key == ADDRESSES_KEY)
        .order_by(models.SettingMedia.created_at.asc())
        .all()
    )
    return addresses, media_items


def _guess_media_type(upload: UploadFile) -> SettingMediaType:
    content_type = (upload.content_type or "").lower()
    if content_type.startswith("image/"):
        return SettingMediaType.image
    if content_type.startswith("video/"):
        return SettingMediaType.video
    raise ValueError("Unsupported media type")


def save_addresses_media(db: Session, files: Iterable[UploadFile]) -> list[models.SettingMedia]:
    ensure_media_directory(_MEDIA_SUBDIR)
    created: list[models.SettingMedia] = []
    for upload in files:
        data = upload.file.read()
        if not data:
            continue
        media_type = _guess_media_type(upload)
        target_path = get_media_path(_MEDIA_SUBDIR, upload.filename)
        target_path.write_bytes(data)
        relative_path = relative_media_path(target_path)
        asset = models.SettingMedia(
            setting_key=ADDRESSES_KEY,
            file_path=relative_path,
            file_name=upload.filename or target_path.name,
            content_type=upload.content_type or "application/octet-stream",
            media_type=media_type,
        )
        db.add(asset)
        created.append(asset)
    if created:
        db.commit()
        for asset in created:
            db.refresh(asset)
    return created


def update_addresses(
    db: Session,
    *,
    addresses: str,
    media_ids: Iterable[int] | None = None,
) -> tuple[str, list[models.SettingMedia]]:
    value = addresses.strip()
    setting = db.get(models.Setting, ADDRESSES_KEY)
    if not setting:
        setting = models.Setting(key=ADDRESSES_KEY)
        db.add(setting)
    setting.value = value
    keep_ids = {int(media_id) for media_id in (media_ids or [])}
    existing = (
        db.query(models.SettingMedia)
        .filter(models.SettingMedia.setting_key == ADDRESSES_KEY)
        .all()
    )
    for asset in existing:
        if asset.id not in keep_ids:
            remove_media_file(asset.file_path)
            db.delete(asset)
    db.commit()
    db.refresh(setting)
    return get_addresses(db)


__all__ = [
    "ADDRESSES_KEY",
    "get_addresses",
    "save_addresses_media",
    "update_addresses",
]

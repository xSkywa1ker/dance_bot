from __future__ import annotations

from sqlalchemy.orm import Session

from ..db import models

ADDRESSES_KEY = "studio_addresses"


def get_addresses(db: Session) -> str:
    setting = db.get(models.Setting, ADDRESSES_KEY)
    return setting.value if setting and setting.value is not None else ""


def update_addresses(db: Session, *, addresses: str) -> str:
    value = addresses.strip()
    setting = db.get(models.Setting, ADDRESSES_KEY)
    if not setting:
        setting = models.Setting(key=ADDRESSES_KEY)
        db.add(setting)
    setting.value = value
    db.commit()
    db.refresh(setting)
    return setting.value or ""

from sqlalchemy.orm import Session
from ..db import models
from . import security


def authenticate_admin(db: Session, email: str, password: str) -> models.AdminUser | None:
    admin = db.query(models.AdminUser).filter_by(email=email).first()
    if not admin:
        return None
    if not security.verify_password(password, admin.password_hash):
        return None
    return admin

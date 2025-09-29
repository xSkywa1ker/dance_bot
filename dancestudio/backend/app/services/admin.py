import logging
from sqlalchemy.orm import Session

from ..core import security
from ..db import models

logger = logging.getLogger(__name__)


def ensure_admin_exists(session: Session, login: str, password: str) -> None:
    existing = session.query(models.AdminUser).filter_by(login=login).first()
    if existing:
        logger.info("Admin user '%s' already exists", login)
        return
    admin = models.AdminUser(
        login=login,
        password_hash=security.get_password_hash(password),
        role=models.AdminRole.admin,
    )
    session.add(admin)
    session.commit()
    logger.info("Created default admin user '%s'", login)

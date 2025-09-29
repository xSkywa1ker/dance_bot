import logging
from sqlalchemy.orm import Session

from ..core import security
from ..db import models

logger = logging.getLogger(__name__)


def ensure_admin_exists(session: Session, login: str, password: str) -> None:
    admin = session.query(models.AdminUser).filter_by(login=login).first()
    if admin:
        updated = False
        if not security.verify_password(password, admin.password_hash):
            admin.password_hash = security.get_password_hash(password)
            updated = True
        if admin.role != models.AdminRole.admin:
            admin.role = models.AdminRole.admin
            updated = True
        if updated:
            session.commit()
            logger.info("Updated default admin user '%s'", login)
        else:
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

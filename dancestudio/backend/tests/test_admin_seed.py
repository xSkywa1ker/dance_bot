from app.db import models
from app.services.admin import ensure_admin_exists
from app.core import security


def test_creates_default_admin(db_session):
    ensure_admin_exists(db_session, "admin_login", "strong_password")

    created = db_session.query(models.AdminUser).filter_by(login="admin_login").one()

    assert created.role == models.AdminRole.admin
    assert security.verify_password("strong_password", created.password_hash)


def test_updates_password_for_existing_admin(db_session):
    ensure_admin_exists(db_session, "admin_login", "old_password")

    ensure_admin_exists(db_session, "admin_login", "new_password")

    admins = db_session.query(models.AdminUser).filter_by(login="admin_login").all()
    assert len(admins) == 1
    assert security.verify_password("new_password", admins[0].password_hash)

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..db.session import SessionLocal
from ..db import models
from ..config import get_settings
from .admin import ensure_admin_exists


def seed(session: Session) -> None:
    settings = get_settings()
    ensure_admin_exists(session, settings.default_admin_login, settings.default_admin_password)
    if session.query(models.Direction).count() == 0:
        direction = models.Direction(name="Hip-Hop", description="Энергичные занятия")
        session.add(direction)
        session.flush()
        slot = models.ClassSlot(
            direction_id=direction.id,
            starts_at=datetime.utcnow() + timedelta(days=1),
            duration_min=60,
            capacity=10,
            price_single_visit=700,
        )
        session.add(slot)
    if session.query(models.Product).count() == 0:
        product = models.Product(
            type=models.ProductType.subscription,
            name="Абонемент на 8 занятий",
            description="Действует 30 дней",
            price=5000,
            classes_count=8,
            validity_days=30,
        )
        session.add(product)
    session.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
        print("Seed data created")

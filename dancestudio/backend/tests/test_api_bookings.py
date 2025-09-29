from datetime import datetime, timedelta
import importlib
from pathlib import Path
import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.db import models
from app.db.session import Base, get_db
from app.services import booking_service


@pytest.fixture()
def api_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_admin():
        return models.AdminUser(id=1, login="admin", role="admin")

    routes_pkg_name = "app.api.routes"
    routes_path = Path(__file__).resolve().parents[1] / "app/api/routes"
    original_routes_pkg = sys.modules.get(routes_pkg_name)
    temp_package = types.ModuleType(routes_pkg_name)
    temp_package.__path__ = [str(routes_path)]
    sys.modules[routes_pkg_name] = temp_package

    try:
        bookings_module = importlib.import_module("app.api.routes.bookings")
    finally:
        if original_routes_pkg is None:
            sys.modules.pop(routes_pkg_name, None)
        else:
            sys.modules[routes_pkg_name] = original_routes_pkg

    bookings_router = bookings_module.router

    test_app = FastAPI()
    test_app.include_router(bookings_router, prefix="/api/v1")

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[deps.get_current_admin] = override_get_current_admin

    with TestClient(test_app) as client:
        yield client, TestingSessionLocal

    test_app.dependency_overrides.clear()


def test_create_booking_capacity_conflict(api_client, monkeypatch):
    client, SessionLocal = api_client
    db = SessionLocal()

    direction = models.Direction(name="Hip-Hop")
    db.add(direction)
    db.commit()

    slot = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.utcnow() + timedelta(days=2),
        duration_min=60,
        capacity=1,
        price_single_visit=500,
    )
    user = models.User(tg_id=1)
    db.add_all([slot, user])
    db.commit()
    slot_id = slot.id
    user_id = user.id
    db.close()

    def raise_no_free_seats(*_args, **_kwargs):
        raise booking_service.BookingError("No free seats")

    monkeypatch.setattr(booking_service, "book_class", raise_no_free_seats)

    second_booking = client.post(
        "/api/v1/bookings",
        json={"user_id": user_id, "class_slot_id": slot_id},
    )
    assert second_booking.status_code == 409
    assert second_booking.json()["detail"] == "No free seats"


def test_cancel_booking_invalid_status_returns_bad_request(api_client):
    client, SessionLocal = api_client
    db = SessionLocal()

    direction = models.Direction(name="Jazz")
    db.add(direction)
    db.commit()

    slot = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.utcnow() + timedelta(days=2),
        duration_min=60,
        capacity=2,
        price_single_visit=500,
    )
    user = models.User(tg_id=42)
    db.add_all([slot, user])
    db.commit()

    booking = models.Booking(
        user_id=user.id,
        class_slot_id=slot.id,
        status=models.BookingStatus.canceled,
    )
    db.add(booking)
    db.commit()
    booking_id = booking.id
    db.close()

    response = client.post(f"/api/v1/bookings/{booking_id}/cancel", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot cancel"

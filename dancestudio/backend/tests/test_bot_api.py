import importlib
import sys
import types
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.core.constants import RESERVATION_PAYMENT_TIMEOUT
from app.db import models
from app.db.session import Base, get_db


@pytest.fixture()
def bot_api_client(monkeypatch):
    monkeypatch.setenv("BOT_API_TOKEN", "bot-secret")
    get_settings.cache_clear()

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

    routes_pkg_name = "app.api.routes"
    routes_path = Path(__file__).resolve().parents[1] / "app/api/routes"
    original_routes_pkg = sys.modules.get(routes_pkg_name)
    temp_package = types.ModuleType(routes_pkg_name)
    temp_package.__path__ = [str(routes_path)]
    sys.modules[routes_pkg_name] = temp_package

    try:
        bot_module = importlib.import_module("app.api.routes.bot")
    finally:
        if original_routes_pkg is None:
            sys.modules.pop(routes_pkg_name, None)
        else:
            sys.modules[routes_pkg_name] = original_routes_pkg

    bot_router = bot_module.router

    test_app = FastAPI()
    test_app.include_router(bot_router, prefix="/api/v1")

    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as client:
        yield client, TestingSessionLocal

    test_app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_sync_user_creates_user(bot_api_client):
    client, SessionLocal = bot_api_client
    response = client.post(
        "/api/v1/bot/users/sync",
        json={"tg_id": 123, "full_name": "Test User"},
        headers={"X-Bot-Token": "bot-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tg_id"] == 123
    assert data["full_name"] == "Test User"

    db = SessionLocal()
    user = db.query(models.User).filter_by(tg_id=123).one()
    assert user.full_name == "Test User"
    db.close()


def test_create_booking_creates_payment(bot_api_client):
    client, SessionLocal = bot_api_client
    db = SessionLocal()
    direction = models.Direction(name="Hip-Hop")
    db.add(direction)
    db.commit()

    slot = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.utcnow() + timedelta(days=2),
        duration_min=60,
        capacity=5,
        price_single_visit=700,
    )
    db.add(slot)
    db.commit()
    slot_id = slot.id
    db.close()

    response = client.post(
        "/api/v1/bot/bookings",
        json={"tg_id": 456, "slot_id": slot_id},
        headers={"X-Bot-Token": "bot-secret"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "confirmed"
    assert payload["needs_payment"] is False
    assert payload["slot"]["id"] == slot_id
    assert payload["payment_status"] == "paid"

    db = SessionLocal()
    booking = db.query(models.Booking).one()
    assert booking.status == models.BookingStatus.confirmed
    payment = db.query(models.Payment).one()
    assert payment.purpose == models.PaymentPurpose.single_visit
    assert payment.user_id == booking.user_id
    db.close()


def test_list_bookings_returns_upcoming(bot_api_client):
    client, SessionLocal = bot_api_client
    db = SessionLocal()
    direction = models.Direction(name="Jazz")
    db.add(direction)
    db.commit()

    slot = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.utcnow() + timedelta(days=1),
        duration_min=45,
        capacity=3,
        price_single_visit=800,
    )
    user = models.User(tg_id=999)
    db.add_all([slot, user])
    db.commit()

    booking = models.Booking(
        user_id=user.id,
        class_slot_id=slot.id,
        status=models.BookingStatus.confirmed,
    )
    db.add(booking)
    db.commit()
    db.close()

    response = client.get(
        "/api/v1/bot/users/999/bookings",
        headers={"X-Bot-Token": "bot-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["slot"]["direction_name"] == "Jazz"


def test_pending_booking_exposes_payment_link(bot_api_client):
    client, SessionLocal = bot_api_client
    db = SessionLocal()
    direction = models.Direction(name="Salsa")
    db.add(direction)
    db.commit()

    slot = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.utcnow() + timedelta(hours=2),
        duration_min=60,
        capacity=10,
        price_single_visit=900,
    )
    user = models.User(tg_id=1111)
    db.add_all([slot, user])
    db.commit()

    booking = models.Booking(
        user_id=user.id,
        class_slot_id=slot.id,
        status=models.BookingStatus.reserved,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    payment = models.Payment(
        user_id=user.id,
        class_slot_id=slot.id,
        amount=Decimal("900.00"),
        currency="RUB",
        provider=models.PaymentProvider.stub,
        order_id="order-test",
        status=models.PaymentStatus.pending,
        purpose=models.PaymentPurpose.single_visit,
        confirmation_url="http://example.com/pay",
    )
    db.add(payment)
    db.commit()
    db.close()

    response = client.get(
        "/api/v1/bot/users/1111/bookings",
        headers={"X-Bot-Token": "bot-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    booking_payload = data[0]
    assert booking_payload["needs_payment"] is True
    assert booking_payload["payment_url"] == "http://example.com/pay"
    assert booking_payload["reservation_expires_at"] is not None

    # Expire the reservation and ensure it is not returned anymore
    db = SessionLocal()
    stored_booking = db.query(models.Booking).one()
    stored_booking.created_at = datetime.utcnow() - RESERVATION_PAYMENT_TIMEOUT - timedelta(minutes=1)
    db.commit()
    db.close()

    response = client.get(
        "/api/v1/bot/users/1111/bookings",
        headers={"X-Bot-Token": "bot-secret"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_bot_token_required(bot_api_client):
    client, _ = bot_api_client
    response = client.post(
        "/api/v1/bot/users/sync",
        json={"tg_id": 1},
    )
    assert response.status_code == 401

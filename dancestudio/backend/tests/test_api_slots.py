from datetime import datetime, timedelta, timezone
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

from app.db import models
from app.db.session import Base, get_db


@pytest.fixture()
def slots_api_client():
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
    direction_column = models.ClassSlot.__table__.c.direction_id
    original_nullable = direction_column.nullable
    direction_column.nullable = True
    try:
        Base.metadata.create_all(bind=engine)
    finally:
        direction_column.nullable = original_nullable

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
        slots_module = importlib.import_module("app.api.routes.slots")
    finally:
        if original_routes_pkg is None:
            sys.modules.pop(routes_pkg_name, None)
        else:
            sys.modules[routes_pkg_name] = original_routes_pkg

    slots_router = slots_module.router

    test_app = FastAPI()
    test_app.include_router(slots_router, prefix="/api/v1")
    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as client:
        yield client, TestingSessionLocal

    test_app.dependency_overrides.clear()


def test_slots_without_direction_are_skipped(slots_api_client):
    client, SessionLocal = slots_api_client
    db = SessionLocal()

    direction = models.Direction(name="Hip-Hop")
    db.add(direction)
    db.commit()

    valid_slot = models.ClassSlot(
        direction_id=direction.id,
        starts_at=datetime.now(timezone.utc) + timedelta(days=1),
        duration_min=60,
        capacity=10,
        price_single_visit=500,
    )
    invalid_slot = models.ClassSlot(
        direction_id=None,
        starts_at=datetime.now(timezone.utc) + timedelta(days=2),
        duration_min=60,
        capacity=10,
        price_single_visit=500,
    )

    db.add_all([valid_slot, invalid_slot])
    db.commit()
    db.close()

    response = client.get("/api/v1/slots")

    assert response.status_code == 200
    slots = response.json()
    assert len(slots) == 1
    assert slots[0]["id"] == valid_slot.id
    assert slots[0]["direction_id"] == direction.id

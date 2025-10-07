from pathlib import Path
import importlib
import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.db import models
from app.db.session import Base, get_db


@pytest.fixture()
def settings_api_client(monkeypatch, tmp_path):
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

    from app.services import storage

    media_root = tmp_path / "media"
    media_root.mkdir()
    monkeypatch.setattr(storage, "BASE_MEDIA_DIR", media_root)

    routes_pkg_name = "app.api.routes"
    routes_path = Path(__file__).resolve().parents[1] / "app/api/routes"
    original_routes_pkg = sys.modules.get(routes_pkg_name)
    temp_package = types.ModuleType(routes_pkg_name)
    temp_package.__path__ = [str(routes_path)]
    sys.modules[routes_pkg_name] = temp_package

    try:
        settings_module = importlib.import_module("app.api.routes.settings")
    finally:
        if original_routes_pkg is None:
            sys.modules.pop(routes_pkg_name, None)
        else:
            sys.modules[routes_pkg_name] = original_routes_pkg

    settings_router = settings_module.router

    test_app = FastAPI()
    test_app.include_router(settings_router, prefix="/api/v1")
    test_app.mount("/media", StaticFiles(directory=media_root), name="media")

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[deps.get_current_admin] = override_get_current_admin

    with TestClient(test_app) as client:
        yield client, TestingSessionLocal, media_root

    test_app.dependency_overrides.clear()


def test_upload_addresses_media_accepts_lf_only(settings_api_client):
    client, SessionLocal, media_root = settings_api_client

    boundary = "Boundary123"
    payload = b"".join(
        [
            f"--{boundary}\n".encode(),
            b"Content-Disposition: form-data; name=\"files\"; filename=\"banner.png\"\n",
            b"Content-Type: image/png\n\n",
            b"PNGDATA",
            f"\n--{boundary}--".encode(),
        ]
    )

    response = client.post(
        "/api/v1/settings/addresses/media",
        content=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    assert response.status_code == 200
    created = response.json()
    assert len(created) == 1
    assert created[0]["filename"] == "banner.png"
    assert created[0]["media_type"] == "image"

    db = SessionLocal()
    assets = db.query(models.SettingMedia).all()
    assert len(assets) == 1
    saved_asset = assets[0]
    assert saved_asset.content_type == "image/png"
    file_path = media_root / saved_asset.file_path
    assert file_path.exists()
    assert file_path.read_bytes().startswith(b"PNGDATA")
    db.close()


def test_upload_addresses_media_standard_form(settings_api_client):
    client, SessionLocal, media_root = settings_api_client

    response = client.post(
        "/api/v1/settings/addresses/media",
        files={"files": ("poster.jpg", b"JPEGDATA", "image/jpeg")},
    )

    assert response.status_code == 200
    created = response.json()
    assert len(created) == 1
    assert created[0]["filename"].endswith(".jpg")

    db = SessionLocal()
    assets = db.query(models.SettingMedia).all()
    assert len(assets) == 1
    saved_asset = assets[0]
    assert saved_asset.content_type == "image/jpeg"
    assert (media_root / saved_asset.file_path).exists()
    db.close()

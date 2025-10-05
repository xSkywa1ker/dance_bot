from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.py"


def _load_settings(monkeypatch: pytest.MonkeyPatch, **env: str):
    monkeypatch.delenv("PAYMENT_PROVIDER_TOKEN", raising=False)
    monkeypatch.delenv("PROVIDER_TOKEN", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    spec = importlib.util.spec_from_file_location("temp_bot_config", _CONFIG_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BotSettings()


def test_payment_provider_token_env(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _load_settings(monkeypatch, PAYMENT_PROVIDER_TOKEN="token-from-env")
    assert settings.payment_provider_token == "token-from-env"


def test_provider_token_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _load_settings(monkeypatch, PROVIDER_TOKEN="legacy-token")
    assert settings.payment_provider_token == "legacy-token"

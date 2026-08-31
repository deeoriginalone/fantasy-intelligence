import importlib
import os
import sys

import pytest


@pytest.fixture(autouse=True)
def isolate_runtime_modules():
    runtime_modules = [
        "config",
        "auth",
        "app",
        "pickem_pg_store",
        "pickem_inputs_routes",
        "pickem_feed_routes",
        "pickem_routes",
        "market_routes",
        "survivor_routes",
    ]
    for module_name in runtime_modules:
        sys.modules.pop(module_name, None)
    yield
    for module_name in runtime_modules:
        sys.modules.pop(module_name, None)


@pytest.fixture
def db_env(monkeypatch):
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret")
    monkeypatch.setenv("DB_HOST", "db.primary")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "fantasy_intelligence")
    monkeypatch.setenv("DB_USER", "fantasy")
    monkeypatch.setenv("DB_PASSWORD", "secret123")
    monkeypatch.setenv("ADMIN_TOKEN", "admin-token")
    monkeypatch.setenv("SLEEPER_LEAGUE_ID", "league-123")
    monkeypatch.setenv("SLEEPER_DRAFT_ID", "draft-123")

    monkeypatch.setenv("FI_DB_HOST", "fi-db-host")
    monkeypatch.setenv("FI_DB_PORT", "6543")
    monkeypatch.setenv("FI_DB_NAME", "fi_fantasy")
    monkeypatch.setenv("FI_DB_USER", "fi_user")
    monkeypatch.setenv("FI_DB_PASSWORD", "fi_password")


def load_runtime_modules():
    import config as config_module
    import pickem_pg_store as pickem_store_module
    import app as app_module

    importlib.reload(config_module)
    importlib.reload(pickem_store_module)
    importlib.reload(app_module)
    return config_module, app_module, pickem_store_module


def test_config_db_kwargs_returns_expected_fields(db_env):
    config_module, _, _ = load_runtime_modules()
    expected = {
        "host": "db.primary",
        "port": 5433,
        "dbname": "fantasy_intelligence",
        "user": "fantasy",
        "password": "secret123",
    }

    assert config_module.Config.db_kwargs() == expected


def test_pickem_store_uses_centralized_config(db_env, monkeypatch):
    _, _, pickem_store_module = load_runtime_modules()
    calls = []

    def fake_connect(**kwargs):
        calls.append(kwargs)
        return "fake-connection"

    monkeypatch.setattr(pickem_store_module.psycopg2, "connect", fake_connect)
    result = pickem_store_module.connect()

    assert result == "fake-connection"
    assert calls == [pickem_store_module.Config.db_kwargs()]
    assert calls[0]["port"] == 5433
    assert isinstance(calls[0]["port"], int)


def test_main_app_and_pickem_store_resolve_same_settings(db_env, monkeypatch):
    config_module, app_module, pickem_store_module = load_runtime_modules()
    calls = []

    def fake_connect(**kwargs):
        calls.append(kwargs)
        return "fake-connection"

    monkeypatch.setattr(app_module.psycopg2, "connect", fake_connect)
    monkeypatch.setattr(pickem_store_module.psycopg2, "connect", fake_connect)

    app_conn = app_module.get_db_connection()
    pickem_conn = pickem_store_module.connect()

    assert app_conn == "fake-connection"
    assert pickem_conn == "fake-connection"
    assert calls[0] == config_module.Config.db_kwargs()
    assert calls[1] == config_module.Config.db_kwargs()
    assert calls[0] == calls[1]


def test_fi_db_values_do_not_redirect_active_pickem_store(db_env, monkeypatch):
    _, _, pickem_store_module = load_runtime_modules()
    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return "fake-connection"

    monkeypatch.setattr(pickem_store_module.psycopg2, "connect", fake_connect)
    pickem_store_module.connect()

    assert captured["host"] == "db.primary"
    assert captured["port"] == 5433
    assert captured["dbname"] == "fantasy_intelligence"
    assert captured["user"] == "fantasy"
    assert captured["password"] == "secret123"
    assert captured["host"] != os.getenv("FI_DB_HOST")
    assert captured["port"] != int(os.getenv("FI_DB_PORT"))


def test_missing_required_db_configuration_raises_controlled_error(monkeypatch):
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret")
    monkeypatch.setenv("ADMIN_TOKEN", "admin-token")
    monkeypatch.setenv("SLEEPER_LEAGUE_ID", "league-123")
    monkeypatch.setenv("SLEEPER_DRAFT_ID", "draft-123")
    for key in ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(RuntimeError, match="Missing required environment variable: DB_HOST"):
        import config as config_module


def test_psycopg_connect_is_not_called_with_real_db(monkeypatch, db_env):
    _, _, pickem_store_module = load_runtime_modules()
    seen = {}

    def fake_connect(**kwargs):
        seen.update(kwargs)
        return "fake-connection"

    monkeypatch.setattr(pickem_store_module.psycopg2, "connect", fake_connect)
    assert pickem_store_module.connect() == "fake-connection"
    assert seen == pickem_store_module.Config.db_kwargs()
    assert "password" in seen
    assert seen["password"] == "secret123"

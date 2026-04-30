import logging
from unittest.mock import patch

import pytest

import app.core.config as config_module


@pytest.fixture(autouse=True)
def _isolate_settings_cache():
    config_module.get_settings.cache_clear()
    yield
    config_module.get_settings.cache_clear()


def _build_settings(env_vars: dict[str, str]):
    with patch.dict("os.environ", env_vars, clear=False):
        return config_module.get_settings()


def test_production_default_password_fails():
    with pytest.raises(RuntimeError, match="OLD_USER_INITIAL_PASSWORD must be set"):
        _build_settings(
            {
                "APP_ENV": "production",
                "JWT_SECRET_KEY": "a" * 48,
                "OLD_USER_INITIAL_PASSWORD": "",
            }
        )


def test_production_placeholder_password_fails():
    with pytest.raises(RuntimeError, match="OLD_USER_INITIAL_PASSWORD must be set"):
        _build_settings(
            {
                "APP_ENV": "production",
                "JWT_SECRET_KEY": "a" * 48,
                "OLD_USER_INITIAL_PASSWORD": "dev-only-replace-this-with-a-strong-password",
            }
        )


def test_production_secure_password_passes():
    settings = _build_settings(
        {
            "APP_ENV": "production",
            "JWT_SECRET_KEY": "a" * 48,
            "OLD_USER_INITIAL_PASSWORD": "MyStrongPass123!@#",
        }
    )
    assert settings.app_env == "production"
    assert settings.old_user_initial_password == "MyStrongPass123!@#"


def test_test_env_default_password_warns(caplog):
    with caplog.at_level(logging.WARNING, logger="app.core.config"):
        settings = _build_settings(
            {
                "APP_ENV": "test",
                "JWT_SECRET_KEY": "",
                "OLD_USER_INITIAL_PASSWORD": "",
            }
        )
    assert settings.app_env == "test"
    assert "OLD_USER_INITIAL_PASSWORD is using an insecure default" in caplog.text
    assert "JWT_SECRET_KEY is using the default test value" in caplog.text


def test_production_default_jwt_secret_fails():
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY must be set"):
        _build_settings(
            {
                "APP_ENV": "production",
                "JWT_SECRET_KEY": "change-me-in-production",
                "OLD_USER_INITIAL_PASSWORD": "MyStrongPass123!@#",
            }
        )

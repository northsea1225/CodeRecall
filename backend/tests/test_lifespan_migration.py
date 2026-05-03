from __future__ import annotations

import logging
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command as alembic_command

from app.core.config import settings
from app.db import init_db


def _build_url(db_path: Path) -> str:
    return f"sqlite:///{db_path}"


def _alembic_version(database_url: str) -> str | None:
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as conn:
            if not engine.dialect.has_table(conn, "alembic_version"):
                return None
            row = conn.execute(sa.text("SELECT version_num FROM alembic_version")).fetchone()
            return row[0] if row else None
    finally:
        engine.dispose()


def _has_table(database_url: str, table: str) -> bool:
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as conn:
            return engine.dialect.has_table(conn, table)
    finally:
        engine.dispose()


@pytest.fixture
def tmp_sqlite_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    # alembic env.py overrides sqlalchemy.url with settings.database_url at run
    # time, so route both Alembic and our helper functions through settings.
    url = _build_url(tmp_path / "test.db")
    monkeypatch.setattr(settings, "database_url", url)
    return url


def test_empty_db_with_successful_migrations_upgrades_to_head(tmp_sqlite_url: str) -> None:
    init_db.initialize_database(tmp_sqlite_url)

    assert _alembic_version(tmp_sqlite_url) == "0011"
    assert _has_table(tmp_sqlite_url, "mistakes")
    assert _has_table(tmp_sqlite_url, "users")


def test_empty_db_with_failing_migration_falls_back_to_create_all(
    tmp_sqlite_url: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(init_db.command, "upgrade", _boom)

    with caplog.at_level(logging.WARNING):
        init_db.initialize_database(tmp_sqlite_url)

    assert _has_table(tmp_sqlite_url, "mistakes")
    assert _has_table(tmp_sqlite_url, "users")
    assert any(
        rec.name == "app.db.init_db"
        and rec.levelno == logging.WARNING
        and "falling back to create_all" in rec.message
        for rec in caplog.records
    )


def test_existing_db_with_successful_migration_upgrades_to_head(tmp_sqlite_url: str) -> None:
    config = init_db._build_alembic_config(tmp_sqlite_url)
    alembic_command.upgrade(config, "0007")
    assert _alembic_version(tmp_sqlite_url) == "0007"

    init_db.initialize_database(tmp_sqlite_url)

    assert _alembic_version(tmp_sqlite_url) == "0011"


def test_existing_db_with_failing_migration_fails_fast(
    tmp_sqlite_url: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    config = init_db._build_alembic_config(tmp_sqlite_url)
    alembic_command.upgrade(config, "0007")
    assert _alembic_version(tmp_sqlite_url) == "0007"

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(init_db.command, "upgrade", _boom)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="boom"):
            init_db.initialize_database(tmp_sqlite_url)

    assert _alembic_version(tmp_sqlite_url) == "0007"
    assert any(
        rec.name == "app.db.init_db"
        and rec.levelno == logging.ERROR
        and "refusing to fall back" in rec.message
        for rec in caplog.records
    )

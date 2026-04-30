from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from alembic import command as alembic_command
from sqlalchemy import create_engine

from app.core.config import settings
from app.core.limiter import limiter
from app.db.init_db import _build_alembic_config
from app.db.session import _connect_args


@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    """Default off: rate limiting must not interfere with existing test suite.

    The single rate-limit test opts back in via the ``rate_limiter_enabled`` fixture.
    """
    previous = limiter.enabled
    limiter.enabled = False
    limiter.reset()
    try:
        yield
    finally:
        limiter.reset()
        limiter.enabled = previous


@pytest.fixture
def rate_limiter_enabled():
    """Opt-in fixture for tests that need real rate-limit enforcement."""
    previous = limiter.enabled
    limiter.enabled = True
    limiter.reset()
    try:
        yield limiter
    finally:
        limiter.reset()
        limiter.enabled = previous


@pytest.fixture
def alembic_head_engine(monkeypatch: pytest.MonkeyPatch):
    """SQLite engine built via real ``alembic upgrade head`` (not create_all).

    Used to validate that production-grade migration scripts (not
    ``Base.metadata`` snapshots) produce a schema the application correctly
    operates on. About 200-500 ms per use, so reserve for migration-sensitive
    regression tests.
    """
    tmpdir = tempfile.mkdtemp(prefix="coderecall-alembic-")
    db_path = Path(tmpdir) / "test_alembic.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setattr(settings, "database_url", url)
    alembic_command.upgrade(_build_alembic_config(url), "head")
    engine = create_engine(url, connect_args=_connect_args(url))
    try:
        yield engine
    finally:
        engine.dispose()
        try:
            db_path.unlink(missing_ok=True)
            os.rmdir(tmpdir)
        except OSError:
            pass

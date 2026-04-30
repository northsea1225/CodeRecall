from __future__ import annotations

from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app import models  # noqa: F401 - register table metadata


@pytest.fixture
def client(rate_limiter_enabled):
    tempdir = tempfile.TemporaryDirectory()
    database_url = f"sqlite:///{Path(tempdir.name) / 'rate_limit.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    tempdir.cleanup()


def test_login_route_rate_limits_after_threshold(client: TestClient) -> None:
    payload = {"username": "ratelimituser", "password": "doesnotmatter1"}
    accepted = 0
    saw_429 = False

    for _ in range(15):
        response = client.post(
            "/api/v1/auth/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code == 429:
            saw_429 = True
            body = response.json()
            assert body["code"] == "rate_limit_exceeded"
            break
        accepted += 1

    assert saw_429, "Expected /auth/token to return 429 within 15 attempts"
    assert accepted <= 10, f"Limit should kick in at 10/minute, got {accepted} accepted"


def test_register_route_rate_limits_after_threshold(client: TestClient) -> None:
    saw_429 = False
    accepted = 0

    for i in range(8):
        response = client.post(
            "/api/v1/auth/register",
            json={"username": f"ratelimit_reg_{i}", "password": "validpass123"},
        )
        if response.status_code == 429:
            saw_429 = True
            body = response.json()
            assert body["code"] == "rate_limit_exceeded"
            break
        accepted += 1

    assert saw_429, "Expected /auth/register to return 429 within 8 attempts"
    assert accepted <= 3, f"Register limit should kick in at 3/hour, got {accepted} accepted"


def test_disabled_limiter_does_not_block(client: TestClient) -> None:
    from app.core.limiter import limiter

    limiter.enabled = False
    payload = {"username": "passthrough", "password": "doesnotmatter1"}

    statuses = []
    for _ in range(15):
        response = client.post(
            "/api/v1/auth/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        statuses.append(response.status_code)

    assert 429 not in statuses, "When the limiter is disabled, no request should be rate limited"

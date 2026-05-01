"""I-004 phase 4: regression tests for Cache-Control headers on the GET routes
that pair with the SW NetworkFirst rules in frontend/vite.config.ts.

Mistakes list/detail get max-age=300 (5 min) to match the SW api-mistakes
window. Categories/tags get max-age=1800 (30 min) to match api-taxonomy.
All use 'private' so shared proxies / CDNs cannot leak data across users.
"""

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
from app import models  # noqa: F401 - import models so Base metadata is populated


@pytest.fixture(scope="module")
def db_engine():
    tempdir = tempfile.TemporaryDirectory()
    database_url = f"sqlite:///{Path(tempdir.name) / 'test_cache_control.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    tempdir.cleanup()


@pytest.fixture()
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _register_and_login(client: TestClient, username: str, password: str = "testpass123") -> dict[str, str]:
    register_resp = client.post(
        "/api/v1/auth/register", json={"username": username, "password": password}
    )
    assert register_resp.status_code == 200, register_resp.text

    token_resp = client.post(
        "/api/v1/auth/token", data={"username": username, "password": password}
    )
    assert token_resp.status_code == 200, token_resp.text
    token = token_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_mistakes_list_has_cache_control(client: TestClient) -> None:
    """GET /api/v1/mistakes list response must carry private 5-minute cache."""
    headers = _register_and_login(client, "cache_user_mistakes")
    r = client.get("/api/v1/mistakes", headers=headers)
    assert r.status_code == 200, r.text
    assert r.headers.get("cache-control") == "private, max-age=300"


def test_get_categories_list_has_long_cache_control(client: TestClient) -> None:
    """GET /api/v1/categories list response must carry private 30-minute cache."""
    headers = _register_and_login(client, "cache_user_categories")
    r = client.get("/api/v1/categories", headers=headers)
    assert r.status_code == 200, r.text
    assert r.headers.get("cache-control") == "private, max-age=1800"

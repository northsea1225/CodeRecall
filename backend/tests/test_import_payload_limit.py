from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401 - register table metadata
from app.db.base import Base
from app.db.session import get_db
from app.main import BodySizeLimitMiddleware, app


@pytest.fixture
def client():
    tempdir = tempfile.TemporaryDirectory()
    database_url = f"sqlite:///{Path(tempdir.name) / 'payload_limit.db'}"
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


def _register_and_login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_oversized_body_returns_413(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(BodySizeLimitMiddleware, "MAX_BYTES", 256)
    big_blob = "x" * 1024  # 1 KB body, well above the 256 B cap

    response = client.post(
        "/api/v1/auth/register",
        content=big_blob,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413, response.text
    body = response.json()
    assert body["code"] == "payload_too_large"
    assert body["detail"]["max_bytes"] == 256


def test_oversized_body_emits_cors_headers_for_allowed_origin(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(BodySizeLimitMiddleware, "MAX_BYTES", 64)

    response = client.post(
        "/api/v1/auth/register",
        content="x" * 256,
        headers={
            "content-type": "application/json",
            "origin": "http://localhost:5173",
        },
    )

    assert response.status_code == 413
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_too_many_mistakes_rejected_by_pydantic(client: TestClient) -> None:
    token = _register_and_login(client, "payload_user", "ValidPass123!")

    one_mistake = {
        "legacy_id": 1,
        "title": "x",
        "stem_markdown": "x",
        "wrong_answer_markdown": "x",
        "correct_answer_markdown": "x",
        "error_reason_markdown": "x",
        "language": "python",
        "difficulty": 3,
        "source": "",
        "status": "new",
        "category_name": "default",
        "tag_names": [],
        "ease_factor": 2.5,
        "interval_days": 0,
        "repetition": 0,
        "is_archived": False,
        "created_at": "2026-04-30T00:00:00",
        "updated_at": "2026-04-30T00:00:00",
    }
    payload = {
        "format": "coderecall",
        "schema_version": 3,
        "mistakes": [one_mistake] * 10001,
    }

    response = client.post(
        "/api/v1/import/v3",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "validation_error"


def test_request_within_limits_passes(client: TestClient) -> None:
    token = _register_and_login(client, "payload_user2", "ValidPass123!")

    payload = {
        "format": "coderecall",
        "schema_version": 3,
        "categories": [],
        "tags": [],
        "mistakes": [],
        "review_sessions": [],
        "review_session_items": [],
        "review_logs": [],
    }

    response = client.post(
        "/api/v1/import/v3",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text

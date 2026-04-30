"""Cross-user data isolation regression tests for Phase B."""

from __future__ import annotations

from datetime import datetime, timezone
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
    database_url = f"sqlite:///{Path(tempdir.name) / 'test_isolation.db'}"
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
    register_resp = client.post("/api/v1/auth/register", json={"username": username, "password": password})
    assert register_resp.status_code == 200, register_resp.text

    token_resp = client.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert token_resp.status_code == 200, token_resp.text
    token = token_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_category(client: TestClient, headers: dict[str, str], name: str = "Test Cat") -> int:
    response = client.post("/api/v1/categories", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _create_mistake(
    client: TestClient,
    headers: dict[str, str],
    category_id: int,
    title: str = "Test Mistake",
) -> int:
    response = client.post(
        "/api/v1/mistakes",
        json={
            "title": title,
            "category_id": category_id,
            "stem_markdown": "problem statement",
            "wrong_answer_markdown": "wrong code",
            "correct_answer_markdown": "correct code",
            "error_reason_markdown": "missed an edge case",
            "language": "python",
            "difficulty": 2,
            "source": "unit-test",
            "tags": ["isolation"],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


class TestMistakeCRUDIsolation:
    def test_user_b_cannot_see_user_a_mistakes(self, client: TestClient) -> None:
        headers_a = _register_and_login(client, "user_a_crud")
        headers_b = _register_and_login(client, "user_b_crud")
        category_id = _create_category(client, headers_a)
        _create_mistake(client, headers_a, category_id)

        response = client.get("/api/v1/mistakes", headers=headers_b)

        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_user_b_cannot_access_update_or_delete_user_a_mistake(self, client: TestClient) -> None:
        headers_a = _register_and_login(client, "user_a_byid")
        headers_b = _register_and_login(client, "user_b_byid")
        category_id = _create_category(client, headers_a)
        mistake_id = _create_mistake(client, headers_a, category_id)

        get_response = client.get(f"/api/v1/mistakes/{mistake_id}", headers=headers_b)
        patch_response = client.patch(
            f"/api/v1/mistakes/{mistake_id}",
            json={"title": "stolen update"},
            headers=headers_b,
        )
        delete_response = client.delete(f"/api/v1/mistakes/{mistake_id}", headers=headers_b)
        owner_response = client.get(f"/api/v1/mistakes/{mistake_id}", headers=headers_a)

        assert get_response.status_code == 404
        assert patch_response.status_code == 404
        assert delete_response.status_code == 404
        assert owner_response.status_code == 200
        assert owner_response.json()["title"] == "Test Mistake"

    def test_user_b_cannot_create_mistake_with_user_a_category(self, client: TestClient) -> None:
        headers_a = _register_and_login(client, "user_a_cross_category")
        headers_b = _register_and_login(client, "user_b_cross_category")
        category_id = _create_category(client, headers_a)

        response = client.post(
            "/api/v1/mistakes",
            json={
                "title": "Cross category",
                "category_id": category_id,
                "stem_markdown": "problem statement",
                "wrong_answer_markdown": "wrong code",
                "correct_answer_markdown": "correct code",
                "error_reason_markdown": "missed an edge case",
                "language": "python",
                "difficulty": 2,
            },
            headers=headers_b,
        )

        assert response.status_code == 404


class TestCategoryIsolation:
    def test_same_name_categories_for_different_users(self, client: TestClient) -> None:
        headers_a = _register_and_login(client, "user_a_cat")
        headers_b = _register_and_login(client, "user_b_cat")

        response_a = client.post("/api/v1/categories", json={"name": "DP"}, headers=headers_a)
        response_b = client.post("/api/v1/categories", json={"name": "DP"}, headers=headers_b)

        assert response_a.status_code == 201
        assert response_b.status_code == 201
        assert response_a.json()["id"] != response_b.json()["id"]

    def test_user_b_cannot_access_or_modify_user_a_category(self, client: TestClient) -> None:
        headers_a = _register_and_login(client, "user_a_cat2")
        headers_b = _register_and_login(client, "user_b_cat2")
        category_id = _create_category(client, headers_a, "Private Cat")

        get_response = client.get(f"/api/v1/categories/{category_id}", headers=headers_b)
        patch_response = client.patch(
            f"/api/v1/categories/{category_id}",
            json={"name": "renamed"},
            headers=headers_b,
        )
        delete_response = client.delete(f"/api/v1/categories/{category_id}", headers=headers_b)

        assert get_response.status_code == 404
        assert patch_response.status_code == 404
        assert delete_response.status_code == 404


class TestReviewAndStatsIsolation:
    def test_user_b_review_queue_and_stats_ignore_user_a_data(self, client: TestClient) -> None:
        headers_a = _register_and_login(client, "user_a_review_stats")
        headers_b = _register_and_login(client, "user_b_review_stats")
        category_id = _create_category(client, headers_a)
        mistake_id = _create_mistake(client, headers_a, category_id)

        stats_response = client.get("/api/v1/stats/overview", headers=headers_b)
        session_response = client.post("/api/v1/review/sessions", json={"strategy": "random", "limit": 10}, headers=headers_b)
        reveal_response = client.get(f"/api/v1/review/items/{mistake_id}/reveal", headers=headers_b)

        assert stats_response.status_code == 200
        assert stats_response.json()["total_mistakes"] == 0
        assert session_response.status_code == 201
        assert session_response.json()["total_count"] == 0
        assert session_response.json()["next_item"] is None
        assert reveal_response.status_code == 404


class TestV3ImportIsolation:
    def test_same_payload_can_be_imported_by_two_users(self, client: TestClient) -> None:
        headers_a = _register_and_login(client, "user_a_v3")
        headers_b = _register_and_login(client, "user_b_v3")
        timestamp = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc).isoformat()
        payload = {
            "format": "coderecall",
            "schema_version": 3,
            "exported_at": timestamp,
            "categories": [{"name": "Arrays", "description": ""}],
            "tags": [{"name": "easy"}],
            "mistakes": [
                {
                    "uuid": "550e8400-e29b-41d4-a716-446655440000",
                    "legacy_id": 1,
                    "title": "Two Sum",
                    "stem_markdown": "find two numbers",
                    "wrong_answer_markdown": "nested loop bug",
                    "correct_answer_markdown": "use hashmap",
                    "error_reason_markdown": "off by one",
                    "language": "python",
                    "difficulty": 2,
                    "source": "leetcode",
                    "status": "new",
                    "category_name": "Arrays",
                    "tag_names": ["easy"],
                    "ease_factor": 2.5,
                    "interval_days": 0,
                    "repetition": 0,
                    "next_review_at": None,
                    "is_archived": False,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            ],
            "review_sessions": [],
            "review_session_items": [],
            "review_logs": [],
        }

        response_a = client.post("/api/v1/import/v3", json=payload, headers=headers_a)
        response_b = client.post("/api/v1/import/v3", json=payload, headers=headers_b)

        assert response_a.status_code == 200, response_a.text
        assert response_b.status_code == 200, response_b.text
        assert response_a.json()["imported"]["mistakes"] == 1
        assert response_b.json()["imported"]["mistakes"] == 1

    def test_export_v3_only_returns_own_data(self, client: TestClient) -> None:
        headers_a = _register_and_login(client, "user_a_exp")
        headers_b = _register_and_login(client, "user_b_exp")
        category_id = _create_category(client, headers_a, "Export Cat")
        _create_mistake(client, headers_a, category_id, "Only A's mistake")

        response_a = client.get("/api/v1/export/v3", headers=headers_a)
        response_b = client.get("/api/v1/export/v3", headers=headers_b)

        assert response_a.status_code == 200
        assert response_b.status_code == 200
        assert [mistake["title"] for mistake in response_a.json()["mistakes"]] == ["Only A's mistake"]
        assert response_b.json()["mistakes"] == []

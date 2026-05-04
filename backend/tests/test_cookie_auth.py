from __future__ import annotations

from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import models  # noqa: F401 - register table metadata
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Category, TokenJtiBlacklist, User
from app.services.auth_service import create_user, decode_access_token
from app.services.csrf_service import CSRF_COOKIE, CSRF_HEADER


PASSWORD = "Passw0rd!12345"


@pytest.fixture(scope="module")
def db_engine():
    tempdir = tempfile.TemporaryDirectory()
    database_url = f"sqlite:///{Path(tempdir.name) / 'test_cookie_auth.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        tempdir.cleanup()


@pytest.fixture()
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def _login(client: TestClient, db_session: Session, username: str) -> tuple[object, User]:
    user = create_user(db_session, username, PASSWORD)
    response = client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": PASSWORD},
    )
    return response, user


def _set_cookie_headers(response: object) -> list[str]:
    return response.headers.get_list("set-cookie")


def _make_category(db_session: Session, user_id: int, name: str = "Cookie Auth") -> Category:
    category = Category(user_id=user_id, name=name, description="")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


def _mistake_payload(category_id: int) -> dict[str, object]:
    return {
        "title": "cookie auth csrf mistake",
        "stem_markdown": "题干",
        "wrong_answer_markdown": "错误答案",
        "correct_answer_markdown": "正确答案",
        "error_reason_markdown": "错因",
        "language": "python",
        "difficulty": 2,
        "source": "LeetCode",
        "status": "new",
        "category_id": category_id,
        "tags": ["csrf"],
    }


def test_login_sets_cookies_and_returns_csrf_header(
    client: TestClient,
    db_session: Session,
) -> None:
    response, _ = _login(client, db_session, "cookie_login")

    set_cookies = _set_cookie_headers(response)
    csrf_cookie = response.cookies.get(CSRF_COOKIE)
    assert response.status_code == 200, response.text
    assert any(line.startswith("access_token=") and "httponly" in line.lower() for line in set_cookies)
    assert any(line.startswith(f"{CSRF_COOKIE}=") and "httponly" not in line.lower() for line in set_cookies)
    assert response.headers[CSRF_HEADER] == csrf_cookie


def test_csrf_blocks_mutation_without_header(
    client: TestClient,
    db_session: Session,
) -> None:
    _login(client, db_session, "csrf_block_first")
    client.cookies.clear()
    _, user = _login(client, db_session, "csrf_block")
    category = _make_category(db_session, user.id)

    response = client.post("/api/v1/mistakes", json=_mistake_payload(category.id))

    assert response.status_code == 403
    assert response.json()["code"] == "csrf_invalid"


def test_csrf_passes_when_header_matches(
    client: TestClient,
    db_session: Session,
) -> None:
    _, user = _login(client, db_session, "csrf_pass")
    category = _make_category(db_session, user.id)
    csrf = client.cookies.get(CSRF_COOKIE)

    response = client.post(
        "/api/v1/mistakes",
        json=_mistake_payload(category.id),
        headers={CSRF_HEADER: csrf},
    )

    assert response.status_code == 201, response.text


def test_logout_clears_cookies_and_blacklists_jti(
    client: TestClient,
    db_session: Session,
) -> None:
    login_response, _ = _login(client, db_session, "cookie_logout")
    payload = decode_access_token(login_response.json()["access_token"])

    response = client.post("/api/v1/auth/logout")

    set_cookies = _set_cookie_headers(response)
    assert response.status_code == 200, response.text
    assert any(line.startswith("access_token=") and "Max-Age=0" in line for line in set_cookies)
    assert any(line.startswith(f"{CSRF_COOKIE}=") and "Max-Age=0" in line for line in set_cookies)
    assert db_session.get(TokenJtiBlacklist, payload["jti"]) is not None


def test_bearer_fallback_within_compat_window(
    client: TestClient,
    db_session: Session,
) -> None:
    login_response, _ = _login(client, db_session, "bearer_compat")
    token = login_response.json()["access_token"]
    client.cookies.clear()

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200, response.text


def test_me_returns_token_exp_at_and_no_store_cache(
    client: TestClient,
    db_session: Session,
) -> None:
    _login(client, db_session, "cookie_me")

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200, response.text
    assert response.json()["token_exp_at"] is not None
    assert response.headers["Cache-Control"] == "no-store"

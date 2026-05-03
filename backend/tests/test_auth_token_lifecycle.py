from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app import models  # noqa: F401 - register table metadata
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import TokenJtiBlacklist, User
from app.services.auth_service import create_access_token, decode_access_token, token_exp_datetime
from app.services.token_blacklist_service import cleanup_expired_blacklisted_jtis


@pytest.fixture(scope="module")
def db_engine():
    tempdir = tempfile.TemporaryDirectory()
    database_url = f"sqlite:///{Path(tempdir.name) / 'test_auth_token_lifecycle.db'}"
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


def _make_user(db_session: Session, username: str = "tokenlife") -> User:
    user = User(username=username, display_name=username, password_hash="unused")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _manual_access_token(
    *,
    user_id: int,
    username: str,
    exp: datetime,
    jti: str | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": jti or uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def test_refresh_success_issues_new_jti(client: TestClient, db_session: Session) -> None:
    user = _make_user(db_session, "refresh_success")
    old_token = create_access_token(user.id, user.username)
    old_payload = decode_access_token(old_token)

    response = client.post("/api/v1/auth/refresh", headers=_auth_header(old_token))

    assert response.status_code == 200, response.text
    new_token = response.json()["access_token"]
    new_payload = decode_access_token(new_token)
    assert new_token != old_token
    assert new_payload["jti"] != old_payload["jti"]
    assert new_payload["sub"] == old_payload["sub"]
    expected_exp = datetime.now(timezone.utc) + timedelta(minutes=120)
    actual_exp = token_exp_datetime(new_payload)
    assert abs((actual_exp - expected_exp).total_seconds()) <= 60


def test_refresh_rejects_expired_token_outside_grace(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _make_user(db_session, "refresh_expired")
    token = _manual_access_token(
        user_id=user.id,
        username=user.username,
        exp=datetime.now(timezone.utc) - timedelta(seconds=200),
    )

    response = client.post("/api/v1/auth/refresh", headers=_auth_header(token))

    assert response.status_code == 401
    assert response.json()["code"] == "token_expired"


def test_refresh_accepts_token_within_grace_seconds(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _make_user(db_session, "refresh_grace")
    token = _manual_access_token(
        user_id=user.id,
        username=user.username,
        exp=datetime.now(timezone.utc) - timedelta(seconds=60),
    )

    response = client.post("/api/v1/auth/refresh", headers=_auth_header(token))

    assert response.status_code == 200, response.text
    assert response.json()["access_token"] != token


def test_get_current_user_rejects_blacklisted_jti(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _make_user(db_session, "blacklisted_me")
    token = create_access_token(user.id, user.username)
    payload = decode_access_token(token)
    db_session.add(
        TokenJtiBlacklist(
            jti=payload["jti"],
            user_id=user.id,
            exp_at=token_exp_datetime(payload),
        )
    )
    db_session.commit()

    response = client.get("/api/v1/auth/me", headers=_auth_header(token))

    assert response.status_code == 401
    assert response.json()["code"] == "token_revoked"


def test_logout_writes_blacklist_row(client: TestClient, db_session: Session) -> None:
    user = _make_user(db_session, "logout_writes")
    token = create_access_token(user.id, user.username)
    payload = decode_access_token(token)

    response = client.post("/api/v1/auth/logout", headers=_auth_header(token))

    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True}
    row = db_session.get(TokenJtiBlacklist, payload["jti"])
    assert row is not None
    assert row.user_id == user.id
    assert _as_utc(row.exp_at) == token_exp_datetime(payload)


def test_old_token_invalid_after_logout(client: TestClient, db_session: Session) -> None:
    user = _make_user(db_session, "logout_invalidates")
    token = create_access_token(user.id, user.username)

    logout_response = client.post("/api/v1/auth/logout", headers=_auth_header(token))
    assert logout_response.status_code == 200, logout_response.text
    response = client.get("/api/v1/auth/me", headers=_auth_header(token))

    assert response.status_code == 401
    assert response.json()["code"] == "token_revoked"


def test_cleanup_expired_blacklisted_jtis_deletes_only_expired_rows(db_session: Session) -> None:
    now = datetime.now(timezone.utc)
    user = _make_user(db_session, "cleanup_user")
    expired_jti = uuid.uuid4().hex
    active_jti = uuid.uuid4().hex
    db_session.add_all(
        [
            TokenJtiBlacklist(jti=expired_jti, user_id=user.id, exp_at=now - timedelta(seconds=1)),
            TokenJtiBlacklist(jti=active_jti, user_id=user.id, exp_at=now + timedelta(minutes=5)),
        ]
    )
    db_session.commit()

    deleted = cleanup_expired_blacklisted_jtis(db_session, now=now)

    assert deleted == 1
    remaining_jtis = set(db_session.scalars(select(TokenJtiBlacklist.jti)))
    assert expired_jti not in remaining_jtis
    assert active_jti in remaining_jtis

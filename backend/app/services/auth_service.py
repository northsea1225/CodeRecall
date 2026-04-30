from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import re
from typing import Optional

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import raise_api_error
from app.core.config import settings
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 100
USERNAME_PATTERN_TEXT = r"^[A-Za-z0-9_]+$"
_USERNAME_RE = re.compile(USERNAME_PATTERN_TEXT)

PASSWORD_MIN_LENGTH = 8
BCRYPT_PASSWORD_MAX_BYTES = 72


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def create_access_token(user_id: int, username: str) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "username": username,
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("Invalid token type.")
    return payload


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    normalized = username.strip()
    if not normalized:
        return None
    return db.scalar(select(User).where(User.username == normalized))


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_user(db: Session, username: str, password: str) -> User:
    normalized = username.strip()
    if not normalized:
        raise_api_error(422, "invalid_username", "Username cannot be blank.", {"field": "username"})
    if len(normalized) < USERNAME_MIN_LENGTH:
        raise_api_error(
            422,
            "invalid_username",
            f"Username must be at least {USERNAME_MIN_LENGTH} characters.",
            {"field": "username", "min_length": USERNAME_MIN_LENGTH},
        )
    if len(normalized) > USERNAME_MAX_LENGTH:
        raise_api_error(
            422,
            "invalid_username",
            f"Username must be at most {USERNAME_MAX_LENGTH} characters.",
            {"field": "username", "max_length": USERNAME_MAX_LENGTH},
        )
    if _USERNAME_RE.fullmatch(normalized) is None:
        raise_api_error(
            422,
            "invalid_username",
            "Username may only contain letters, numbers, and underscores.",
            {"field": "username", "pattern": USERNAME_PATTERN_TEXT},
        )
    if not password:
        raise_api_error(422, "invalid_password", "Password cannot be blank.", {"field": "password"})
    if len(password) < PASSWORD_MIN_LENGTH:
        raise_api_error(
            422,
            "invalid_password",
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters.",
            {"field": "password", "min_length": PASSWORD_MIN_LENGTH},
        )
    if len(password.encode("utf-8")) > BCRYPT_PASSWORD_MAX_BYTES:
        raise_api_error(
            422,
            "invalid_password",
            f"Password must be at most {BCRYPT_PASSWORD_MAX_BYTES} bytes.",
            {"field": "password", "max_bytes": BCRYPT_PASSWORD_MAX_BYTES},
        )

    user = User(
        username=normalized,
        display_name=normalized,
        password_hash=hash_password(password),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise_api_error(409, "username_exists", "Username already exists.", {"username": normalized})
    db.refresh(user)
    return user


def ensure_default_old_user(db: Session) -> User:
    user = get_user_by_username(db, "old_user")
    if user is not None:
        _maybe_rotate_old_user_password(db, user)
        return user

    user = User(
        username="old_user",
        display_name="old user",
        password_hash=hash_password(settings.old_user_initial_password),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


_LEGACY_OLD_USER_PASSWORDS = ("coderecall", "change_me_immediately")


def _maybe_rotate_old_user_password(db: Session, user: User) -> None:
    if settings.app_env.strip().lower() == "test":
        return
    if any(verify_password(pwd, user.password_hash) for pwd in _LEGACY_OLD_USER_PASSWORDS):
        user.password_hash = hash_password(settings.old_user_initial_password)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("old_user password hash rotated to new configured value.")

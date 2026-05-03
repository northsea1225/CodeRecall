from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, oauth2_scheme
from app.api.errors import raise_api_error
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models import User
from app.services.auth_service import (
    BCRYPT_PASSWORD_MAX_BYTES,
    PASSWORD_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    USERNAME_PATTERN_TEXT,
    authenticate_user,
    create_access_token,
    create_user,
    decode_access_token,
    token_exp_datetime,
)
from app.services.token_blacklist_service import (
    is_jti_blacklisted,
    maybe_cleanup_blacklist,
    revoke_jti,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str = Field(
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
        pattern=USERNAME_PATTERN_TEXT,
    )
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=BCRYPT_PASSWORD_MAX_BYTES)


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    user_id: int


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    is_active: bool


class LogoutOut(BaseModel):
    ok: bool = True


def _auth_response(user: User) -> AuthOut:
    return AuthOut(
        access_token=create_access_token(user.id, user.username),
        username=user.username,
        user_id=user.id,
    )


@router.post("/token", response_model=AuthOut)
@limiter.limit("10/minute;100/hour")
def login_route(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> AuthOut:
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise_api_error(401, "invalid_credentials", "Username or password is incorrect.", {})
    return _auth_response(user)


@router.post("/register", response_model=AuthOut)
@limiter.limit("3/hour;10/day")
def register_route(request: Request, payload: RegisterIn, db: Session = Depends(get_db)) -> AuthOut:
    user = create_user(db, payload.username, payload.password)
    return _auth_response(user)


@router.post("/refresh", response_model=AuthOut)
@limiter.limit("120/minute;1000/hour")
def refresh_route(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthOut:
    try:
        payload = decode_access_token(
            token,
            leeway_seconds=settings.access_token_refresh_grace_seconds,
        )
        user_id = int(payload["sub"])
        jti = payload["jti"]
    except jwt.ExpiredSignatureError:
        raise_api_error(401, "token_expired", "Token has expired.", {})
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise_api_error(401, "invalid_token", "Invalid token.", {})

    if is_jti_blacklisted(db, jti):
        raise_api_error(401, "token_revoked", "Token has been revoked.", {})

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise_api_error(401, "unauthorized", "Invalid credentials.", {})

    return _auth_response(user)


@router.post("/logout", response_model=LogoutOut)
def logout_route(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> LogoutOut:
    try:
        payload = decode_access_token(
            token,
            leeway_seconds=settings.access_token_refresh_grace_seconds,
        )
        revoke_jti(
            db,
            jti=payload["jti"],
            user_id=int(payload["sub"]),
            exp_at=token_exp_datetime(payload),
        )
        maybe_cleanup_blacklist(
            db,
            interval_seconds=settings.token_blacklist_cleanup_interval_seconds,
        )
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise_api_error(401, "invalid_token", "Invalid token.", {})
    return LogoutOut()


@router.get("/me", response_model=UserOut)
def me_route(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
    )

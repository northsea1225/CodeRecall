from __future__ import annotations

from datetime import datetime
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import cookie_scheme, get_current_user, oauth2_scheme
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
from app.services.csrf_service import (
    CSRF_COOKIE,
    CSRF_HEADER,
    generate_csrf_token,
    verify_csrf_for_mutation,
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
    token_exp_at: datetime


class UserMeOut(BaseModel):
    id: int
    username: str
    display_name: str
    is_active: bool
    token_exp_at: Optional[datetime] = None


class LogoutOut(BaseModel):
    ok: bool = True


def _set_auth_cookies(response: Response, user: User) -> tuple[str, datetime]:
    csrf = generate_csrf_token()
    token = create_access_token(user.id, user.username, csrf=csrf)
    payload = decode_access_token(token)
    exp_at = token_exp_datetime(payload)
    max_age = settings.access_token_expire_minutes * 60
    cookie_kwargs = dict(
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=max_age,
        path="/api/v1",
    )
    response.set_cookie(key="access_token", value=token, httponly=True, **cookie_kwargs)
    response.set_cookie(key=CSRF_COOKIE, value=csrf, httponly=False, **cookie_kwargs)
    response.headers[CSRF_HEADER] = csrf
    return token, exp_at


def _auth_response(response: Response, user: User) -> AuthOut:
    token, exp_at = _set_auth_cookies(response, user)
    return AuthOut(
        access_token=token,
        username=user.username,
        user_id=user.id,
        token_exp_at=exp_at,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/api/v1")
    response.delete_cookie(CSRF_COOKIE, path="/api/v1")


@router.post("/token", response_model=AuthOut)
@limiter.limit("10/minute;100/hour")
def login_route(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> AuthOut:
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise_api_error(401, "invalid_credentials", "Username or password is incorrect.", {})
    return _auth_response(response, user)


@router.post("/register", response_model=AuthOut)
@limiter.limit("3/hour;10/day")
def register_route(
    request: Request,
    response: Response,
    payload: RegisterIn,
    db: Session = Depends(get_db),
) -> AuthOut:
    user = create_user(db, payload.username, payload.password)
    return _auth_response(response, user)


@router.post("/refresh", response_model=AuthOut)
@limiter.limit("120/minute;1000/hour")
def refresh_route(
    request: Request,
    response: Response,
    cookie_token: Optional[str] = Depends(cookie_scheme),
    bearer_token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthOut:
    token = cookie_token
    via = "cookie"
    if bearer_token is not None and settings.bearer_compat_active:
        token = bearer_token
        via = "bearer"
    if token is None:
        raise_api_error(401, "missing_token", "Authentication required.", {})

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

    if via == "cookie":
        jwt_csrf = payload.get("csrf", "")
        if not jwt_csrf:
            raise_api_error(401, "invalid_token", "Cookie token missing csrf claim.", {})
        verify_csrf_for_mutation(request, jwt_csrf)

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise_api_error(401, "unauthorized", "Invalid credentials.", {})

    return _auth_response(response, user)


@router.post("/logout", response_model=LogoutOut)
def logout_route(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LogoutOut:
    token = request.cookies.get("access_token")
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer ") and settings.bearer_compat_active:
        token = auth_header[7:]

    try:
        if token is not None:
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
        pass
    _clear_auth_cookies(response)
    return LogoutOut()


@router.get("/me", response_model=UserMeOut)
@limiter.limit("60/minute")
def me_route(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
) -> UserMeOut:
    response.headers["Cache-Control"] = "no-store"
    token_exp_at: Optional[datetime] = None
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        payload = decode_access_token(cookie_token)
        token_exp_at = token_exp_datetime(payload)
        csrf = payload.get("csrf", "")
        if csrf:
            response.headers[CSRF_HEADER] = csrf

    return UserMeOut(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
        token_exp_at=token_exp_at,
    )

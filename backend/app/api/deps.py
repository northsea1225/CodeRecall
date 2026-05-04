from __future__ import annotations

from typing import NoReturn

import jwt
from fastapi import Depends, Request, status
from fastapi.security import APIKeyCookie, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.api.errors import raise_api_error
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token
from app.services.csrf_service import verify_csrf_for_mutation
from app.services.token_blacklist_service import is_jti_blacklisted

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)
cookie_scheme = APIKeyCookie(name="access_token", auto_error=False)


def _auth_error(code: str, message: str) -> NoReturn:
    raise_api_error(status.HTTP_401_UNAUTHORIZED, code, message, {})


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    cookie_token: str | None = Depends(cookie_scheme),
    bearer_token: str | None = Depends(oauth2_scheme),
) -> User:
    token = cookie_token
    via = "cookie"
    if bearer_token is not None and settings.bearer_compat_active:
        token = bearer_token
        via = "bearer"
    if token is None:
        _auth_error("missing_token", "Authentication required.")

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
        jti = payload["jti"]
    except jwt.ExpiredSignatureError:
        _auth_error("token_expired", "Token has expired.")
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        _auth_error("invalid_token", "Invalid token.")

    if is_jti_blacklisted(db, jti):
        _auth_error("token_revoked", "Token has been revoked.")

    if via == "cookie":
        jwt_csrf = payload.get("csrf", "")
        if not jwt_csrf:
            _auth_error("invalid_token", "Cookie token missing csrf claim.")
        verify_csrf_for_mutation(request, jwt_csrf)

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        _auth_error("unauthorized", "Invalid credentials.")
    return user

from __future__ import annotations

from typing import NoReturn

import jwt
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.api.errors import raise_api_error
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token
from app.services.token_blacklist_service import is_jti_blacklisted

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def _auth_error(code: str, message: str) -> NoReturn:
    raise_api_error(status.HTTP_401_UNAUTHORIZED, code, message, {})


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
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

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        _auth_error("unauthorized", "Invalid credentials.")
    return user

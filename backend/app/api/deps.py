from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def _auth_error(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": message, "detail": {}},
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise _auth_error("token_expired", "Token has expired.")
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise _auth_error("invalid_token", "Invalid token.")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _auth_error("unauthorized", "Invalid credentials.")
    return user

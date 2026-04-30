from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.errors import raise_api_error
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


def _auth_response(user: User) -> AuthOut:
    return AuthOut(
        access_token=create_access_token(user.id, user.username),
        username=user.username,
        user_id=user.id,
    )


@router.post("/token", response_model=AuthOut)
def login_route(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> AuthOut:
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise_api_error(401, "invalid_credentials", "Username or password is incorrect.", {})
    return _auth_response(user)


@router.post("/register", response_model=AuthOut)
def register_route(payload: RegisterIn, db: Session = Depends(get_db)) -> AuthOut:
    user = create_user(db, payload.username, payload.password)
    return _auth_response(user)


@router.get("/me", response_model=UserOut)
def me_route(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
    )

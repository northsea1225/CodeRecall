from __future__ import annotations

import secrets

from fastapi import Request

from app.api.errors import raise_api_error

CSRF_HEADER = "X-CSRF-Token"
CSRF_COOKIE = "csrf_token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf_for_mutation(request: Request, jwt_csrf: str) -> None:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    header_csrf = request.headers.get(CSRF_HEADER)
    cookie_csrf = request.cookies.get(CSRF_COOKIE)
    if (
        not header_csrf
        or not cookie_csrf
        or header_csrf != cookie_csrf
        or header_csrf != jwt_csrf
    ):
        raise_api_error(403, "csrf_invalid", "CSRF token mismatch.", {})

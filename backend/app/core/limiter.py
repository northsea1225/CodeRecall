from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def _client_key(request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    return get_remote_address(request)


limiter = Limiter(
    key_func=_client_key,
    enabled=settings.rate_limit_enabled,
    default_limits=[],
    headers_enabled=False,
)

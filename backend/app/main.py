from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.errors import error_payload
from app.api.routes import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.db.init_db import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Always run migrations on startup. initialize_database() decides internally
    # whether to fall back to create_all (empty DB) or fail-fast (existing DB)
    # when Alembic upgrade fails — see backend/app/db/init_db.py.
    initialize_database()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-CSRF-Token"],
    # Expose ETag + Cache-Control to the SW / browser fetch layer so the PWA
    # (I-004) can read them. ETag generation is not yet wired (it would need a
    # FastAPI middleware), but exposing the header now means we don't have to
    # touch CORS again when ETag lands.
    expose_headers=["ETag", "Cache-Control", "X-CSRF-Token"],
    max_age=3600,
)


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject incoming bodies whose Content-Length exceeds the configured cap.

    Defends /import/v3 and any other JSON-heavy endpoint from OOM attacks
    where an attacker uploads a multi-GB payload. Content-Length is checked
    pre-routing so we never buffer the full body. Chunked transfer encoding
    (no Content-Length header) is not handled here; it remains rate-limited
    upstream and fenced by Pydantic max_length limits at parse time.
    """

    MAX_BYTES = 50 * 1024 * 1024

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None and cl.isdigit() and int(cl) > self.MAX_BYTES:
            origin = request.headers.get("origin")
            headers: dict[str, str] = {}
            if origin and origin in settings.cors_origins:
                headers["access-control-allow-origin"] = origin
                headers["access-control-allow-credentials"] = "true"
                headers["vary"] = "Origin"
            return JSONResponse(
                status_code=413,
                content=error_payload(
                    "payload_too_large",
                    f"Payload exceeds limit of {self.MAX_BYTES // (1024 * 1024)} MB.",
                    {"max_bytes": self.MAX_BYTES},
                ),
                headers=headers,
            )
        return await call_next(request)


app.add_middleware(BodySizeLimitMiddleware)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.exception_handler(RateLimitExceeded)
async def handle_rate_limit_exceeded(_, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content=error_payload(
            "rate_limit_exceeded",
            "Too many requests. Please slow down and try again later.",
            {"limit": str(exc.limit.limit) if getattr(exc, "limit", None) else None},
        ),
    )


@app.exception_handler(HTTPException)
async def handle_http_exception(_, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and {"code", "message", "detail"}.issubset(detail.keys()):
        payload = detail
    else:
        payload = error_payload("http_error", str(detail), {})
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def handle_validation_exception(_, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_payload(
            "validation_error",
            "Request validation failed.",
            exc.errors(),
        ),
    )


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env.value,
    }

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.errors import error_payload
from app.api.routes import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.db.init_db import initialize_database, should_initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    if should_initialize_database():
        initialize_database()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "environment": settings.app_env,
    }

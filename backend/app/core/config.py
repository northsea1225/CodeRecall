import logging
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

logger = logging.getLogger(__name__)
_bearer_compat_deadline_missing_warned = False

_DEFAULT_JWT_SECRET = "change-me-in-production"
_INSECURE_JWT_SECRETS = {
    _DEFAULT_JWT_SECRET,
    "dev-only-replace-this-with-a-generated-random-secret",
    "",
}
_INSECURE_OLD_USER_PASSWORDS = {
    "coderecall",
    "change_me_immediately",
    "dev-only-replace-this-with-a-strong-password",
    "",
}


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    app_name: str = Field(default="CodeRecall API", alias="APP_NAME")
    app_env: AppEnv = Field(default=AppEnv.DEVELOPMENT, alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")  # nosec B104 — dev default; production overrides via env or runs behind a reverse proxy (see SECURITY.md)
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    frontend_origin: str = Field(default="http://localhost:5173", alias="FRONTEND_ORIGIN")
    database_url: str = Field(default="sqlite:///./coderecall.db", alias="DATABASE_URL")
    enable_ai_analysis: bool = Field(default=False, alias="ENABLE_AI_ANALYSIS")
    llm_provider: str = Field(default="", alias="LLM_PROVIDER")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    llm_model_premium: str = Field(default="", alias="LLM_MODEL_PREMIUM")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_allowed_models: str = Field(default="", alias="LLM_ALLOWED_MODELS")
    llm_quick_model: str = Field(default="", alias="LLM_QUICK_MODEL")
    jwt_secret_key: str = Field(default=_DEFAULT_JWT_SECRET, alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=120, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    access_token_refresh_grace_seconds: int = Field(default=120, alias="ACCESS_TOKEN_REFRESH_GRACE_SECONDS")
    token_blacklist_cleanup_interval_seconds: int = Field(default=600, alias="TOKEN_BLACKLIST_CLEANUP_INTERVAL_SECONDS")
    bearer_compat_window_seconds: int = Field(default=86400, alias="BEARER_COMPAT_WINDOW_SECONDS")
    bearer_compat_deadline_iso: str = Field(default="", alias="BEARER_COMPAT_DEADLINE_ISO")
    cookie_secure_override: Optional[bool] = Field(default=None, alias="COOKIE_SECURE")
    old_user_initial_password: str = Field(default="", alias="OLD_USER_INITIAL_PASSWORD")
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        raw = self.frontend_origin
        origins = {o.strip() for o in raw.split(",") if o.strip()}
        expanded: set[str] = set()
        for origin in origins:
            expanded.add(origin)
            if "localhost" in origin:
                expanded.add(origin.replace("localhost", "127.0.0.1"))
        return sorted(expanded)

    @property
    def cookie_secure(self) -> bool:
        if self.cookie_secure_override is not None:
            return self.cookie_secure_override
        return self.app_env in (AppEnv.PRODUCTION, AppEnv.STAGING)

    @property
    def bearer_compat_active(self) -> bool:
        """Whether to accept Bearer tokens. False after the configured deadline."""
        global _bearer_compat_deadline_missing_warned
        if not self.bearer_compat_deadline_iso:
            if not _bearer_compat_deadline_missing_warned:
                logger.warning("BEARER_COMPAT_DEADLINE_ISO is unset; falling back to compat=on")
                _bearer_compat_deadline_missing_warned = True
            return True
        try:
            deadline = datetime.fromisoformat(self.bearer_compat_deadline_iso.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) < deadline
        except ValueError:
            logger.warning("Invalid BEARER_COMPAT_DEADLINE_ISO; falling back to compat=on")
            return True

    @property
    def sqlite_database_path(self) -> Optional[Path]:
        url = make_url(self.database_url)
        if url.get_backend_name() != "sqlite":
            return None

        database = url.database or ""
        if database in {":memory:", ""}:
            return None

        db_path = Path(database)
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
        return db_path.resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()

    if s.app_env == AppEnv.TEST:
        if s.jwt_secret_key.strip() in _INSECURE_JWT_SECRETS:
            logger.warning("JWT_SECRET_KEY is using the default test value.")
        if s.old_user_initial_password.strip() in _INSECURE_OLD_USER_PASSWORDS:
            logger.warning("OLD_USER_INITIAL_PASSWORD is using an insecure default.")
        return s

    if s.jwt_secret_key.strip() in _INSECURE_JWT_SECRETS:
        raise RuntimeError(
            "JWT_SECRET_KEY must be set to a non-default value. "
            "Only APP_ENV=test is exempt. "
            "Run: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )

    if s.old_user_initial_password.strip() in _INSECURE_OLD_USER_PASSWORDS:
        raise RuntimeError(
            "OLD_USER_INITIAL_PASSWORD must be set to a non-empty, non-default value.\n"
            "Quick fix:\n"
            "  export OLD_USER_INITIAL_PASSWORD=$(python -c \"import secrets; print(secrets.token_urlsafe(24))\")\n"
            "Only APP_ENV=test is exempt."
        )

    return s


settings = get_settings()

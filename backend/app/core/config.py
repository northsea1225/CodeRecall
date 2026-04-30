import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

logger = logging.getLogger(__name__)

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


class Settings(BaseSettings):
    app_name: str = Field(default="CodeRecall API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
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
    access_token_expire_minutes: int = Field(default=10080, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
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
        origins = {self.frontend_origin}
        if "localhost" in self.frontend_origin:
            origins.add(self.frontend_origin.replace("localhost", "127.0.0.1"))
        return sorted(origins)

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
    env = s.app_env.strip().lower()

    if env == "test":
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

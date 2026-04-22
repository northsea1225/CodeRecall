from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


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
    return Settings()


settings = get_settings()

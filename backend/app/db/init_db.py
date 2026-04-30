import logging
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.db.session import _connect_args
from app.models import Category, Mistake, MistakeTag, ReviewLog, ReviewSession, ReviewSessionItem, Tag, User  # noqa: F401
from app.services.auth_service import ensure_default_old_user


logger = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _build_alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _create_all(database_url: str) -> None:
    engine = create_engine(database_url, connect_args=_connect_args(database_url))
    Base.metadata.create_all(bind=engine)


def _database_has_state(database_url: str) -> bool:
    url = make_url(database_url)
    backend = url.get_backend_name()
    if backend == "sqlite":
        database = url.database or ""
        if database in {":memory:", ""}:
            return False
        db_path = Path(database)
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
        return db_path.exists()
    engine = create_engine(database_url, connect_args=_connect_args(database_url))
    try:
        with engine.connect() as conn:
            return engine.dialect.has_table(conn, "alembic_version")
    finally:
        engine.dispose()


def initialize_database(database_url: Optional[str] = None, force_fallback: bool = False) -> None:
    target_url = database_url or settings.database_url

    if force_fallback:
        _create_all(target_url)
        _ensure_old_user(target_url)
        return

    db_exists = _database_has_state(target_url)
    try:
        command.upgrade(_build_alembic_config(target_url), "head")
    except Exception as exc:
        if not db_exists:
            logger.warning(
                "Alembic upgrade failed for empty DB, falling back to create_all: %s",
                exc,
            )
            _create_all(target_url)
        else:
            logger.error(
                "Alembic upgrade failed on existing DB; refusing to fall back to create_all: %s",
                exc,
            )
            raise
    _ensure_old_user(target_url)


def _ensure_old_user(database_url: str) -> None:
    engine = create_engine(database_url, connect_args=_connect_args(database_url))
    with Session(engine, autoflush=False, autocommit=False, expire_on_commit=False) as db:
        has_users_table = engine.dialect.has_table(db.connection(), "users")
        if has_users_table:
            ensure_default_old_user(db)
    engine.dispose()


def should_initialize_database(database_url: Optional[str] = None) -> bool:
    # Deprecated: kept for backwards compatibility. The lifespan now always runs
    # initialize_database(), which internally decides between fallback create_all
    # (empty DB) and fail-fast (existing DB) when Alembic upgrade fails.
    target_url = database_url or settings.database_url
    url = make_url(target_url)
    if url.get_backend_name() != "sqlite":
        return False

    database = url.database or ""
    if database in {":memory:", ""}:
        return True

    db_path = Path(database)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    return not db_path.exists()

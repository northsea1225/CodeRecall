from __future__ import annotations

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base
from app.models import Category, Mistake, MistakeTag, ReviewLog, ReviewSession, ReviewSessionItem, Tag, User  # noqa: F401

config = context.config

if config.config_file_name is not None:
    # alembic.ini ships a [logger_root] section; logging.config.fileConfig
    # rebuilds the root logger handlers from scratch, which detaches handlers
    # the host process attached earlier (uvicorn, pytest caplog, etc.). We
    # snapshot and restore them so in-process callers keep their logging.
    _root = logging.getLogger()
    _preserved = list(_root.handlers)
    fileConfig(config.config_file_name, disable_existing_loggers=False)
    for _handler in _preserved:
        if _handler not in _root.handlers:
            _root.addHandler(_handler)

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

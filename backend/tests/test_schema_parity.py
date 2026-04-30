"""Schema parity audit (H-009).

Asserts that ``Base.metadata.create_all`` produces a SQLite schema
identical to the one ``alembic upgrade head`` produces. Audits columns,
indexes, unique constraints, and foreign keys (including their names).

If this test fails, an alembic migration introduced a schema element that
the ORM Model declarations do not mirror — production DBs (built via
alembic) and dev/empty-DB fallbacks (built via ``create_all`` in
init_db.py) would then drift apart.

Long-term goal (Codex): retire production ``_create_all()`` so alembic
is the only schema source. Until then this test guards parity.
"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect

from app.db.base import Base
from app.db.session import _connect_args
from app import models  # noqa: F401 - populate metadata


def _sort_key(item):
    return (str(item[0]) if item[0] is not None else "~", item[1])


def _reflect(engine) -> dict:
    insp = inspect(engine)
    out: dict = {}
    for table in sorted(insp.get_table_names()):
        if table == "alembic_version":
            continue
        out[table] = {
            "columns": {c["name"]: str(c["type"]) for c in insp.get_columns(table)},
            "indexes": sorted(
                [
                    (idx["name"], tuple(idx["column_names"]), bool(idx["unique"]))
                    for idx in insp.get_indexes(table)
                ],
                key=_sort_key,
            ),
            "uniques": sorted(
                [
                    (u["name"], tuple(u["column_names"]))
                    for u in insp.get_unique_constraints(table)
                ],
                key=_sort_key,
            ),
            "fks": sorted(
                [
                    (
                        fk["name"],
                        tuple(fk["constrained_columns"]),
                        fk["referred_table"],
                        tuple(fk["referred_columns"]),
                    )
                    for fk in insp.get_foreign_keys(table)
                ],
                key=_sort_key,
            ),
        }
    return out


def test_create_all_matches_alembic_head(alembic_head_engine, tmp_path) -> None:
    create_all_url = f"sqlite:///{tmp_path}/createall.db"
    create_all_engine = create_engine(
        create_all_url, connect_args=_connect_args(create_all_url)
    )
    try:
        Base.metadata.create_all(bind=create_all_engine)
        assert _reflect(create_all_engine) == _reflect(alembic_head_engine)
    finally:
        create_all_engine.dispose()

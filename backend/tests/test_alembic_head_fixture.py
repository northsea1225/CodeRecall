"""Regression coverage exercising production migration scripts (alembic head).

These tests are intentionally minimal: their job is to prove the
``alembic_head_engine`` fixture is healthy and that the schema produced by
real migration scripts (rather than ``Base.metadata.create_all``) still
satisfies key application invariants — user_id filtering and the per-user
uuid uniqueness index introduced in 0008.

Heavier integration coverage continues to live in
``test_cross_user_isolation.py`` and ``test_import_export_v3.py``, both of
which still use ``create_all`` paths. Those are kept as-is to provide
complementary coverage; nothing here replaces them.
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Category, Mistake, User
from app.services.auth_service import hash_password


def _make_user(db: Session, username: str) -> User:
    user = User(username=username, password_hash=hash_password("testpass123"))
    db.add(user)
    db.flush()
    return user


def _make_category(db: Session, user_id: int, name: str = "Default") -> Category:
    category = Category(user_id=user_id, name=name)
    db.add(category)
    db.flush()
    return category


def _make_mistake(
    db: Session,
    user_id: int,
    category_id: int,
    *,
    title: str,
    uuid: str | None = None,
) -> Mistake:
    mistake = Mistake(
        user_id=user_id,
        category_id=category_id,
        uuid=uuid,
        title=title,
        stem_markdown="stem",
        wrong_answer_markdown="wrong",
        correct_answer_markdown="correct",
        error_reason_markdown="reason",
        language="cpp",
        difficulty=1,
    )
    db.add(mistake)
    db.flush()
    return mistake


def test_alembic_head_engine_is_at_head_revision(alembic_head_engine) -> None:
    inspector = sa.inspect(alembic_head_engine)
    table_names = set(inspector.get_table_names())

    assert "alembic_version" in table_names
    for required in ("users", "mistakes", "categories", "review_sessions", "review_logs"):
        assert required in table_names, f"missing table {required}"

    with alembic_head_engine.connect() as conn:
        version = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
    assert version == "0008"

    mistake_indexes = {idx["name"] for idx in inspector.get_indexes("mistakes")}
    assert "ix_mistakes_user_uuid" in mistake_indexes, (
        "per-user uuid unique index from migration 0008 missing"
    )


def test_user_id_filter_isolation_under_alembic_head(alembic_head_engine) -> None:
    with Session(alembic_head_engine, expire_on_commit=False) as db:
        alice = _make_user(db, "alice")
        bob = _make_user(db, "bob")
        alice_cat = _make_category(db, alice.id, name="Alice cat")
        bob_cat = _make_category(db, bob.id, name="Bob cat")
        _make_mistake(db, alice.id, alice_cat.id, title="alice-mistake")
        _make_mistake(db, bob.id, bob_cat.id, title="bob-mistake")
        db.commit()

        alice_visible = db.scalars(
            sa.select(Mistake).where(Mistake.user_id == alice.id)
        ).all()
        bob_visible = db.scalars(
            sa.select(Mistake).where(Mistake.user_id == bob.id)
        ).all()

    assert {m.title for m in alice_visible} == {"alice-mistake"}
    assert {m.title for m in bob_visible} == {"bob-mistake"}


def test_per_user_uuid_unique_index_under_alembic_head(alembic_head_engine) -> None:
    shared_uuid = "00000000-0000-4000-8000-000000000abc"

    with Session(alembic_head_engine, expire_on_commit=False) as db:
        alice = _make_user(db, "alice")
        bob = _make_user(db, "bob")
        alice_cat = _make_category(db, alice.id, name="Alice cat")
        bob_cat = _make_category(db, bob.id, name="Bob cat")

        _make_mistake(db, alice.id, alice_cat.id, title="alice-1", uuid=shared_uuid)
        _make_mistake(db, bob.id, bob_cat.id, title="bob-1", uuid=shared_uuid)
        db.commit()

    # Same (user_id, uuid) should be rejected by the partial unique index.
    with Session(alembic_head_engine, expire_on_commit=False) as db:
        alice = db.scalars(sa.select(User).where(User.username == "alice")).one()
        cat = db.scalars(sa.select(Category).where(Category.user_id == alice.id)).one()
        with pytest.raises(IntegrityError):
            _make_mistake(db, alice.id, cat.id, title="alice-dup", uuid=shared_uuid)
            db.commit()

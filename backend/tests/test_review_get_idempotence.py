"""Idempotence tests for the review GET surface (H-007).

The GET endpoints (/sessions/{id}/next, /sessions/{id}/summary) used to
opportunistically write to the DB — syncing session.completed_count and
setting session.ended_at. As of H-007 those writes only happen on the
POST submit path (apply_progress). These tests pin that contract.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models import (
    Category,
    Mistake,
    ReviewResult,
    ReviewSession,
    User,
)
from app.services.auth_service import hash_password
from app.services.review import get_next_item, get_summary, start_session, submit_result


def _make_user(db: Session, username: str = "alice") -> User:
    user = User(username=username, password_hash=hash_password("testpass123"))
    db.add(user)
    db.flush()
    return user


def _seed_session_inputs(db: Session, user_id: int, *, count: int = 2) -> list[int]:
    category = Category(user_id=user_id, name="cat")
    db.add(category)
    db.flush()
    ids: list[int] = []
    for i in range(count):
        mistake = Mistake(
            user_id=user_id,
            category_id=category.id,
            title=f"m{i}",
            stem_markdown="stem",
            wrong_answer_markdown="wrong",
            correct_answer_markdown="correct",
            error_reason_markdown="reason",
            language="cpp",
            difficulty=1,
        )
        db.add(mistake)
        db.flush()
        ids.append(mistake.id)
    db.commit()
    return ids


def _session_state(db: Session, session_id: int) -> tuple:
    row = db.scalar(sa.select(ReviewSession).where(ReviewSession.id == session_id))
    db.refresh(row)
    return (row.ended_at, row.completed_count)


def test_get_summary_does_not_mutate_session(alembic_head_engine) -> None:
    with Session(alembic_head_engine, expire_on_commit=False) as db:
        user = _make_user(db)
        mistake_ids = _seed_session_inputs(db, user.id, count=2)
        session_out = start_session(db, "random", 5, user_id=user.id)
        session_id = session_out.id

        # Submit only the first item; session is still in progress.
        submit_result(db, session_id, mistake_ids[0], ReviewResult.GOOD, user_id=user.id)

        before = _session_state(db, session_id)

        for _ in range(3):
            get_summary(db, session_id, user_id=user.id)

        after = _session_state(db, session_id)
        assert before == after


def test_get_next_item_does_not_mutate_session(alembic_head_engine) -> None:
    with Session(alembic_head_engine, expire_on_commit=False) as db:
        user = _make_user(db)
        mistake_ids = _seed_session_inputs(db, user.id, count=2)
        session_out = start_session(db, "random", 5, user_id=user.id)
        session_id = session_out.id

        submit_result(db, session_id, mistake_ids[0], ReviewResult.GOOD, user_id=user.id)

        before = _session_state(db, session_id)

        for _ in range(3):
            get_next_item(db, session_id, user_id=user.id)

        after = _session_state(db, session_id)
        assert before == after


def test_submit_last_item_marks_session_completed(alembic_head_engine) -> None:
    with Session(alembic_head_engine, expire_on_commit=False) as db:
        user = _make_user(db)
        mistake_ids = _seed_session_inputs(db, user.id, count=2)
        session_out = start_session(db, "random", 5, user_id=user.id)
        session_id = session_out.id

        # Sanity: total queue size depends on what start_session selected.
        session_row = db.scalar(sa.select(ReviewSession).where(ReviewSession.id == session_id))
        assert session_row.ended_at is None
        assert session_row.total_count == 2

        # Submit both queued items; the apply_progress on the final submit
        # is what should mark ended_at — not the GETs.
        for mid in mistake_ids:
            submit_result(db, session_id, mid, ReviewResult.GOOD, user_id=user.id)

        db.refresh(session_row)
        assert session_row.ended_at is not None
        assert session_row.completed_count == 2

        # Final GETs are idempotent on the now-completed session.
        before = _session_state(db, session_id)
        for _ in range(3):
            get_summary(db, session_id, user_id=user.id)
            get_next_item(db, session_id, user_id=user.id)
        after = _session_state(db, session_id)
        assert before == after

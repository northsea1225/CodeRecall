from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Mistake, ReviewLog, ReviewSession, ReviewSessionItem
from app.services.taxonomy_service import utc_now


def _mistake_loader_options():
    return (
        joinedload(Mistake.category),
        selectinload(Mistake.tags),
    )


def select_session_mistakes(db: Session, strategy: str, limit: int) -> list[Mistake]:
    if strategy == "random":
        statement = (
            select(Mistake)
            .options(*_mistake_loader_options())
            .where(Mistake.is_archived.is_(False))
            .order_by(func.random())
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    # "due_first" and "spaced_repetition" are intentionally equivalent: both sort by
    # next_review_at ascending. A full SM-2 interval-aware ordering is deferred to a
    # future iteration; the distinction is kept in the API surface for forward-compatibility.
    if strategy not in {"due_first", "spaced_repetition"}:
        raise ValueError(f"unsupported review strategy: {strategy}")

    now = utc_now()
    due_statement = (
        select(Mistake)
        .options(*_mistake_loader_options())
        .where(
            Mistake.is_archived.is_(False),
            Mistake.next_review_at.is_not(None),
            Mistake.next_review_at <= now,
        )
        .order_by(Mistake.next_review_at.asc(), Mistake.id.asc())
        .limit(limit)
    )
    return list(db.scalars(due_statement).all())


def count_due_mistakes(db: Session) -> tuple[int, datetime]:
    now = utc_now()
    statement = (
        select(func.count())
        .select_from(Mistake)
        .where(
            Mistake.is_archived.is_(False),
            Mistake.next_review_at.is_not(None),
            Mistake.next_review_at <= now,
        )
    )
    return int(db.scalar(statement) or 0), now


def select_next_mistake(db: Session, session: ReviewSession) -> ReviewSessionItem | None:
    submitted_subquery = select(ReviewLog.mistake_id).where(ReviewLog.session_id == session.id)
    statement = (
        select(ReviewSessionItem)
        .options(
            joinedload(ReviewSessionItem.mistake).joinedload(Mistake.category),
            joinedload(ReviewSessionItem.mistake).selectinload(Mistake.tags),
        )
        .where(
            ReviewSessionItem.session_id == session.id,
            ~ReviewSessionItem.mistake_id.in_(submitted_subquery),
        )
        .order_by(ReviewSessionItem.order_index.asc(), ReviewSessionItem.id.asc())
        .limit(1)
    )
    return db.scalar(statement)

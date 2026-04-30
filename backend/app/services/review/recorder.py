from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import raise_api_error, raise_not_found
from app.models import Mistake, ReviewLog, ReviewResult, ReviewSession, ReviewSessionItem
from app.services.taxonomy_service import normalize_optional_text, utc_now


def record_review_log(
    db: Session,
    session: ReviewSession,
    mistake_id: int,
    user_result: ReviewResult,
    shown_at: Optional[datetime],
    time_spent_ms: Optional[int],
    note: Optional[str],
    *,
    user_id: int,
) -> ReviewLog:
    queue_item = db.scalar(
        select(ReviewSessionItem).where(
            ReviewSessionItem.session_id == session.id,
            ReviewSessionItem.mistake_id == mistake_id,
        )
    )
    if queue_item is None:
        raise_api_error(
            422,
            "mistake_not_in_session",
            "Mistake is not part of this review session.",
            {"session_id": session.id, "mistake_id": mistake_id},
        )

    existing = db.scalar(
        select(ReviewLog).where(
            ReviewLog.session_id == session.id,
            ReviewLog.mistake_id == mistake_id,
        )
    )
    if existing is not None:
        return existing

    mistake = db.scalar(
        select(Mistake).where(Mistake.id == mistake_id, Mistake.user_id == user_id)
    )
    if mistake is None:
        raise_not_found("mistake", mistake_id)

    answered_at = utc_now()
    log = ReviewLog(
        user_id=session.user_id,
        mistake_id=mistake.id,
        session_id=session.id,
        review_mode=session.strategy,
        user_result=user_result,
        shown_at=shown_at or answered_at,
        answered_at=answered_at,
        time_spent_ms=time_spent_ms,
        note=normalize_optional_text(note) or "",
    )
    db.add(log)
    db.flush()
    return log

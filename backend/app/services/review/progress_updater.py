from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Mistake, MistakeStatus, ReviewLog, ReviewResult, ReviewSession
from app.schemas.review import ReviewProgressOut
from app.services.review.scheduler import compute_next_schedule
from app.services.taxonomy_service import utc_now

_PROMOTION_RESULTS = {ReviewResult.GOOD, ReviewResult.EASY}


def _derive_status(answered_logs: list[ReviewLog]) -> MistakeStatus:
    if not answered_logs:
        return MistakeStatus.NEW

    latest = answered_logs[-1]
    if latest.user_result == ReviewResult.AGAIN:
        return MistakeStatus.LEARNING

    if len(answered_logs) == 1:
        return MistakeStatus.LEARNING

    if len(answered_logs) >= 3 and all(log.user_result in _PROMOTION_RESULTS for log in answered_logs[-2:]):
        return MistakeStatus.MASTERED

    return MistakeStatus.REVIEWING


def apply_progress(db: Session, session: ReviewSession, log: ReviewLog, *, user_id: int) -> ReviewProgressOut:
    mistake = db.scalar(
        select(Mistake).where(Mistake.id == log.mistake_id, Mistake.user_id == user_id)
    )
    if mistake is None:
        raise ValueError(f"mistake {log.mistake_id} missing while applying review progress")

    answered_logs = list(
        db.scalars(
            select(ReviewLog)
            .where(
                ReviewLog.mistake_id == log.mistake_id,
                ReviewLog.user_id == user_id,
                ReviewLog.answered_at.is_not(None),
            )
            .order_by(ReviewLog.answered_at.asc(), ReviewLog.id.asc())
        ).all()
    )
    mistake.review_count = len(answered_logs)
    mistake.last_reviewed_at = answered_logs[-1].answered_at if answered_logs else None
    mistake.status = _derive_status(answered_logs)

    if session.strategy == "spaced_repetition":
        previous_interval = mistake.interval_days
        previous_ease_factor = mistake.ease_factor
        schedule = compute_next_schedule(
            user_result=log.user_result,
            ease_factor=mistake.ease_factor,
            interval_days=mistake.interval_days,
            repetition=mistake.repetition,
            now=log.answered_at,
        )
        mistake.ease_factor = float(schedule["ease_factor"])
        mistake.interval_days = int(schedule["interval_days"])
        mistake.repetition = int(schedule["repetition"])
        mistake.next_review_at = schedule["next_review_at"]

        log.old_interval_days = previous_interval
        log.new_interval_days = mistake.interval_days
        log.old_ease_factor = previous_ease_factor
        log.new_ease_factor = mistake.ease_factor

    completed = int(
        db.scalar(
            select(func.count())
            .select_from(ReviewLog)
            .where(ReviewLog.session_id == session.id, ReviewLog.user_id == user_id)
        )
        or 0
    )
    session.completed_count = completed
    if completed >= session.total_count and session.ended_at is None:
        session.ended_at = log.answered_at or utc_now()

    db.commit()
    db.refresh(log)
    db.refresh(session)
    db.refresh(mistake)
    return ReviewProgressOut(completed=completed, total=session.total_count)

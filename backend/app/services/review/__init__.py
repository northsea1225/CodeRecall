from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.errors import raise_not_found
from app.models import Mistake, ReviewLog, ReviewResult, ReviewSession, ReviewSessionItem
from app.schemas.review import (
    ReviewCapabilityOut,
    ReviewDueCountOut,
    ReviewItemOut,
    ReviewLogOut,
    ReviewNextOut,
    ReviewProgressOut,
    ReviewRevealOut,
    ReviewResultCountsOut,
    ReviewSessionOut,
    ReviewSubmitOut,
    ReviewSummaryOut,
)
from app.services.ai_analysis_service import get_ai_capability
from app.services.review.progress_updater import apply_progress
from app.services.review.recorder import record_review_log
from app.services.review.selector import count_due_mistakes, select_next_mistake, select_session_mistakes
from app.services.taxonomy_service import utc_now


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _get_session(db: Session, session_id: int, user_id: int | None = None) -> ReviewSession:
    statement = select(ReviewSession).where(ReviewSession.id == session_id)
    if user_id is not None:
        statement = statement.where(ReviewSession.user_id == user_id)
    session = db.scalar(statement)
    if session is None:
        raise_not_found("review_session", session_id)
    return session


def _serialize_review_item(mistake: Mistake, *, shown_at: datetime) -> ReviewItemOut:
    return ReviewItemOut(
        mistake_id=mistake.id,
        title=mistake.title,
        stem_markdown=mistake.stem_markdown,
        language=mistake.language,
        difficulty=mistake.difficulty,
        category_name=mistake.category.name,
        tag_names=[tag.name for tag in mistake.tags],
        shown_at=shown_at,
    )


def _serialize_reveal(mistake: Mistake) -> ReviewRevealOut:
    return ReviewRevealOut(
        mistake_id=mistake.id,
        title=mistake.title,
        stem_markdown=mistake.stem_markdown,
        wrong_answer_markdown=mistake.wrong_answer_markdown,
        correct_answer_markdown=mistake.correct_answer_markdown,
        error_reason_markdown=mistake.error_reason_markdown,
        language=mistake.language,
        difficulty=mistake.difficulty,
        category_name=mistake.category.name,
        tag_names=[tag.name for tag in mistake.tags],
    )


def _serialize_review_log(log: ReviewLog, *, progress: ReviewProgressOut) -> ReviewSubmitOut:
    payload = ReviewLogOut.model_validate(log).model_dump()
    return ReviewSubmitOut(**payload, progress=progress)


def _count_completed(db: Session, session_id: int, user_id: int | None = None) -> int:
    filters = [ReviewLog.session_id == session_id]
    if user_id is not None:
        filters.append(ReviewLog.user_id == user_id)
    statement = select(func.count()).select_from(ReviewLog).where(*filters)
    return int(db.scalar(statement) or 0)


def _progress_for_session(db: Session, session: ReviewSession, user_id: int | None = None) -> ReviewProgressOut:
    completed = _count_completed(db, session.id, user_id=user_id)
    if session.completed_count != completed:
        session.completed_count = completed
        db.commit()
        db.refresh(session)
    return ReviewProgressOut(completed=completed, total=session.total_count)


def _mark_session_completed_if_needed(db: Session, session: ReviewSession, *, progress: ReviewProgressOut) -> None:
    if progress.completed >= session.total_count and session.ended_at is None:
        session.ended_at = utc_now()
        db.commit()
        db.refresh(session)


def start_session(db: Session, strategy: str, limit: int, user_id: int | None = None) -> ReviewSessionOut:
    started_at = utc_now()
    session = ReviewSession(
        user_id=user_id,
        strategy=strategy,
        started_at=started_at,
        total_count=0,
        completed_count=0,
    )
    db.add(session)
    db.flush()

    selected_mistakes = select_session_mistakes(db, strategy, limit, user_id=user_id)

    ordered_mistakes: list[Mistake] = []
    for order_index, mistake in enumerate(selected_mistakes):
        ordered_mistakes.append(mistake)
        db.add(
            ReviewSessionItem(
                session_id=session.id,
                mistake_id=mistake.id,
                order_index=order_index,
            )
        )

    session.total_count = len(ordered_mistakes)
    if session.total_count == 0:
        session.ended_at = started_at

    db.commit()
    db.refresh(session)

    next_item = None
    if ordered_mistakes:
        next_item = _serialize_review_item(ordered_mistakes[0], shown_at=utc_now())

    return ReviewSessionOut(
        id=session.id,
        strategy=session.strategy,
        started_at=_coerce_utc(session.started_at),
        total_count=session.total_count,
        completed_count=session.completed_count,
        next_item=next_item,
    )


def get_next_item(db: Session, session_id: int, user_id: int | None = None) -> ReviewNextOut:
    session = _get_session(db, session_id, user_id=user_id)
    progress = _progress_for_session(db, session, user_id=user_id)

    next_session_item = select_next_mistake(db, session)
    if next_session_item is None:
        _mark_session_completed_if_needed(db, session, progress=progress)
        return ReviewNextOut(next_item=None, progress=progress)

    return ReviewNextOut(
        next_item=_serialize_review_item(next_session_item.mistake, shown_at=utc_now()),
        progress=progress,
    )


def submit_result(
    db: Session,
    session_id: int,
    mistake_id: int,
    user_result: ReviewResult,
    shown_at: Optional[datetime] = None,
    time_spent_ms: Optional[int] = None,
    note: Optional[str] = None,
    user_id: int | None = None,
) -> ReviewSubmitOut:
    session = _get_session(db, session_id, user_id=user_id)
    log = record_review_log(
        db,
        session,
        mistake_id=mistake_id,
        user_result=user_result,
        shown_at=shown_at,
        time_spent_ms=time_spent_ms,
        note=note,
        user_id=user_id,
    )
    progress = apply_progress(db, session, log, user_id=user_id)
    return _serialize_review_log(log, progress=progress)


def get_reveal(db: Session, mistake_id: int, user_id: int | None = None) -> ReviewRevealOut:
    filters = [Mistake.id == mistake_id]
    if user_id is not None:
        filters.append(Mistake.user_id == user_id)
    mistake = db.scalar(
        select(Mistake)
        .options(joinedload(Mistake.category), selectinload(Mistake.tags))
        .where(*filters)
    )
    if mistake is None:
        raise_not_found("mistake", mistake_id)
    return _serialize_reveal(mistake)


def get_summary(db: Session, session_id: int, user_id: int | None = None) -> ReviewSummaryOut:
    session = _get_session(db, session_id, user_id=user_id)
    progress = _progress_for_session(db, session, user_id=user_id)
    _mark_session_completed_if_needed(db, session, progress=progress)

    counts = {result.value: 0 for result in ReviewResult}
    rows = db.execute(
        select(ReviewLog.user_result, func.count())
        .where(
            ReviewLog.session_id == session.id,
            *( [ReviewLog.user_id == user_id] if user_id is not None else [] ),
        )
        .group_by(ReviewLog.user_result)
    ).all()
    for result, count in rows:
        key = result.value if isinstance(result, ReviewResult) else str(result)
        counts[key] = int(count)

    end_time = session.ended_at or utc_now()
    duration_ms = max(
        int((_coerce_utc(end_time) - _coerce_utc(session.started_at)).total_seconds() * 1000),
        0,
    )

    return ReviewSummaryOut(
        total_count=session.total_count,
        completed_count=progress.completed,
        result_counts=ReviewResultCountsOut(**counts),
        duration_ms=duration_ms,
    )


def get_capability() -> ReviewCapabilityOut:
    capability = get_ai_capability()
    return ReviewCapabilityOut(
        ai_analysis_enabled=bool(capability["enabled"]),
        model=capability["model"] if capability["enabled"] else None,
    )


def get_due_count(db: Session, user_id: int | None = None) -> ReviewDueCountOut:
    due_count, as_of = count_due_mistakes(db, user_id=user_id)
    return ReviewDueCountOut(due_count=due_count, as_of=as_of)

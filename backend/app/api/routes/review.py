from typing import Optional

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.review import (
    ReviewCapabilityOut,
    ReviewDueCountOut,
    ReviewNextOut,
    ReviewRevealOut,
    ReviewSessionOut,
    ReviewSessionStartIn,
    ReviewSubmitIn,
    ReviewSubmitOut,
    ReviewSummaryOut,
)
from app.services.review import (
    get_capability,
    get_due_count,
    get_next_item,
    get_reveal,
    get_summary,
    start_session,
    submit_result,
)


router = APIRouter(prefix="/review", tags=["review"])


@router.post("/sessions", response_model=ReviewSessionOut, status_code=status.HTTP_201_CREATED)
def start_review_session_route(
    payload: Optional[ReviewSessionStartIn] = Body(default=None),
    db: Session = Depends(get_db),
) -> ReviewSessionOut:
    request = payload or ReviewSessionStartIn()
    return start_session(db, strategy=request.strategy, limit=request.limit)


@router.get("/sessions/{session_id}/next", response_model=ReviewNextOut)
def get_next_review_item_route(session_id: int, db: Session = Depends(get_db)) -> ReviewNextOut:
    return get_next_item(db, session_id)


@router.post("/sessions/{session_id}/submit", response_model=ReviewSubmitOut)
def submit_review_result_route(
    session_id: int,
    payload: ReviewSubmitIn,
    db: Session = Depends(get_db),
) -> ReviewSubmitOut:
    return submit_result(
        db,
        session_id,
        payload.mistake_id,
        payload.user_result,
        payload.shown_at,
        payload.time_spent_ms,
        payload.note,
    )


@router.get("/sessions/{session_id}/summary", response_model=ReviewSummaryOut)
def get_review_summary_route(session_id: int, db: Session = Depends(get_db)) -> ReviewSummaryOut:
    return get_summary(db, session_id)


@router.get("/capability", response_model=ReviewCapabilityOut, response_model_exclude_none=True)
def get_review_capability_route() -> ReviewCapabilityOut:
    return get_capability()


@router.get("/due-count", response_model=ReviewDueCountOut)
def get_review_due_count_route(db: Session = Depends(get_db)) -> ReviewDueCountOut:
    return get_due_count(db)


@router.get("/items/{mistake_id}/reveal", response_model=ReviewRevealOut)
def get_review_reveal_route(mistake_id: int, db: Session = Depends(get_db)) -> ReviewRevealOut:
    return get_reveal(db, mistake_id)

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.review import ReviewResult


ReviewStrategy = Literal["random", "spaced_repetition", "due_first"]


class ReviewItemOut(BaseModel):
    mistake_id: int
    title: str
    stem_markdown: str
    language: str
    difficulty: int
    category_name: str
    tag_names: list[str]
    shown_at: datetime


class ReviewRevealOut(BaseModel):
    mistake_id: int
    title: str
    stem_markdown: str
    wrong_answer_markdown: str
    correct_answer_markdown: str
    error_reason_markdown: str
    language: str
    difficulty: int
    category_name: str
    tag_names: list[str]


class ReviewProgressOut(BaseModel):
    completed: int
    total: int


class ReviewSessionStartIn(BaseModel):
    strategy: ReviewStrategy = "random"
    limit: int = Field(default=10, ge=1, le=50)


class ReviewSessionOut(BaseModel):
    id: int
    strategy: ReviewStrategy
    started_at: datetime
    total_count: int
    completed_count: int
    next_item: Optional[ReviewItemOut] = None


class ReviewNextOut(BaseModel):
    next_item: Optional[ReviewItemOut] = None
    progress: ReviewProgressOut


class ReviewSubmitIn(BaseModel):
    mistake_id: int
    user_result: ReviewResult
    shown_at: Optional[datetime] = None
    time_spent_ms: Optional[int] = Field(default=None, ge=0)
    note: Optional[str] = None


class ReviewLogOut(BaseModel):
    id: int
    mistake_id: int
    session_id: Optional[int]
    review_mode: str
    user_result: ReviewResult
    shown_at: datetime
    answered_at: Optional[datetime]
    time_spent_ms: Optional[int]
    note: str

    model_config = ConfigDict(from_attributes=True)


class ReviewSubmitOut(ReviewLogOut):
    progress: ReviewProgressOut


class ReviewResultCountsOut(BaseModel):
    again: int = 0
    hard: int = 0
    good: int = 0
    easy: int = 0


class ReviewSummaryOut(BaseModel):
    total_count: int
    completed_count: int
    result_counts: ReviewResultCountsOut
    duration_ms: int


class ReviewCapabilityOut(BaseModel):
    ai_analysis_enabled: bool
    model: Optional[str] = None


class ReviewDueCountOut(BaseModel):
    due_count: int
    as_of: datetime
